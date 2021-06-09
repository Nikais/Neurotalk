import errno
import json
import logging
import threading
import time

import parlai.chat_service.utils.logging as log_utils
import websocket
from parlai.chat_service.core.socket import ChatServiceMessageSocket

SOCKET_TIMEOUT = 6


# Socket handler
class TelegramServiceMessageSocket(ChatServiceMessageSocket):
    def __init__(self, server_url, port, message_callback):
        super().__init__(server_url, port, message_callback)

    def _setup_socket(self):
        """
        Create socket handlers and registers the socket.
        """

        def on_socket_open(*args):
            log_utils.print_and_log(
                logging.DEBUG, f'Socket open: {args}')
            self._send_world_alive()

        def on_error(ws, error):
            try:
                if error.errno == errno.ECONNREFUSED:
                    self._ensure_closed()
                    self.use_socket = False
                    raise Exception("Socket refused connection, cancelling")
                else:
                    log_utils.print_and_log(
                        logging.WARN, 'Socket logged error: {}'.format(repr(error))
                    )
            except BaseException:
                if type(error) is websocket.WebSocketConnectionClosedException:
                    return  # Connection closed is noop
                log_utils.print_and_log(
                    logging.WARN,
                    'Socket logged error: {} Restarting'.format(repr(error)),
                )
                self._ensure_closed()

        def on_disconnect(*args):
            """
            Disconnect event is a no-op for us, as the server reconnects automatically
            on a retry.
            """
            log_utils.print_and_log(
                logging.INFO, 'World server disconnected: {}'.format(args)
            )
            self.alive = False
            self._ensure_closed()

        def on_message(*args):
            """
            Incoming message handler for messages from the FB user.
            """
            packet_dict = json.loads(args[1])
            if packet_dict['type'] == 'conn_success':
                self.alive = True
                return  # No action for successful connection
            if packet_dict['type'] == 'pong':
                self.last_pong = time.time()
                return  # No further action for pongs
            message_data = packet_dict['content']
            log_utils.print_and_log(
                logging.DEBUG, f'Message data received: {message_data}'
            )
            self.message_callback(message_data)

        def run_socket(*args):
            url_base_name = self.server_url.split('https://')[1]
            while self.keep_running:
                try:
                    sock_addr = "wss://{}/".format(url_base_name)
                    self.ws = websocket.WebSocketApp(
                        sock_addr,
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_disconnect,
                    )
                    self.ws.on_open = on_socket_open
                    self.ws.run_forever(ping_interval=1, ping_timeout=0.9)
                except Exception as e:
                    log_utils.print_and_log(
                        logging.WARN,
                        'Socket error {}, attempting restart'.format(repr(e)),
                    )
                time.sleep(0.2)

        # Start listening thread
        self.listen_thread = threading.Thread(
            target=run_socket, name='Main-Socket-Thread'
        )
        self.listen_thread.daemon = True
        self.listen_thread.start()
        time.sleep(1.2)
        while not self.alive:
            try:
                self._send_world_alive()
            except Exception:
                pass
            time.sleep(0.8)
