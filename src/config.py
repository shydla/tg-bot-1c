from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

@dataclass
class TgBot:
    token: str
    admin_id: str

@dataclass
class SSH:
    host: str
    username: str
    password: str
    db_server: str
    db_user: str
    db_pwd: str
    user: str
    user_pwd: str

@dataclass
class Config:
    tg_bot: TgBot
    ssh: SSH

def load_config() -> Config:
    load_dotenv()
    
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN"),
            admin_id=getenv("ADMIN_ID")
        ),
        ssh=SSH(
            host=getenv("SSH_HOST"),
            username=getenv("SSH_USERNAME"),
            password=getenv("SSH_PASSWORD"),
            db_server=getenv("DB_SERVER", "localhost"),
            db_user=getenv("DB_USER", "postgres"),
            db_pwd=getenv("DB_PASSWORD", "postgres"),
            user=getenv("USER_1C", "Admin"),
            user_pwd=getenv("USER_1C_PASSWORD", "123")
        )
    ) 