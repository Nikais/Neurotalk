from parlai.core.params import ParlaiParser


class Parser(ParlaiParser):
    """
    Provide an opt-producer and CLI argument parser.

    Pseudo-extension of ``argparse`` which sets a number of parameters
    for the ParlAI framework. More options can be added specific to other
    modules by passing this object and calling ``add_arg()`` or
    ``add_argument()`` on it.

    For an example, see ``parlai.core.dict.DictionaryAgent.add_cmdline_args``.

    :param add_parlai_args:
        (default True) initializes the default arguments for ParlAI
        package, including the data download paths and task arguments.
    :param add_model_args:
        (default False) initializes the default arguments for loading
        models, including initializing arguments from that model.
    """

    def __init__(self, add_parlai_args=True, add_model_args=False, description=None, **kwargs):
        """
        Initialize the Parlai parser with add_telgram_args implementation.
        """
        super().__init__(add_parlai_args, add_model_args, description, **kwargs)

    def add_telegram_args(self):
        """
        Add Telegram arguments
        """
        self.add_chatservice_args()
        telegram = self.add_argument_group('Telegram')
        telegram.add_argument(
            '--verbose',
            dest='verbose',
            action='store_true',
            help='print all messages sent to and from Turkers'
        )
        telegram.add_argument(
            '--log-level',
            dest='log_level',
            type=int,
            default=20,
            help='importance level for what to put into the logs. the lower '
                 'the level the more that gets logged. values are 0-50',
        )
        telegram.add_argument(
            '--force-telegram-bot-token',
            dest='force_telegram_bot_token',
            action='store_true',
            help='override the page token stored in the cache for a new one',
        )
        telegram.add_argument(
            '--bypass-server-setup',
            dest='bypass_server_setup',
            action='store_true',
            default=False,
            help='should bypass traditional server and socket setup',
        )
        telegram.add_argument(
            '--local',
            dest='local',
            action='store_true',
            default=False,
            help='Run the server locally on this server rather than setting up'
                 ' a heroku server.',
        )
        telegram.set_defaults(is_debug=False)
        telegram.set_defaults(verbose=False)
