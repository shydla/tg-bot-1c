from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import load_config
from ssh_manager import SSHManager

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

    # Получаем только пользовател в оидании
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

async def cmd_databases(message: types.Message, db=None):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user['status'] != 'approved':
        await message.answer("У вас нет доступа к этой команде.")
        return

    config = load_config()
    ssh = SSHManager(
        host=config.ssh.host,
        username=config.ssh.username,
        password=config.ssh.password,
        db_server=config.ssh.db_server,
        db_user=config.ssh.db_user,
        db_pwd=config.ssh.db_pwd,
        user=config.ssh.user,
        user_pwd=config.ssh.user_pwd,
        rclone_remote=config.ssh.rclone_remote,
        rclone_path=config.ssh.rclone_path
    )

    try:
        databases = await ssh.get_1c_databases()
        if not databases:
            await message.answer("Не удалось получить список баз данных")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        active_backups_msg = []

        # Добавляем кнопки для баз данных
        for db_info in databases:
            db_name = db_info['name']
            db_descr = db_info.get('descr', 'Без описания')
            
            # Формируем текст кнопки
            button_text = f"💾 {db_name}  - "
            if db_descr:
                button_text += f"📝 ({db_descr})"

            if SSHManager.is_backup_active(db_name):
                markup.add(InlineKeyboardButton(
                    text=f"🔄 {button_text} (выгрузка...)",
                    callback_data="backup_in_progress"
                ))
                active_backups_msg.append(db_name)
            else:
                markup.add(InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"backup_{db_name}"
                ))

        # Добавляем кнопку отмены
        markup.add(InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="backup_cancel"
        ))

        msg_text = "📋 Выберите базу для создания резервной копии:"
        if active_backups_msg:
            msg_text += f"\n\n⚠️ Выгрузка уже идет для баз: {', '.join(active_backups_msg)}"

        await message.answer(msg_text, reply_markup=markup)

    except Exception as e:
        await message.answer(f"Произошла ошибка при получении списка баз: {str(e)}")
    finally:
        await ssh.close()

async def process_backup_callback(callback: types.CallbackQuery, db=None):
    # Обработка кнопки отмены
    if callback.data == "backup_cancel":
        await callback.message.delete()
        await callback.answer("Операция отменена")
        return

    if callback.data == "backup_in_progress":
        await callback.answer("Выгрузка этой базы уже идет!", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    
    if not user or user['status'] != 'approved':
        await callback.answer("У вас нет доступа к этой команде.", show_alert=True)
        return

    db_name = callback.data.split('_')[1]

    if SSHManager.is_backup_active(db_name):
        await callback.answer("Выгрузка этой базы уже идет!", show_alert=True)
        return

    await callback.answer(f"Создаю резервную копию базы {db_name}...", show_alert=False)

    config = load_config()
    ssh = SSHManager(
        host=config.ssh.host,
        username=config.ssh.username,
        password=config.ssh.password,
        db_server=config.ssh.db_server,
        db_user=config.ssh.db_user,
        db_pwd=config.ssh.db_pwd,
        user=config.ssh.user,
        user_pwd=config.ssh.user_pwd,
        rclone_remote=config.ssh.rclone_remote,
        rclone_path=config.ssh.rclone_path
    )

    try:
        await callback.message.delete()
        status_message = await callback.message.answer(
            f"🔄 Начата выгрузка базы {db_name}...\n"
            f"⏳ Пожалуйста, подождите..."
        )
        
        cloud_link = await ssh.create_database_backup(db_name)
        if cloud_link:
            await status_message.edit_text(
                f"✅ Резервная копия базы {db_name} успешно создана!\n\n"
                f"📥 Ссылка на Яндекс.Диск:\n{cloud_link}\n\n"
                f"ℹ️ Для скачивания:\n"
                f"1. Перейдите по ссылке\n"
                f"2. Нажмите кнопку 'Скачать' на странице Яндекс.Диска"
            )
        else:
            await status_message.edit_text(
                f"❌ Не удалось создать резервную копию базы {db_name} "
                f"или загрузить её в облако"
            )

    except Exception as e:
        await callback.message.answer(f"Произошла ошибка: {str(e)}")
    finally:
        await ssh.close()

def register_user_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, Command("start"))
    dp.register_message_handler(cmd_users, Command("users"))
    dp.register_message_handler(cmd_pending, Command("pending"))
    dp.register_message_handler(cmd_databases, Command("backup"))
    dp.register_callback_query_handler(
        process_callback,
        lambda c: c.data.startswith(('approve_', 'block_'))
    )
    dp.register_callback_query_handler(
        process_backup_callback,
        lambda c: c.data.startswith('backup_')
    )