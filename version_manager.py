import os
import json
import subprocess
import uuid
import datetime
from typing import List, Dict


class VersionManager:
    """
    Простая система версионирования через git.
    Сохраняет состояние проекта в git после каждого действия.
    Undo/Redo работают через git checkout.
    """

    def __init__(self, project_path: str, controller):
        """
        Инициализация менеджера версий

        Args:
            project_path: Путь к папке проекта
            controller: Ссылка на controller из graphical.py для сохранения/загрузки
        """
        self.project_path = project_path
        self.controller = controller
        self.git_dir = os.path.join(project_path, ".gitrepo")

        # Инициализация git репозитория
        self._init_git()

        # Текущий указатель на коммит (для отслеживания позиции в истории)
        self.current_commit = self._get_current_commit()

    def _init_git(self):
        """Инициализация git репозитория"""
        os.makedirs(self.git_dir, exist_ok=True)

        try:
            # Проверяем, есть ли уже git репозиторий
            if not os.path.exists(os.path.join(self.git_dir, ".git")):
                subprocess.run(["git", "init", self.git_dir], check=True)
                # Настраиваем git, чтобы избежать ошибок с именем пользователя и email
                subprocess.run(["git", "-C", self.git_dir, "config", "user.name", "NetlistEditor"], check=True)
                subprocess.run(["git", "-C", self.git_dir, "config", "user.email", "netlist@editor.local"], check=True)

                # Создаем начальный файл для первого коммита
                initial_file = os.path.join(self.git_dir, "project_state.json")
                with open(initial_file, "w", encoding="utf-8") as f:
                    json.dump({"blocks": []}, f, indent=2)
                subprocess.run(["git", "-C", self.git_dir, "add", "project_state.json"], check=True)
                subprocess.run(["git", "-C", self.git_dir, "commit", "-m", "Initial commit"], check=True)
        except Exception as e:
            print(f"Ошибка при инициализации git: {e}")

    def save_state(self, action_name: str):
        """
        Сохранить текущее состояние проекта в git

        Args:
            action_name: Описание действия для сообщения коммита
        """
        try:
            # 1. Копируем файл в git репозиторий
            project_file = os.path.join(self.git_dir, "project_state.json")

            # Сохраняем текущее состояние через существующий метод controller
            self.controller.save_scene(project_file)

            # 2. Добавляем в индекс и делаем коммит
            subprocess.run(["git", "-C", self.git_dir, "add", "project_state.json"], check=True)
            commit_message = f"{action_name} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(
                ["git", "-C", self.git_dir, "commit", "-m", commit_message],
                capture_output=True,
                text=True
            )

            # 3. Получаем хеш последнего коммита
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
            # 1. Получаем список коммитов
            commits = self._get_commit_history()
            if len(commits) < 2:  # Нужно минимум 2 коммита (начальный + хотя бы один)
                print("Нет изменений для отката")
                return False

            # 2. Находим текущий коммит в истории
            current_index = -1
            for i, commit in enumerate(commits):
                if commit['hash'].startswith(self.current_commit):
                    current_index = i
                    break

            # Если текущий коммит не найден, используем последний
            if current_index == -1:
                current_index = 0

            # 3. Проверяем, можно ли откатить (не в начале ли мы)
            if current_index >= len(commits) - 1:  # Уже в самом начале истории
                print("Невозможно откатить, достигнуто начало истории")
                return False

            # 4. Получаем хеш предыдущего коммита (в хронологическом порядке - следующий в списке)
            prev_commit = commits[current_index + 1]['hash']

            # 5. Переходим к предыдущему коммиту
            subprocess.run(["git", "-C", self.git_dir, "checkout", prev_commit, "--", "project_state.json"], check=True)

            # 6. Загружаем состояние из git репозитория
            git_project_file = os.path.join(self.git_dir, "project_state.json")
            self.controller.load_scene(git_project_file)

            # 7. Обновляем текущий коммит
            self.current_commit = prev_commit

            print(f"Откат выполнена к коммиту: {prev_commit[:7]}")
            return True

        except Exception as e:
            print(f"Ошибка при откате: {e}")
            # Восстанавливаем рабочее состояние при ошибке
            subprocess.run(["git", "-C", self.git_dir, "checkout", self.current_commit, "--", "project_state.json"],
                           check=False)
            return False

    def redo(self) -> bool:
        """
        Вернуть откатенное изменение

        Returns:
            True если возврат успешен, False в противном случае
        """
        try:
            # 1. Получаем список коммитов
            commits = self._get_commit_history()
            if len(commits) < 2:
                print("Нет изменений для возврата")
                return False

            # 2. Находим текущий коммит в истории
            current_index = -1
            for i, commit in enumerate(commits):
                if commit['hash'].startswith(self.current_commit):
                    current_index = i
                    break

            # Если текущий коммит не найден, используем последний
            if current_index == -1:
                current_index = 0

            # 3. Проверяем, можно ли вернуть (не в конце ли мы)
            if current_index <= 0:  # Уже в конце истории
                print("Невозможно вернуть изменения, достигнут конец истории")
                return False

            # 4. Получаем хеш следующего коммита (в хронологическом порядке - предыдущий в списке)
            next_commit = commits[current_index - 1]['hash']

            # 5. Переходим к следующему коммиту
            subprocess.run(["git", "-C", self.git_dir, "checkout", next_commit, "--", "project_state.json"], check=True)

            # 6. Загружаем состояние
            git_project_file = os.path.join(self.git_dir, "project_state.json")
            self.controller.load_scene(git_project_file)

            # 7. Обновляем текущий коммит
            self.current_commit = next_commit

            print(f"Возврат выполнен к коммиту: {next_commit[:7]}")
            return True

        except Exception as e:
            print(f"Ошибка при возврате изменений: {e}")
            # Восстанавливаем рабочее состояние при ошибке
            subprocess.run(["git", "-C", self.git_dir, "checkout", self.current_commit, "--", "project_state.json"],
                           check=False)
            return False

    def _get_commit_history(self) -> List[Dict]:
        """
        Получить историю коммитов

        Returns:
            Список словарей с информацией о коммитах
        """
        try:
            result = subprocess.run(
                ["git", "-C", self.git_dir, "log", "--pretty=format:%H|%s|%cd", "--date=iso", "--",
                 "project_state.json"],
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

    print("\nИстория после двух откатов:")
    for entry in version_manager.get_history():
        print(f"- {entry['action']} ({entry['commit']})")

    # 6. Делаем redo
    print("\nВыполняем redo (возврат BlockB):")
    version_manager.redo()

    print("\nФинальное состояние проекта:")
    print(controller.data)

    print("\n" + "=" * 50)
    print("ТЕПЕРЬ ДЕМОНСТРАЦИЯ ВОССТАНОВЛЕНИЯ ИСТОРИИ ПРИ НОВОМ ЗАПУСКЕ")
    print("=" * 50)

    # Эмуляция нового запуска приложения - создаем новый экземпляр
    print("\nСоздаем новый экземпляр VersionManager для эмуляции нового запуска...")
    new_controller = MockController()
    new_version_manager = VersionManager(temp_dir, new_controller)

    print(
        f"Текущий коммит при новом запуске: {new_version_manager.current_commit[:7] if new_version_manager.current_commit else 'None'}")

    print("\nИстория при новом запуске:")
    for entry in new_version_manager.get_history():
        print(f"- {entry['action']} ({entry['commit']})")

    print("\nПопытка выполнить undo после нового запуска:")
    if new_version_manager.undo():
        print("Undo после нового запуска успешен!")
    else:
        print("Undo после нового запуска не удался")

    print(
        f"Текущий коммит после undo: {new_version_manager.current_commit[:7] if new_version_manager.current_commit else 'None'}")

    print("\nСостояние проекта после undo нового запуска:")
    print(new_controller.data)

    print("\nДемонстрация завершена")
    sys.exit(0)