import time

from parlai.chat_service.core.agents import ChatServiceAgent
from parlai.core.message import Message


class TelegramAgent(ChatServiceAgent):
    """
    Base class for a person on Telegram that can act in a ParlAI world.
    """
    def __init__(self, opt, manager, receiver_id, task_id):
        super().__init__(opt, manager, receiver_id, task_id)
        self.disp_id = 'TelegramUser'

    def _is_image_attempt(self, message):
        img_attempt = False
        if 'document' in message:
            img_attempt = message['document']['mime_type'] == 'image/jpeg'
        elif 'photo' in message:
            img_attempt = True
        return img_attempt

    def act(self, timeout=None):
        """
        Pulls a message from the message queue.

        If none exist returns None unless the timeout has expired.
        """
        # if this is the first act since last sent message start timing
        if self.message_request_time is None:
            self.message_request_time = time.time()

        # If checking timeouts
        if timeout:
            # If time is exceeded, timeout
            if time.time() - self.message_request_time > timeout:
                return self.mark_inactive()

        msg = self.get_new_act_message()

        if msg is not None:
            if msg.get('img_attempt') and not self.data.get('allow_images', False):
                # Let agent know that they cannot send images if they
                # attempted to send one
                msg = None
                act = {
                    'id': 'SYSTEM',
                    'text': 'Only text messages are supported at this time. '
                            'Please try with a text-only message.',
                    'episode_done': True,
                }
                self.observe(act)
            elif not msg.get('text'):
                # Do not allow agent to send empty strings
                msg = None
                act = {
                    'id': 'SYSTEM',
                    'text': 'Only text messages are supported at this time. '
                            'Please try with a text-only message.',
                    'episode_done': True,
                }
                self.observe(act)
            if self.message_request_time is not None:
                self.message_request_time = None

        return msg

    def mark_inactive(self):
        # some kind of behavior to send a message when a user is marked as
        # being inactive. Could be useful. Should return a message to be sent
        pass

    def observe(self, act):  # TODO Need to check it
        """
        Send an agent a message through the manager.
        """
        msg = act['text']
        resp = self.manager.observe_message(
            self.id,
            msg,
            act.get('quick_replies', None),
            act.get('persona_id', None),
        )
        try:
            mid = resp['message_id']
            if mid not in self.observed_packets:
                self.observed_packets[mid] = act
        except Exception:
            print(f'{resp} could not be extracted to an observed message.')

    def put_data(self, message):
        """
        Put data into the message queue if it hasn't already been seen.
        """
        mid = message['mid']
        if 'text' not in message:
            print('Msg: {} could not be extracted to text format'.format(message))
        text = message.get('text', None)
        recipient = message['recipient'].get('id', None)
        img_attempt = self._is_image_attempt(message)
        if mid not in self.acted_packets:
            self.acted_packets[mid] = {'mid': mid, 'text': text}
            action = {
                'episode_done': False,
                'text': text,
                'id': recipient,
                'img_attempt': img_attempt
            }
            self.msg_queue.put(action)
