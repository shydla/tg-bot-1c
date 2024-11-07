from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

@dataclass
class TgBot:
    token: str
    admin_id: str

@dataclass
class Config:
    tg_bot: TgBot

def load_config() -> Config:
    load_dotenv()
    
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN"),
            admin_id=getenv("ADMIN_ID")
        )
    ) 