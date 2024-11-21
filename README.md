# 1C Backup Telegram Bot

Telegram бот для создания резервных копий баз 1С и выгрузки их в Яндекс.Диск.

## Возможности

- 💾 Создание резервных копий баз 1С без прерывания работы пользователей
- 🔄 Использование ibcmd для "горячего" бэкапа работающих баз
- 👥 Система регистрации пользователей с подтверждением администратором
- ☁️ Автоматическая выгрузка бэкапов в Яндекс.Диск
- 🔒 Разграничение прав доступа
- 📊 Управление пользователями

## Особенности работы

### Непрерывное резервное копирование

- ✨ Выгрузка баз данных происходит без остановки работы пользователей
- 🔄 Создание резервных копий возможно в любое время рабочего дня
- 💼 Пользователи могут продолжать работу во время выгрузки
- ⚡ Использование современного механизма ibcmd обеспечивает целостность данных
- 🛡️ Безопасное копирование без блокировки базы

## Требования

- Python 3.8+
- Poetry
- Docker и Docker Compose (для развертывания)
- Настроенный rclone с доступом к Яндекс.Диску
- Доступ к серверу 1С по SSH

## Установка и запуск

### Предварительные требования

1. Установите Docker и Docker Compose:
```bash
# Для Ubuntu
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
```

### Настройка Rclone

1. Установите Rclone на сервер:
```bash
curl https://rclone.org/install.sh | sudo bash
```

2. Настройте подключение к Яндекс.Диску:
```bash
rclone config
# Выберите "n" для создания нового remote
# Введите имя (например, "yadisk")
# Выберите "Yandex Disk" из списка
# Следуйте инструкциям для авторизации
```

### Развертывание бота

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/1c-backup-bot.git
cd 1c-backup-bot
```

2. Создайте и настройте файл окружения:
```bash
cp .env.example .env
nano .env
```

Пример содержимого `.env`:
```env
# Bot settings
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # Получите у @BotFather
ADMIN_ID=123456789  # Ваш Telegram ID (можно узнать у @userinfobot)

# SSH connection
SSH_HOST=192.168.1.100  # IP сервера 1С
SSH_USERNAME=user  # Пользователь SSH
SSH_PASSWORD=password  # Пароль SSH

# Database connection
DB_SERVER=localhost
DB_USER=postgres
DB_PASSWORD=postgres

# 1C connection
USER_1C=Admin
USER_1C_PASSWORD=123

# Rclone settings
RCLONE_REMOTE=yadisk  # Имя remote из настроек rclone
RCLONE_PATH=backup/1c  # Путь в облаке для сохранения бэкапов
```

3. Соберите и запустите контейнеры:
```bash
# Сборка и запуск
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f bot
```

### Проверка работоспособности

1. Откройте бота в Telegram
2. Отправьте команду `/start`
3. Если вы админ (ваш ID указан в ADMIN_ID), вы получите полный доступ
4. Другие пользователи должны получить одобрение от админа

### Обновление бота

Для обновления до последней версии:
```bash
# Остановите контейнеры
docker-compose down

# Получите последние изменения
git pull

# Пересоберите и запустите контейнеры
docker-compose up -d --build
```

### Обслуживание

#### Просмотр логов:
```bash
# Все логи
docker-compose logs -f

# Только логи бота
docker-compose logs -f bot
```

#### Перезапуск бота:
```bash
docker-compose restart bot
```

#### Очистка неиспользуемых образов:
```bash
docker system prune -a
```

### Устранение неполадок

1. Если бот не отвечает:
   - Проверьте логи: `docker-compose logs -f bot`
   - Убедитесь, что токен бота правильный
   - Проверьте подключение к интернету

2. Если не работает выгрузка баз:
   - Проверьте SSH подключение
   - Убедитесь, что путь к утилитам 1С правильный
   - Проверьте права доступа пользователя SSH

3. Если не работает загрузка в Яндекс.Диск:
   - Проверьте настройки rclone
   - Убедитесь, что токен Яндекс.Диска не истек
   - Проверьте наличие свободного места в облаке

### Безопасность

1. Регулярно меняйте пароли
2. Используйте сложные пароли
3. Ограничьте доступ к серверу по SSH
4. Регулярно обновляйте систему и компоненты

### Резервное копирование

Рекомендуется регулярно создавать резервную копию файла базы данных бота:
```bash
# Создание бэкапа базы бота
docker-compose exec bot cp /app/bot.db /app/bot.db.backup
```

## Команды бота

- `/start` - Начало работы с ботом
- `/backup` - Создание резервной копии базы
- `/users` - Список пользователей (только для админа)
- `/pending` - Список ожидающих подтверждения (только для админа)

## Структура проекта
```
1c-backup-bot/
├── src/
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   ├── ssh_manager.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── user.py
│   └── middlewares/
│       ├── __init__.py
│       └── database.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── poetry.lock
└── README.md
```

## Лицензия

MIT

## Автор

Your Name <shydla@gmail.com>

## Вклад в проект

1. Форкните проект
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте изменения в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Поддержка

Если у вас возникли проблемы или есть предложения по улучшению, создайте Issue в репозитории.

