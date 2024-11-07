from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import Database

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, database: Database):
        super().__init__()
        self.database = database

    async def on_pre_process_message(self, message: Message, data: dict):
        data["db"] = self.database

    async def on_pre_process_callback_query(self, callback_query: CallbackQuery, data: dict):
        data["db"] = self.database

    async def on_post_process_message(self, message: Message, data: dict, *args):
        if "db" in data:
            del data["db"]

    async def on_post_process_callback_query(self, callback_query: CallbackQuery, data: dict, *args):
        if "db" in data:
            del data["db"]