import os
import json
import subprocess
import uuid
import datetime
import hashlib
from typing import List, Dict, Optional


class VersionManager:
    """
    Простая система версионирования через git.
    Создает отдельный репозиторий для каждого файла.
    Сохраняет состояние проекта в git после каждого действия.
    Undo/Redo работают через git checkout.
    """

    # Центральная директория для хранения всех репозиториев
    HISTORY_BASE_DIR = os.path.join(os.path.curdir, ".editor_history")
    MAPPING_FILE = os.path.join(HISTORY_BASE_DIR, "file_mapping.json")

    def __init__(self, file_path: Optional[str], controller):
        """
        Инициализация менеджера версий

        Args:
            file_path: Путь к редактируемому файлу (None для unsaved файлов)
            controller: Ссылка на controller из graphical.py для сохранения/загрузки
        """
        self.controller = controller
        self.file_path = file_path
        self.repository_id = None
        
        # Инициализируем базовую директорию
        os.makedirs(self.HISTORY_BASE_DIR, exist_ok=True)
        
        # Загружаем маппинг файлов
        self.mapping = self._load_mapping()
        
        # Определяем или создаем репозиторий для файла
        if file_path:
            # Для сохраненных файлов используем хеш пути или существующий репозиторий
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            self.repository_id = self._get_or_create_repository_id(normalized_path)
        else:
            # Для unsaved файлов создаем новый UUID
            self.repository_id = str(uuid.uuid4())
            print(f"Created new repository for unsaved file: {self.repository_id}")
        
        # Настраиваем пути
        self.git_dir = os.path.join(self.HISTORY_BASE_DIR, self.repository_id)
        self.filename = "project_state.json"
        self.project_file = os.path.join(self.git_dir, self.filename)

        # Инициализация git репозитория
        self._init_git()

        # Текущий указатель на коммит (для отслеживания позиции в истории)
        self.current_commit = self._get_current_commit()

        # Проверяем и фиксируем изменения, если файл был изменен вне редактора
        if file_path and os.path.exists(file_path):
            self._sync_external_changes()

    def _load_mapping(self) -> Dict:
        """Загрузить маппинг файлов из JSON"""
        if os.path.exists(self.MAPPING_FILE):
            try:
                with open(self.MAPPING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading mapping file: {e}")
        return {}

    def _save_mapping(self):
        """Сохранить маппинг файлов в JSON"""
        try:
            with open(self.MAPPING_FILE, "w", encoding="utf-8") as f:
                json.dump(self.mapping, f, indent=2)
        except Exception as e:
            print(f"Error saving mapping file: {e}")

    def _get_or_create_repository_id(self, file_path: str) -> str:
        """Получить или создать ID репозитория для файла"""
        # Проверяем, есть ли уже репозиторий для этого файла
        if file_path in self.mapping:
            return self.mapping[file_path]
        
        # Создаем новый ID репозитория на основе хеша пути
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:16]
        repo_id = f"file_{path_hash}"
        
        # Сохраняем маппинг
        self.mapping[file_path] = repo_id
        self._save_mapping()
        
        return repo_id

    def associate_with_file(self, file_path: str):
        """Связать текущий репозиторий с файлом"""
        normalized_path = os.path.normpath(os.path.abspath(file_path))
        
        # Если для этого файла уже есть другой репозиторий, используем его
        if normalized_path in self.mapping:
            existing_repo_id = self.mapping[normalized_path]
            if existing_repo_id != self.repository_id:
                # Сохраняем текущее состояние в текущий репозиторий перед переключением
                try:
                    # Сохраняем текущее состояние в текущий репозиторий
                    self.controller.save_scene(self.project_file)
                    subprocess.run(["git", "-C", self.git_dir, "add", "-f", self.filename], check=False)
                    subprocess.run(["git", "-C", self.git_dir, "commit", "-m", f"Final state before file association"], check=False)
                except Exception:
                    pass
                
                # Переключаемся на существующий репозиторий
                old_repo_id = self.repository_id
                self.repository_id = existing_repo_id
                self.git_dir = os.path.join(self.HISTORY_BASE_DIR, self.repository_id)
                self.project_file = os.path.join(self.git_dir, self.filename)
                self.file_path = normalized_path
                self.current_commit = self._get_current_commit()
                
                # Копируем текущее состояние файла в новый репозиторий
                if os.path.exists(file_path):
                    try:
                        # Сохраняем файл в новый репозиторий и коммитим
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        with open(self.project_file, "w", encoding="utf-8") as f:
                            f.write(content)
                        subprocess.run(["git", "-C", self.git_dir, "add", "-f", self.filename], check=False)
                        subprocess.run(["git", "-C", self.git_dir, "commit", "-m", f"Associated with file: {os.path.basename(file_path)}"], check=False)
                        self.current_commit = self._get_current_commit()
                    except Exception as e:
                        print(f"Error copying state to existing repository: {e}")
                
                print(f"Switched to existing repository {self.repository_id} for file {normalized_path}")
                return
        
        # Связываем текущий репозиторий с файлом
        self.file_path = normalized_path
        self.mapping[normalized_path] = self.repository_id
        self._save_mapping()
        
        print(f"Associated repository {self.repository_id} with file {normalized_path}")

    def _init_git(self):
        """Инициализация git репозитория"""
        try:
            # Проверяем, есть ли уже git репозиторий в директории проекта
            if not self._git_repo_exists():
                subprocess.run(["git", "init", self.git_dir], check=True)
                # Настраиваем git, чтобы избежать ошибок с именем пользователя и email
                subprocess.run(["git", "-C", self.git_dir, "config", "user.name", "NetlistEditor"], check=True)
                subprocess.run(["git", "-C", self.git_dir, "config", "user.email", "netlist@editor.local"], check=True)

                # Создаем начальный файл для первого коммита (если его нет)
                if not os.path.exists(self.project_file):
                    with open(self.project_file, "w", encoding="utf-8") as f:
                        json.dump({"blocks": []}, f, indent=2)
                    subprocess.run(["git", "-C", self.git_dir, "add", "-f", self.filename], check=True)
                    subprocess.run(["git", "-C", self.git_dir, "commit", "-m", "Initial commit"], check=True)
        except Exception as e:
            print(f"Ошибка при инициализации git: {e}")

    def _git_repo_exists(self) -> bool:
        """Проверяет, существует ли git репозиторий в специальной поддиректории"""
        try:
            # Проверяем наличие .git внутри git_dir
            git_subdir = os.path.join(self.git_dir, ".git")
            return os.path.exists(git_subdir) and os.path.isdir(git_subdir)
        except:
            return False

    def _sync_external_changes(self):
        """Синхронизирует изменения файла, если он был изменен вне редактора"""
        # Синхронизируем внешний файл с внутренним файлом репозитория
        if self.file_path and os.path.exists(self.file_path):
            try:
                # Сохраняем текущее состояние во внешний файл в репозиторий
                # Копируем содержимое внешнего файла в файл репозитория
                with open(self.file_path, "r", encoding="utf-8") as f:
                    external_content = f.read()
                
                # Сохраняем во временный файл репозитория для сравнения
                if os.path.exists(self.project_file):
                    with open(self.project_file, "r", encoding="utf-8") as f:
                        repo_content = f.read()
                else:
                    repo_content = None

                # Если содержимое отличается, коммитим изменения
                if external_content != repo_content:
                    # Сохраняем внешний файл в репозиторий
                    with open(self.project_file, "w", encoding="utf-8") as f:
                        f.write(external_content)
                    
                    print("Обнаружены внешние изменения файла, фиксируем в git...")
                    # Добавляем и коммитим изменения
                    subprocess.run(["git", "-C", self.git_dir, "add", "-f", self.filename], check=True)
                    commit_message = f"External changes - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    subprocess.run(["git", "-C", self.git_dir, "commit", "-m", commit_message], check=True)
                    # Обновляем текущий коммит
                    result = subprocess.run(
                        ["git", "-C", self.git_dir, "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    self.current_commit = result.stdout.strip()
                    print(f"Внешние изменения зафиксированы: {commit_message}, коммит: {self.current_commit[:7]}")
            except Exception as e:
                print(f"Ошибка при синхронизации внешних изменений: {e}")

    def save_state(self, action_name: str, save_to_file: Optional[str] = None):
        """
        Сохранить текущее состояние проекта в git

        Args:
            action_name: Описание действия для сообщения коммита
            save_to_file: Если указан, сохранить также во внешний файл (для saved файлов)
        """
        try:
            # Сохраняем текущее состояние через существующий метод controller
            # Сначала сохраняем во внешний файл, если он указан
            if save_to_file:
                self.controller.save_scene(save_to_file)
                # Копируем содержимое внешнего файла в файл репозитория
                with open(save_to_file, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(self.project_file, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                # Для unsaved файлов сохраняем в файл репозитория
                self.controller.save_scene(self.project_file)

            # Добавляем в индекс и делаем коммит
            subprocess.run(["git", "-C", self.git_dir, "add", "-f", self.filename], check=True)
            commit_message = f"{action_name} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(
                ["git", "-C", self.git_dir, "commit", "-m", commit_message],
                capture_output=True,
                text=True
            )

            # Получаем хеш последнего коммита
            result = subprocess.run(
                ["git", "-C", self.git_dir, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            self.current_commit = result.stdout.strip()

            print(f"Состояние сохранено: {commit_message}, коммит: {self.current_commit[:7]}")

        except Exception as e:
            print(f"Ошибка при сохранении состояния: {e}")

    def undo(self) -> bool:
        """
        Откатить последнее изменение

        Returns:
            True если откат успешен, False в противном случае
        """
        try:
            # Получаем список коммитов
            commits = self._get_commit_history()
            if len(commits) < 2:  # Нужно минимум 2 коммита (начальный + хотя бы один)
                print("Нет изменений для отката")
                return False

            # Находим текущий коммит в истории
            current_index = -1
            for i, commit in enumerate(commits):
                if commit['hash'].startswith(self.current_commit):
                    current_index = i
                    break

            # Если текущий коммит не найден, используем последний
            if current_index == -1:
                current_index = 0

            # Проверяем, можно ли откатить (не в начале ли мы)
            # Теперь проверяем, является ли текущий коммит начальным коммитом
            # Предполагаем, что начальный коммит - это первый коммит в репозитории
            initial_commit = self._get_initial_commit()
            if self.current_commit == initial_commit:
                print("Невозможно откатить, достигнуто начальное состояние")
                return False

            # Получаем хеш предыдущего коммита (в хронологическом порядке - следующий в списке)
            prev_commit = commits[current_index + 1]['hash']

            # Переходим к предыдущему коммиту
            subprocess.run(["git", "-C", self.git_dir, "checkout", prev_commit, "--", self.filename], check=True)

            # Загружаем состояние из файла в директории проекта
            self.controller.load_scene(self.project_file)

            # Обновляем текущий коммит
            self.current_commit = prev_commit

            print(f"Откат выполнена к коммиту: {prev_commit[:7]}")
            return True

        except Exception as e:
            print(f"Ошибка при откате: {e}")
            # Восстанавливаем рабочее состояние при ошибке
            subprocess.run(["git", "-C", self.git_dir, "checkout", self.current_commit, "--", self.filename], check=False)
            return False

    def redo(self) -> bool:
        """
        Вернуть откатенное изменение

        Returns:
            True если возврат успешен, False в противном случае
        """
        try:
            # Получаем список коммитов
            commits = self._get_commit_history()
            if len(commits) < 2:
                print("Нет изменений для возврата")
                return False

            # Находим текущий коммит в истории
            current_index = -1
            for i, commit in enumerate(commits):
                if commit['hash'].startswith(self.current_commit):
                    current_index = i
                    break

            # Если текущий коммит не найден, используем последний
            if current_index == -1:
                current_index = 0

            # Проверяем, можно ли вернуть (не в конце ли мы)
            if current_index <= 0:  # Уже в конце истории
                print("Невозможно вернуть изменения, достигнут конец истории")
                return False

            # Получаем хеш следующего коммита (в хронологическом порядке - предыдущий в списке)
            next_commit = commits[current_index - 1]['hash']

            # Переходим к следующему коммиту
            subprocess.run(["git", "-C", self.git_dir, "checkout", next_commit, "--", self.filename], check=True)

            # Загружаем состояние
            self.controller.load_scene(self.project_file)

            # Обновляем текущий коммит
            self.current_commit = next_commit

            print(f"Возврат выполнен к коммиту: {next_commit[:7]}")
            return True

        except Exception as e:
            print(f"Ошибка при возврате изменений: {e}")
            # Восстанавливаем рабочее состояние при ошибке
            subprocess.run(["git", "-C", self.git_dir, "checkout", self.current_commit, "--", self.filename], check=False)
            return False

    def _get_commit_history(self) -> List[Dict]:
        """
        Получить историю коммитов

        Returns:
            Список словарей с информацией о коммитах
        """
        try:
            result = subprocess.run(
                ["git", "-C", self.git_dir, "log", "--pretty=format:%H|%s|%cd", "--date=iso", "--", self.filename],
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 2)
                if len(parts) < 3:
                    continue

                commit_hash, message, date = parts
                commits.append({
                    "hash": commit_hash,
                    "message": message,
                    "date": date
                })

            return commits
        except Exception as e:
            print(f"Ошибка при получении истории коммитов: {e}")
            return []

    def _get_current_commit(self) -> str:
        """
        Получить текущий коммит HEAD

        Returns:
            Хеш текущего коммита
        """
        try:
            result = subprocess.run(
                ["git", "-C", self.git_dir, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            # Если ошибка, возвращаем первый коммит
            try:
                result = subprocess.run(
                    ["git", "-C", self.git_dir, "rev-list", "--max-parents=0", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip().split('\n')[0]
            except:
                return None

    def _get_initial_commit(self) -> str:
        """
        Получить первый коммит в репозитории

        Returns:
            Хеш первого коммита
        """
        try:
            result = subprocess.run(
                ["git", "-C", self.git_dir, "rev-list", "--max-parents=0", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n')[0]
        except:
            return None

    def get_history(self) -> List[Dict]:
        """
        Получить пользовательскую историю действий

        Returns:
            Список действий с хешами коммитов
        """
        commits = self._get_commit_history()
        history = []

        for commit in commits:
            history.append({
                "action": commit["message"],
                "commit": commit["hash"][:7],
                "date": commit["date"]
            })

        return history


# Пример использования
if __name__ == "__main__":
    import sys
    import os
    from PyQt6.QtWidgets import QApplication

    # Создаем QApplication для работы с графикой
    app = QApplication(sys.argv)

    # Создаем локальную директорию для тестирования
    temp_dir = "test_versioning"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"Рабочая директория: {os.path.abspath(temp_dir)}")


    # Создаем мок-объекты для демонстрации
    class MockController:
        def __init__(self):
            self.data = {"blocks": []}

        def add_block(self, name):
            self.data["blocks"].append({"name": name, "instances": []})

        def save_scene(self, filename):
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            print(f"Сохранено в {filename}")

        def load_scene(self, filename):
            with open(filename, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"Загружено из {filename}")
            print(f"Текущее состояние: {self.data}")


    # Инициализация
    controller = MockController()
    version_manager = VersionManager(temp_dir, controller)

    # Демонстрация работы
    print("\n=== Демонстрация работы SimpleVersionManager ===")

    # 1. Начальное состояние
    controller.add_block("BlockA")
    version_manager.save_state("Создан BlockA")

    # 2. Добавляем еще один блок
    controller.add_block("BlockB")
    version_manager.save_state("Создан BlockB")

    # 3. Добавляем третий блок
    controller.add_block("BlockC")
    version_manager.save_state("Создан BlockC")

    print("\nИстория после создания трех блоков:")
    for entry in version_manager.get_history():
        print(f"- {entry['action']} ({entry['commit']})")

    # 4. Делаем undo
    print("\nВыполняем undo (откат создания BlockC):")
    version_manager.undo()

    # 5. Еще один undo
    print("\nВыполняем еще один undo (откат создания BlockB):")
    version_manager.undo()

    # 6. Попытка сделать undo от начального состояния
    print("\nПопытка выполнить undo от начального состояния:")
    version_manager.undo()

    print("\nИстория после попытки отката от начального состояния:")
    for entry in version_manager.get_history():
        print(f"- {entry['action']} ({entry['commit']})")

    # 7. Делаем redo
    print("\nВыполняем redo (возврат BlockB):")
    version_manager.redo()

    print("\nФинальное состояние проекта:")
    print(controller.data)

    print("\n" + "=" * 50)
    print("ТЕПЕРЬ ДЕМОНСТРАЦИЯ СИНХРОНИЗАЦИИ ВНЕШНИХ ИЗМЕНЕНИЙ")
    print("=" * 50)

    # Эмуляция внешнего изменения файла
    print("\nЭмулируем внешнее изменение файла...")
    external_data = {"blocks": [{"name": "ExternalBlock", "instances": []}]}
    external_file_path = os.path.join(temp_dir, "project_state.json")
    with open(external_file_path, "w", encoding="utf-8") as f:
        json.dump(external_data, f, indent=2)
    print(f"Файл изменен внешней программой: {external_data}")

    # Создаем новый экземпляр менеджера для симуляции перезапуска
    print("\nСоздаем новый экземпляр VersionManager для симуляции перезапуска...")
    new_controller = MockController()
    new_version_manager = VersionManager(temp_dir, new_controller)

    print("\nИстория после синхронизации внешних изменений:")
    for entry in new_version_manager.get_history():
        print(f"- {entry['action']} ({entry['commit']})")

    print(f"\nСостояние проекта после синхронизации внешних изменений:")
    print(new_controller.data)

    print("\nДемонстрация завершена")
    sys.exit(0)
