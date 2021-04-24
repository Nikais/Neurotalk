import parlai.chat_service.utils.config as config_utils

from telegram.parser import Parser
from telegram.telegram_manager import TelegramManager

SERVICE_NAME = 'telegram'

if __name__ == '__main__':
    # Setup args
    parser = Parser(False, False)
    parser.add_parlai_data_path()
    parser.add_telegram_args()

    # Parse args from console
    opt = parser.parse_args()

    # Get config args
    config_path = opt.get('config_path')
    config = config_utils.parse_configuration_file(config_path)
    opt.update(config['world_opt'])
    opt['config'] = config

    # Start TelegramManager
    opt['service'] = SERVICE_NAME
    manager = TelegramManager(opt)
    try:
        manager.start_task()
    except BaseException:
        raise
    finally:
        manager.shutdown()
