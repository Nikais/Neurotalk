"""
Telegram Manager Module.

Contains implementation of the TelegramManager, which helps run ParlAI via Telegram.
"""
import logging
import os

import requests
import parlai.chat_service.utils.logging as log_utils
from parlai.chat_service.core.chat_service_manager import ChatServiceManager
from parlai.core.agents import create_agent
from parlai.utils.io import PathManager

import telegram.core.server as server_utils
from telegram.agents import TelegramAgent
from telegram.core.socket import TelegramServiceMessageSocket


class TelegramManager(ChatServiceManager):
    """
    Manages interactions between agents on telegram as well as direct interactions
    between agents and the telegram overworld.
    """

    class MessageSender(ChatServiceManager.ChatServiceMessageSender):
        """
        MessageSender is a wrapper around requests that simplifies the
        process of sending content.
        """

        def __init__(self, secret_token: str):
            self.token = secret_token

        def send_read(self, receiver_id: int):
            pass

        def send_chat_action(self, chat_id, action):
            api_address = f'https://api.telegram.org/bot{self.token}/sendChatAction'
            message = {'chat_id': chat_id, 'action': action}
            requests.post(api_address, json=message)

        def typing_on(self, receiver_id: int, persona_id=None):
            """
            Send typing on msg to agent at receiver_id.
            """
            self.send_chat_action(receiver_id, 'typing')

        def send_message(self, chat_id, text):
            """
            Sends a message directly to telegram.
            """
            api_address = f'https://api.telegram.org/bot{self.token}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': text
            }
            response = requests.post(api_address, json=payload)
            result = response.json()
            log_utils.print_and_log(
                logging.INFO, f'"Telegram response from message send: {result}"'
            )
            return result

        def set_webhook(self, url: str):
            api_address = f'https://api.telegram.org/bot{self.token}/setWebhook'
            message = {'url': url}
            requests.post(api_address, json=message)

    EXIT_STR = 'exit'

    def __init__(self, opt):
        """
        Create a TelegramManager using the given setup options.
        """
        super().__init__(opt)

        self.server_task_name = None

        self._init_logs()

        # Read in Config
        self._parse_config(opt)
        self._complete_setup()

    def _complete_setup(self):
        self.setup_server()
        self.init_new_state()
        self.setup_socket()
        self.start_new_run()
        self._load_model()

    def _confirm_message_delivery(self, event):
        print(f'Event {event}')
        self._log_debug(
            f'Message {event["delivery"]["mid"]} marked as received.'
        )

    def _create_agent(self, task_id: str, agent_id: int) -> TelegramAgent:
        return TelegramAgent(self.opt, self, agent_id, task_id)

    def _init_logs(self):
        """
        Initialize logging settings from the opt.
        """
        log_utils.set_is_debug(self.opt['is_debug'])
        log_utils.set_log_level(self.opt['log_level'])

    def _handle_bot_read(self, agent_id):
        self.sender.send_read(agent_id)
        self.sender.typing_on(agent_id)

    def _handle_webhook_event(self, event):
        if 'message' in event:
            if 'photo' in event['message']:
                event['message']['image'] = True
            if 'document' in event['message']:
                if 'image' in event['message']['document']['mime_type']:
                    event['message']['image'] = True
            self._on_new_message(event)

    def _load_model(self):
        """
        Load model if necessary.
        """
        if 'models' in self.opt and self.should_load_model:
            model_params = {}
            model_info = {}
            for model in self.opt['models']:
                model_opt = self.opt['models'][model]
                override = model_opt.get('override', {})
                if type(override) is list:
                    model_opt['overrides'] = override[0]
                model_params[model] = create_agent(model_opt).share()
                model_info[model] = {'override': override}
            self.runner_opt['model_info'] = model_info
            self.runner_opt['shared_bot_params'] = model_params

    def _on_first_message(self, message):
        agent_id = message['sender']['id']
        self._launch_overworld(agent_id)

    def get_app_token(self):
        """
        Find and return an app access token.
        """
        if not self.opt.get('force_telegram_bot_token'):
            if not os.path.exists(os.path.expanduser("~/.parlai/")):
                PathManager.mkdirs(os.path.expanduser("~/.parlai/"))
            access_token_file = '~/.parlai/telegram_token'
            expanded_file_path = os.path.expanduser(access_token_file)
            if os.path.exists(expanded_file_path):
                print(f"Token was read from: {expanded_file_path}")
                with open(expanded_file_path, 'r') as access_token_file:
                    return access_token_file.read()

        token = input(
            'Enter your bot\'s access token from the BotFather page at '
            'https://telegram.me/botfather/ to continue setup: '
        )
        access_token_file_path = '~/.parlai/telegram_token'
        expanded_file_path = os.path.expanduser(access_token_file_path)
        with open(expanded_file_path, 'w') as access_token_file:
            access_token_file.write(token)
        return token

    def parse_additional_args(self, opt):
        """
        Parse any other service specific args here.
        """
        self.should_load_model = self.config['additional_args'].get('load_model', True)

    def restructure_message(self, message):  # Todo Test it
        """
        Use this function to restructure the message into the provided format.

        returns the appropriate new_message.
        """
        message = message['message']
        message['mid'] = message.pop('message_id')
        message['recipient'] = message.pop('chat')
        message['sender'] = message.pop('from')
        return message

    def setup_server(self):
        """
        Prepare the Telegram server for handling messages.
        """
        if self.bypass_server_setup:
            return

        log_utils.print_and_log(
            logging.INFO,
            '\nYou are going to allow people on Telegram to be agents in '
            'ParlAI.\nDuring this process, Internet connection is required, '
            'and you should turn off your computer\'s auto-sleep '
            'feature.\n',
            should_print=True,
        )
        input('Please press Enter to continue... ')

        log_utils.print_and_log(
            logging.INFO, 'Setting up Telegram webhook...', should_print=True
        )

        # Setup the server with a task name related to the current task
        task_name = f'ParlAI-Telegram-{self.opt["task"]}'
        self.server_task_name = ''.join(
            ch for ch in task_name.lower() if ch.isalnum() or ch == '-'
        )
        self.server_url = server_utils.setup_server(self.server_task_name, self.opt['local'])
        log_utils.print_and_log(
            logging.INFO,
            f'Webhook address: {self.server_url}/webhook',
            should_print=True,
        )

    def setup_socket(self):
        """
        Set up socket to start communicating to workers.
        """
        if self.bypass_server_setup:
            return

        log_utils.print_and_log(
            logging.INFO, 'Local: Setting up WebSocket...', should_print=True
        )

        self.app_token = self.get_app_token()
        self.sender = TelegramManager.MessageSender(self.app_token)
        self.sender.set_webhook(f'{self.server_url}/webhook')

        # Set up receive
        socket_use_url = self.server_url
        if self.opt['local']:
            socket_use_url = 'https://localhost'
        self.socket = TelegramServiceMessageSocket(
            socket_use_url, self.port, self._handle_webhook_event
        )
        log_utils.print_and_log(logging.INFO, 'Done with websocket', should_print=True)

    def shutdown(self):
        """
        Handle any client shutdown cleanup.
        """
        try:
            self.running = False
            self.world_runner.shutdown()
            if not self.bypass_server_setup:
                self.socket.keep_running = False
            self._expire_all_conversations()
        except BaseException as e:
            log_utils.print_and_log(logging.ERROR, f'world ended in error: {e}')

        finally:
            if not self.bypass_server_setup:
                server_utils.delete_server(self.server_task_name, self.opt['local'])

    # Agent Interaction Functions #

    def observe_message(self, receiver_id: int, text: str, quick_replies=None, persona_id: str = None):
        """
        Send a message through the message manager.

        :param receiver_id:
            identifier for agent to send message to
        :param text:
            text to send
        :param quick_replies:
            list of quick replies
        :param persona_id:
            identifier of persona
        """
        return self.sender.send_message(receiver_id, text)
