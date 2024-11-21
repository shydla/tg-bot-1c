import asyncio
import asyncssh
import re
from typing import Optional, List
from datetime import datetime

class SSHManager:
    # Словарь для отслеживания активных выгрузок (статический атрибут класса)
    active_backups = {}

    def __init__(self, host: str, username: str, password: str, db_server: str, 
                 db_user: str, db_pwd: str, user: str, user_pwd: str,
                 rclone_remote: str, rclone_path: str):
        self.host = host
        self.username = username
        self.password = password
        self.db_server = db_server
        self.db_user = db_user
        self.db_pwd = db_pwd
        self.user = user
        self.user_pwd = user_pwd
        self._conn = None
        self._platform_version = None
        self._platform_path = None
        self.backup_dir = "~/dump_1s_dt"
        self.rclone_remote = rclone_remote
        self.rclone_path = rclone_path

    @classmethod
    def is_backup_active(cls, db_name: str) -> bool:
        return db_name in cls.active_backups

    async def connect(self):
        try:
            self._conn = await asyncssh.connect(
                host=self.host,
                username=self.username,
                password=self.password,
                known_hosts=None
            )
            # При подключении сразу определяем версию и путь
            await self._detect_platform_version()
            # Создаем директорию для бэкапов, если её нет
            await self._ensure_backup_dir()
            return True
        except Exception as e:
            print(f"SSH connection error: {e}")
            return False

    async def _ensure_backup_dir(self):
        """Создает директорию для бэкапов, если она не существует"""
        try:
            # Раскрываем ~ в полный путь
            result = await self._conn.run('echo $HOME')
            home_dir = result.stdout.strip()
            self.backup_dir = f"{home_dir}/dump_1s_dt"
            
            # Создаем директорию, если её нет
            await self._conn.run(f'mkdir -p {self.backup_dir}')
        except Exception as e:
            print(f"Error creating backup directory: {e}")
            raise

    async def _detect_platform_version(self):
        try:
            # Получаем список процессов ragent
            result = await self._conn.run('ps aux | grep ragent | grep -v grep')
            output = result.stdout

            # Ищем версию в выводе
            version_pattern = r'(\d+\.\d+\.\d+\.\d+)'
            matches = re.findall(version_pattern, output)
            
            if matches:
                self._platform_version = matches[0]
                # Формируем путь на основе найденной версии
                self._platform_path = f"/opt/1cv8/x86_64/{self._platform_version}"
                return self._platform_version
            return None

        except Exception as e:
            print(f"Error detecting platform version: {e}")
            return None

    @property
    def rac_path(self) -> Optional[str]:
        if self._platform_path:
            return f"{self._platform_path}/rac"
        return None

    @property
    def dump_path(self) -> Optional[str]:
        if self._platform_path:
            return f"{self._platform_path}/1cv8"
        return None

    @property
    def ibcmd_path(self) -> Optional[str]:
        if self._platform_path:
            return f"{self._platform_path}/ibcmd"
        return None

    async def get_1c_databases(self) -> List[dict]:
        if not self._conn or not self.rac_path:
            if not await self.connect():
                return []

        try:
            # Сначала получаем список кластеров
            result = await self._conn.run(f'{self.rac_path} cluster list')
            if result.exit_status != 0:
                print(f"Error getting clusters: {result.stderr}")
                return []

            # Ищем ID кластера в выводе
            clusters = result.stdout.strip().split('\n')
            if not clusters:
                print("No clusters found")
                return []

            # Берем первый кластер и извлекаем его ID
            cluster_info = clusters[0].split(':')
            if len(cluster_info) < 2:
                print(f"Invalid cluster info: {clusters[0]}")
                return []

            cluster_id = cluster_info[1].strip()

            # Получаем список информационных баз для найденного кластера
            result = await self._conn.run(f'{self.rac_path} infobase --cluster={cluster_id} summary list')
            if result.exit_status != 0:
                print(f"Error getting databases: {result.stderr}")
                return []

            # Парсим вывод, ищем имена баз и их описания
            databases = []
            current_db = {}
            
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    if current_db:
                        databases.append(current_db)
                        current_db = {}
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'name' in key:
                        current_db['name'] = value
                    elif 'descr' in key:
                        current_db['descr'] = value
            
            # Добавляем последнюю базу, если она есть
            if current_db:
                databases.append(current_db)
            
            # Добавляем отладочную информацию
            print(f"Found databases: {databases}")
            
            return databases

        except Exception as e:
            print(f"Error getting 1C databases: {e}")
            return []

    async def create_database_backup(self, db_name: str) -> Optional[str]:
        if self.is_backup_active(db_name):
            return None

        if not self._conn or not self.ibcmd_path:
            if not await self.connect():
                return None

        try:
            self.__class__.active_backups[db_name] = True
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.backup_dir}/{db_name}_{timestamp}.dt"
            
            command = [
                self.ibcmd_path,
                "infobase",
                "dump",
                "--dbms=PostgreSQL",
                f"--db-server={self.db_server}",
                f"--db-user={self.db_user}",
                f"--db-pwd={self.db_pwd}",
                f"--user={self.user}",
                f"--password={self.user_pwd}",
                f"--db-name={db_name}",
                f"--data={self.backup_dir}/data",
                backup_path
            ]
            
            dump_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
            result = await self._conn.run(dump_command)
            
            if result.exit_status == 0:
                check_result = await self._conn.run(f'test -f "{backup_path}" && echo "exists"')
                if check_result.stdout.strip() == "exists":
                    await self._conn.run(f'rm -rf "{self.backup_dir}/data"')
                    
                    # Передаем имя базы в метод upload_to_cloud
                    cloud_link = await self.upload_to_cloud(backup_path, db_name)
                    return cloud_link

            return None

        except Exception as e:
            print(f"Error creating backup: {e}")
            try:
                await self._conn.run(f'rm -rf "{self.backup_dir}/data"')
            except:
                pass
            return None
        finally:
            self.__class__.active_backups.pop(db_name, None)

    async def get_1c_server_version(self) -> Optional[str]:
        if not self._platform_version:
            await self._detect_platform_version()
        return self._platform_version

    async def close(self):
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()

    async def upload_to_cloud(self, file_path: str, db_name: str) -> Optional[str]:
        """Загружает файл в облако и возвращает ссылку для скачивания"""
        try:
            # Формируем путь в облаке: remote:path/database_name/
            cloud_db_path = f"{self.rclone_remote}:{self.rclone_path}/{db_name}"
            
            # Очищаем папку базы в облаке
            clear_command = f'rclone purge "{cloud_db_path}"'
            await self._conn.run(clear_command)
            
            # Создаем папку заново
            mkdir_command = f'rclone mkdir "{cloud_db_path}"'
            await self._conn.run(mkdir_command)
            
            # Получаем имя файла из полного пути
            file_name = file_path.split('/')[-1]
            cloud_file_path = f"{cloud_db_path}/{file_name}"
            
            # Загружаем файл в облако
            copy_command = f'rclone copy "{file_path}" "{cloud_db_path}"'
            result = await self._conn.run(copy_command)
            
            if result.exit_status == 0:
                # Публикуем файл и получаем ссылку
                publish_command = f'rclone link "{cloud_file_path}"'
                publish_result = await self._conn.run(publish_command)
                
                if publish_result.exit_status == 0:
                    # Удаляем локальный файл
                    await self._conn.run(f'rm -f "{file_path}"')
                    
                    # Получаем ссылку и преобразуем её в формат для скачивания
                    share_link = publish_result.stdout.strip()
                    
                    # Преобразуем ссылку для Yandex.Disk
                    if 'disk.yandex.ru/d/' in share_link:
                        # Извлекаем хеш из ссылки
                        hash_part = share_link.split('/')[-1]
                        # Формируем прямую ссылку на скачивание
                        download_link = f"https://disk.yandex.ru/d/{hash_part}"
                        return download_link
                    
                    return share_link
            
            return None

        except Exception as e:
            print(f"Error uploading to cloud: {e}")
            return None