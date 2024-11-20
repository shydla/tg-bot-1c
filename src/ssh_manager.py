import asyncio
import asyncssh
import re
from typing import Optional, List
from datetime import datetime

class SSHManager:
    def __init__(self, host: str, username: str, password: str, db_server: str, 
                 db_user: str, db_pwd: str, user: str, user_pwd: str):
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

    async def get_1c_databases(self) -> List[str]:
        if not self._conn or not self.rac_path:
            if not await self.connect():
                return []

        try:
            # Получаем список кластеров
            result = await self._conn.run(f'{self.rac_path} cluster list')
            cluster_id = result.stdout.split()[2]  # Берем первый кластер

            # Получаем список информационных баз
            result = await self._conn.run(f'{self.rac_path} infobase --cluster={cluster_id} summary list')
            
            # Парсим вывод, ищем имена баз
            databases = []
            for line in result.stdout.splitlines():
                if 'name' in line.lower():
                    db_name = line.split(':')[1].strip()
                    databases.append(db_name)
            
            return databases

        except Exception as e:
            print(f"Error getting 1C databases: {e}")
            return []

    async def create_database_backup(self, db_name: str) -> Optional[str]:
        if not self._conn or not self.ibcmd_path:
            if not await self.connect():
                return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.backup_dir}/{db_name}_{timestamp}.dt"
            
            # Формируем команду для ibcmd с параметрами из конфига
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
            
            # Объединяем команду в строку для выполнения через SSH
            dump_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
            result = await self._conn.run(dump_command)
            
            if result.exit_status == 0:
                # Проверяем, что файл действительно создан
                check_result = await self._conn.run(f'test -f "{backup_path}" && echo "exists"')
                if check_result.stdout.strip() == "exists":
                    # Очищаем временную директорию с данными
                    await self._conn.run(f'rm -rf "{self.backup_dir}/data"')
                    return backup_path
            return None

        except Exception as e:
            print(f"Error creating backup: {e}")
            # В случае ошибки тоже пытаемся очистить временную директорию
            try:
                await self._conn.run(f'rm -rf "{self.backup_dir}/data"')
            except:
                pass
            return None

    async def get_1c_server_version(self) -> Optional[str]:
        if not self._platform_version:
            await self._detect_platform_version()
        return self._platform_version

    async def close(self):
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()