import logging
from typing import Union

import requests
from parlai.chat_service.utils import logging as log_utils

MAX_TEXT_CHARS = 4096


def base_telegram_api_method(function):
    def wrapper(self, *args, **kwargs):
        response = function(self, *args, **kwargs).json()
        if response['ok']:
            if 'description' in response:
                log_utils.print_and_log(
                    logging.INFO,
                    f"Telegram API response: {response['description']}",
                    should_print=True
                )
            return response['result']
        else:
            raise Exception(response['description'])

    return wrapper


class MessageSender:
    """
    MessageSender is a wrapper around telegram requests that simplifies the
    process of sending content.
    """

    def __init__(self, secret_token: str):
        self.token = secret_token
        self.api_url = f'https://api.telegram.org/bot{self.token}'

    @base_telegram_api_method
    def send_chat_action(self, chat_id: Union[int, str], action: str):
        """
        Use this method when you need to tell the user that something is happening on the bot's side. The status
        is set for 5 seconds or less (when a message arrives from your bot, Telegram clients clear its typing status).

        :param chat_id:
            unique identifier for the target chat or username of the target channel.
        :param action:
            type of action to broadcast. Choose one, depending on what the user is about to receive.
        :return:
            True on success
        """
        payload = {'chat_id': chat_id, 'action': action}
        return requests.post(self.api_url + '/sendChatAction', json=payload)

    def send_read(self, chat_id):
        pass

    def typing_to(self, chat_id: Union[int, str]):
        """
        Send typing on msg to agent at chat_id.

        :return:
            True on success
        """
        return self.send_chat_action(chat_id, 'typing')

    @base_telegram_api_method
    def send_message(self, chat_id: Union[int, str], text: str, reply_to_message_id: int = None):
        """
        Send message from Bot to chat_id directly

        :param chat_id:
            Unique identifier for the target chat or username of the target channel.
        :param text:
            Text of the message to be sent, 1-4096 characters after entities parsing.
        :param reply_to_message_id:
            If the message is a reply, ID of the original message.
        :return:
            dict with Message object
        """
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id
        return requests.post(self.api_url + '/sendMessage', json=payload)

    @base_telegram_api_method
    def set_webhook(self, url: str):
        """
        Use this method to specify a url and receive incoming updates via an outgoing webhook.

        :param url:
            HTTPS url to send updates to. Use an empty string to remove webhook integration
        :return:
            True on success
        """
        paylaod = {'url': url}
        return requests.post(self.api_url + '/setWebhook', json=paylaod)

    @base_telegram_api_method
    def delete_webhook(self):
        """
        Use this method to remove webhook integration if you decide to switch back to getUpdates.

        :return:
            True on success
        """
        return requests.post(self.api_url + '/deleteWebhook')
