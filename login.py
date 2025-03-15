from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from auth import register_user, verify_user

class LoginPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Login to eKYC")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Login")
        self.signup_button = QPushButton("Sign Up")

        layout.addWidget(self.label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.signup_button)

        self.setLayout(layout)

        self.login_button.clicked.connect(self.handle_login)
        self.signup_button.clicked.connect(self.open_signup_page)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if verify_user(username, password):
            QMessageBox.information(self, "Login Successful", "Welcome!")
            self.main_window.show_main_gui()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password!")

    def open_signup_page(self):
        self.main_window.show_signup_page()


class SignupPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Create an Account")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Choose a Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.signup_button = QPushButton("Sign Up")
        self.back_button = QPushButton("Back to Login")

        layout.addWidget(self.label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.signup_button)
        layout.addWidget(self.back_button)

        self.setLayout(layout)

        self.signup_button.clicked.connect(self.handle_signup)
        self.back_button.clicked.connect(self.back_to_login)

    def handle_signup(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if register_user(username, password):
            QMessageBox.information(self, "Signup Successful", "You can now log in!")
            self.main_window.show_login_page()
        else:
            QMessageBox.warning(self, "Signup Failed", "Username already taken!")

    def back_to_login(self):
        self.main_window.show_login_page()
