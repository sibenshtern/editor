from PyQt6 import QtCore, QtWidgets


class WelcomeWindowUI(object):
    def __init__(self, main_window):
        self.central_widget = QtWidgets.QWidget(parent=main_window)
        self.vertical_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.greeting_label = QtWidgets.QLabel(parent=self.central_widget)
        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.checker_button = QtWidgets.QPushButton(parent=self.central_widget)
        self.editor_button = QtWidgets.QPushButton(parent=self.central_widget)
        self.status_bar = QtWidgets.QStatusBar(parent=main_window)

    def setup_ui(self, main_window):
        main_window.setObjectName("welcome_window")
        main_window.resize(800, 600)

        main_window.setCentralWidget(self.central_widget)
        self.central_widget.setObjectName("central_widget")

        self.vertical_layout.setObjectName("vertical_layout")
        self.vertical_layout.addWidget(self.greeting_label)
        self.vertical_layout.addLayout(self.horizontal_layout)

        self.greeting_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.greeting_label.setObjectName("greeting_label")

        self.horizontal_layout.setObjectName("horizontal_layout")
        self.horizontal_layout.addWidget(self.checker_button)
        self.horizontal_layout.addWidget(self.editor_button)

        self.checker_button.setObjectName("checker_button")

        self.editor_button.setIconSize(QtCore.QSize(16, 16))
        self.editor_button.setObjectName("editor_button")

        self.status_bar.setObjectName("status_bar")
        main_window.setStatusBar(self.status_bar)

        self.retranslate_ui(main_window)
        QtCore.QMetaObject.connectSlotsByName(main_window)

    def retranslate_ui(self, main_window):
        translate = QtCore.QCoreApplication.translate
        main_window.setWindowTitle(translate("main_window", "Welcome window"))
        self.greeting_label.setText(
            translate("main_window", "Welcome to the Schema Editor app.")
        )
        self.checker_button.setText(translate("main_window", "Cheсker"))
        self.editor_button.setText(translate("main_window", "Editor"))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()

    ui = WelcomeWindowUI(main_window)
    ui.setup_ui(main_window)
    main_window.show()
    sys.exit(app.exec())
