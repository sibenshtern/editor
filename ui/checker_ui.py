import sys
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
)


class CheckerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.browse_btn = QPushButton("Обзор...")

        self.layout = QVBoxLayout()
        self.file_layout = QHBoxLayout()
        self.btn_layout = QHBoxLayout()

        self.run_btn = QPushButton("Запуск Чекера")
        self.cancel_btn = QPushButton("Отмена")

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Run Checker")
        self.setFixedSize(500, 300)

        self.browse_btn.clicked.connect(self.browse_file)

        self.file_layout.addWidget(self.browse_btn)

        self.cancel_btn.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.run_btn)
        self.btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.file_layout)
        self.layout.addLayout(self.btn_layout)

        self.setLayout(self.layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите входной файл", "", "Все файлы (*);;Текстовые файлы (*.txt)"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CheckerDialog()
    window.show()
    sys.exit(app.exec())
