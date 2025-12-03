import subprocess

from PyQt6 import QtCore, QtWidgets

from ui.welcome_window_ui import WelcomeWindowUI
from ui.checker_ui import CheckerDialog
from editor import Editor


class Shell(WelcomeWindowUI):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.editor_button.clicked.connect(self.run_editor)
        self.checker_button.clicked.connect(self.checker_init)
        self.editor_window = None

    def run_editor(self):
        """Launch the editor window and close shell."""
        if self.editor_window is None or not self.editor_window.isVisible():
            self.editor_window = Editor()
        else:
            self.editor_window.raise_()
            self.editor_window.activateWindow()

        self.main_window.close()

    @staticmethod
    def run_checker(file_name):
        try:
            result = subprocess.run(
                ["python3", "checker/src/cli.py", "--input", file_name, "-o", "output.txt"], capture_output=True, text=True
            )

            print("=== STDOUT ===")
            print(result.stdout)
            print("=== STDERR ===")
            print(result.stderr)

            print(f"Exit code: {result.returncode}")

        except FileNotFoundError:
            print("Ошибка: приложение 'check_file' не найдено в PATH.")
        except Exception as e:
            print(f"Ошибка при запуске: {e}")

    def checker_init(self):
        dialog = CheckerDialog()

        try:
            dialog.browse_btn.clicked.disconnect()
        except Exception:
            pass

        def browse_wrapper():
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                dialog,
                "Выберите входной файл",
                "",
                "Все файлы (*);;Текстовые файлы (*.txt)",
            )
            if file_path:
                dialog.selected_file = file_path
                print(f"Выбран файл: {file_path}")
            else:
                if hasattr(dialog, "selected_file"):
                    del dialog.selected_file
                print("Файл не выбран (или пользователь отменил выбор).")

        dialog.browse_btn.clicked.connect(browse_wrapper)

        try:
            dialog.run_btn.clicked.disconnect()
        except Exception:
            pass

        def run_wrapper():
            fp = getattr(dialog, "selected_file", None)
            if fp:
                print(f"Запуск чекера для файла: {fp}")
                self.run_checker(fp)
                dialog.accept()
            else:
                print("Нельзя запустить: файл не выбран.")

        dialog.run_btn.clicked.connect(run_wrapper)

        result = dialog.exec()

        if result:
            file_path = getattr(dialog, "selected_file", None)
            if file_path:
                print(f"Файл передан в Shell: {file_path}")
            else:
                print("Диалог принят, но файл не найден.")
        else:
            print("Диалог отменён пользователем (reject).")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()

    ui = Shell(main_window)
    ui.setup_ui(main_window)
    main_window.show()
    sys.exit(app.exec())
