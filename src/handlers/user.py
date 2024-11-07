from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import load_config

config = load_config()
ADMIN_ID = int(config.tg_bot.admin_id)

async def cmd_start(message: types.Message, db=None):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if user_id == ADMIN_ID:
        await message.answer("Добро пожаловать, администратор!")
        await db.add_user(
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        await db.update_user_status(user_id, "approved")
        return

    # Получаем информацию о пользователе из БД
    user = await db.get_user(user_id)
    
    if user is None:
        # Новый пользователь
        await db.add_user(
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        await message.answer("Ваша заявка отправлена администратору. Ожидайте подтверждения.")
        
        # Отправляем уведомление админу
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Разрешить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("Заблокировать", callback_data=f"block_{user_id}")
        )
        
        await message.bot.send_message(
            ADMIN_ID,
            f"Новый пользователь запрашивает доступ:\n"
            f"ID: {user_id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Username: @{message.from_user.username}",
            reply_markup=markup
        )
    else:
        # Существующий пользователь
        if user['status'] == 'approved':
            await message.answer("Добро пожаловать! У вас есть доступ к боту.")
        elif user['status'] == 'blocked':
            reason = user['blocked_reason'] or 'Причина не указана'
            await message.answer(f"Вы заблокированы.\nПричина: {reason}")
        else:
            await message.answer("Ваша заявка находится на рассмотрении.")

async def process_callback(callback: types.CallbackQuery, db=None):
    action, user_id = callback.data.split('_')
    user_id = int(user_id)
    
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    # Проверка на попытку заблокировать админа
    if user_id == ADMIN_ID and action == "block":
        await callback.answer("Невозможно заблокировать администратора!", show_alert=True)
        return

    if action == "approve":
        await db.update_user_status(user_id, "approved")
        await callback.bot.send_message(user_id, "Администратор одобрил вашу заявку. Теперь у вас есть доступ к боту!")
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ Одобрено"
        )
    elif action == "block":
        await db.update_user_status(user_id, "blocked", "Заблокировано администратором")
        await callback.bot.send_message(user_id, "Администратор отклонил вашу заявку.")
        await callback.message.edit_text(
            f"{callback.message.text}\n\n❌ Заблокировано"
        )

    await callback.answer()

async def cmd_users(message: types.Message, db=None):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав администратора!")
        return

    # Получаем всех пользователей
    users = await db.get_users_by_status()
    
    if not users:
        await message.answer("Пользователей пока нет.")
        return

    # Создаем сообщение со списком пользователей
    for user in users:
        # Пропускаем админа в списке
        if user['user_id'] == ADMIN_ID:
            continue
            
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'blocked': '❌'
        }.get(user['status'], '❓')
        
        markup = InlineKeyboardMarkup(row_width=2)
        
        # Для пользователей показываем кнопки в зависимости от статуса
        if user['status'] == 'approved':
            markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"block_{user['user_id']}"))
        elif user['status'] == 'blocked':
            markup.add(InlineKeyboardButton("Разрешить", callback_data=f"approve_{user['user_id']}"))
        else:  # pending
            markup.add(
                InlineKeyboardButton("Разрешить", callback_data=f"approve_{user['user_id']}"),
                InlineKeyboardButton("Заблокировать", callback_data=f"block_{user['user_id']}")
            )

        user_text = (
            f"👤 Пользователь: {user['full_name']}\n"
            f"🆔 ID: {user['user_id']}\n"
            f"👤 Username: @{user['username']}\n"
            f"📅 Дата регистрации: {user['created_at']}\n"
            f"📊 Статус: {status_emoji} {user['status']}\n"
        )
        
        if user['status'] == 'blocked' and user['blocked_reason']:
            user_text += f"❌ Причина блокировки: {user['blocked_reason']}\n"

        await message.answer(user_text, reply_markup=markup)

async def cmd_pending(message: types.Message, db=None):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав администратора!")
        return

    # Получаем только пользователей в ожидании
    users = await db.get_users_by_status('pending')
    
    if not users:
        await message.answer("Нет пользователей в ожидании одобрения.")
        return

    for user in users:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Разрешить", callback_data=f"approve_{user['user_id']}"),
            InlineKeyboardButton("Заблокировать", callback_data=f"block_{user['user_id']}")
        )

        await message.answer(
            f"👤 Пользователь: {user['full_name']}\n"
            f"🆔 ID: {user['user_id']}\n"
            f"👤 Username: @{user['username']}\n"
            f"📅 Дата регистрации: {user['created_at']}\n"
            f"📊 Статус: ⏳ в ожидании",
            reply_markup=markup
        )

def register_user_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, Command("start"))
    dp.register_message_handler(cmd_users, Command("users"))
    dp.register_message_handler(cmd_pending, Command("pending"))
    dp.register_callback_query_handler(
        process_callback,
        lambda c: c.data.startswith(('approve_', 'block_'))
    )