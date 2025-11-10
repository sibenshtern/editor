import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QFrame,
    QSplitter,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


class EditorWindowUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Графический редактор")
        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.menu_actions = {}
        self.create_menu_bar()

        self.create_toolbar(self.main_layout)
        self.create_bottom_section(self.main_layout)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("Файл")

        open_action = QAction("Открыть", self)
        self.menu_actions["open"] = open_action
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить", self)
        self.menu_actions["save"] = save_action
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить как...", self)
        self.menu_actions["save_as"] = save_as_action
        file_menu.addAction(save_as_action)

    def create_toolbar(self, parent_layout):
        toolbar_container = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_container)

        # Create grid layout for buttons
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)

        # Row 0: Labels
        labels = ["Blocks", "Instances", "Pins", "Nets", "Junctions", "Edit"]
        for col, label_text in enumerate(labels):
            label = QLabel(label_text)
            grid_layout.addWidget(label, 0, col)

        # Row 1: Add buttons
        self.add_block = QPushButton("Add block")
        self.add_instance = QPushButton("Add instance")
        self.add_pin = QPushButton("Add pin")
        self.add_net = QPushButton("Add net")
        self.add_junction = QPushButton("Add junction")
        self.btn_undo = QPushButton("Undo")

        grid_layout.addWidget(self.add_block, 1, 0)
        grid_layout.addWidget(self.add_instance, 1, 1)
        grid_layout.addWidget(self.add_pin, 1, 2)
        grid_layout.addWidget(self.add_net, 1, 3)
        grid_layout.addWidget(self.add_junction, 1, 4)
        grid_layout.addWidget(self.btn_undo, 1, 5)

        # Row 2: Delete buttons
        self.del_block = QPushButton("Delete block")
        self.del_instance = QPushButton("Delete instance")
        self.del_pin = QPushButton("Delete pin")
        self.del_net = QPushButton("Delete net")
        self.del_junction = QPushButton("Delete junction")
        self.btn_redo = QPushButton("Redo")

        grid_layout.addWidget(self.del_block, 2, 0)
        grid_layout.addWidget(self.del_instance, 2, 1)
        grid_layout.addWidget(self.del_pin, 2, 2)
        grid_layout.addWidget(self.del_net, 2, 3)
        grid_layout.addWidget(self.del_junction, 2, 4)
        grid_layout.addWidget(self.btn_redo, 2, 5)

        # Row 3: Copy buttons
        self.copy_block = QPushButton("Copy block")
        self.copy_instance = QPushButton("Copy instance")

        grid_layout.addWidget(self.copy_block, 4, 0)
        grid_layout.addWidget(self.copy_instance, 4, 1)

        # Row 4: Rename buttons
        self.rename_block = QPushButton("Rename block")
        self.rename_instance = QPushButton("Rename instance")
        self.rename_pin = QPushButton("Rename pin")
        self.rename_net = QPushButton("Rename net")

        grid_layout.addWidget(self.rename_block, 3, 0)
        grid_layout.addWidget(self.rename_instance, 3, 1)
        grid_layout.addWidget(self.rename_pin, 3, 2)
        grid_layout.addWidget(self.rename_net, 3, 3)

        toolbar_layout.addLayout(grid_layout)
        toolbar_layout.addStretch()

        parent_layout.addWidget(toolbar_container)

    def create_bottom_section(self, parent_layout):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("List of objects:"))
        self.objects_list = QListWidget()

        left_layout.addWidget(self.objects_list)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("Editor zone"))

        self.graphics_frame = QWidget()
        self.graphics_frame.setMinimumHeight(400)

        right_layout.addWidget(self.graphics_frame)

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)

        self.splitter.setSizes([300, 700])

        parent_layout.addWidget(self.splitter)


def main():
    app = QApplication(sys.argv)

    window = EditorWindowUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
