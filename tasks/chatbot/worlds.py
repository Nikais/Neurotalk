from parlai.core.agents import create_agent_from_shared
from parlai.core.worlds import World
from parlai.chat_service.services.messenger.worlds import OnboardWorld


# ---------- Chatbot demo ---------- #
class TelegramBotOnboardWorld(OnboardWorld):
    """
    Example telegram onboarding world for Chatbot Model.
    """
    def __init__(self, opt, agent):
        super().__init__(opt, agent)

    @staticmethod
    def generate_world(opt, agents):
        return TelegramBotOnboardWorld(opt=opt, agent=agents[0])

    def parley(self):
        self.agent.observe({
            'id': 'OnBoardWorld',
            'text': 'Welcome to the Telegram Chatbot demo. '
            'You are now paired with a bot - feel free to send a message. '
            'Type /done to finish the chat, or /reset to reset the dialogue history.'
        })
        self.episodeDone = True

    def episode_done(self):
        return self.episodeDone


class TelegramBotChatTaskWorld(World):
    """
    Example one person world that talks to a provided agent (bot).
    """

    MAX_AGENTS = 1
    MODEL_KEY = 'blender_90M'

    def __init__(self, opt, agent, bot):
        self.agent = agent
        self.episodeDone = False
        self.model = bot

    @staticmethod
    def generate_world(opt, agents):
        if opt['models'] is None:
            raise RuntimeError("Model must be specified")
        return TelegramBotChatTaskWorld(
            opt,
            agents[0],
            create_agent_from_shared(
                opt['shared_bot_params'][TelegramBotChatTaskWorld.MODEL_KEY]
            ),
        )

    @staticmethod
    def assign_roles(agents):
        agents[0].disp_id = 'TelegramAgent'

    def parley(self):
        a = self.agent.act()
        if a is not None:
            if a['text'][:1] == '/':
                if '/done' in a['text']:
                    self.episodeDone = True
                elif '/reset' in a['text']:
                    self.model.reset()
                    self.agent.observe({
                        "text": "[History Cleared]",
                        "episode_done": False
                    })
                else:
                    self.agent.observe({
                        "text": "Invalid option. "
                        "Please type /done to finish the chat or "
                        "/reset to reset the dialogue history",
                        "episode_done": False
                    })
            else:
                print(f"Agent act: {a}")
                self.model.observe(a)
                response = self.model.act()
                print(f"Model response: {response}")
                self.agent.observe(response)

    def episode_done(self):
        return self.episodeDone

    def shutdown(self):
        self.agent.shutdown()


# ---------- Overworld -------- #
class TelegramOverworld(World):
    """
    World to handle moving agents to their proper places.
    """

    def __init__(self, opt, agent):
        self.agent = agent
        self.opt = opt
        self.first_time = True
        self.episodeDone = False

    @staticmethod
    def generate_world(opt, agents):
        return TelegramOverworld(opt, agents[0])

    @staticmethod
    def assign_roles(agents):
        for a in agents:
            a.disp_id = 'Agent'

    def episode_done(self):
        return self.episodeDone

    def parley(self):
        if self.first_time:
            self.agent.observe(
                {
                    'id': 'Overworld',
                    'text': r'Welcome to the overworld for the ParlAI Telegram chatbot '
                    'demo. Please type /begin to start, or /exit to exit.'
                }
            )
            self.first_time = False
        a = self.agent.act()
        if a is not None:
            if a['text'] == '/exit':
                self.episodeDone = True
                return 'exit'
            if a['text'] == '/begin':
                self.episodeDone = True
                return 'default'
            else: self.agent.observe({
                    'id': 'Overworld',
                    'text': 'Invalid option. Please type /begin or /exit.'
                })