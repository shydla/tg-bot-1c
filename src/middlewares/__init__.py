from aiogram import Dispatcher
from .database import DatabaseMiddleware
from database import Database

def register_all_middlewares(dp: Dispatcher, db: Database):
    dp.middleware.setup(DatabaseMiddleware(db)) 