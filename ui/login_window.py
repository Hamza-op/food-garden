"""
AuraPOS Professional - Login Window
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from utils.auth import auth
from database import db


class LoginWindow(QWidget):
    """Modern login window with premium design."""
    
    login_successful = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Food Garden - Login")
        self.setMinimumSize(500, 600)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the login UI."""
        # Main background
        self.setStyleSheet("background-color: #0D0D0D;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(0)
        
        # Spacer top
        layout.addSpacerItem(QSpacerItem(20, 60, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Logo/Title Section
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(8)
        
        title_label = QLabel("Food Garden")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 42px;
            font-weight: bold;
            color: #00ADB5;
            letter-spacing: 3px;
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Professional Billing System")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 14px; color: #666666; letter-spacing: 1px;")
        title_layout.addWidget(subtitle_label)
        
        layout.addWidget(title_container)
        layout.addSpacing(50)
        
        # Login Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161616;
                border: 1px solid #252525;
                border-radius: 16px;
            }
        """)
        card.setMaximumWidth(400)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 40, 35, 40)
        card_layout.setSpacing(20)
        
        # Welcome text
        welcome_label = QLabel("Welcome Back")
        welcome_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #EEEEEE; border: none;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(welcome_label)
        
        card_layout.addSpacing(10)
        
        # Username
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-size: 13px; color: #888888; font-weight: 500; border: none;")
        card_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                border: 2px solid #2A2A2A;
                border-radius: 10px;
                padding: 14px 18px;
                font-size: 15px;
                color: #EEEEEE;
            }
            QLineEdit:focus {
                border-color: #00ADB5;
                background-color: #222222;
            }
        """)
        self.username_input.returnPressed.connect(self.focus_password)
        card_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-size: 13px; color: #888888; font-weight: 500; border: none;")
        card_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                border: 2px solid #2A2A2A;
                border-radius: 10px;
                padding: 14px 18px;
                font-size: 15px;
                color: #EEEEEE;
            }
            QLineEdit:focus {
                border-color: #00ADB5;
                background-color: #222222;
            }
        """)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)
        
        card_layout.addSpacing(5)
        
        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #EF5350; font-size: 13px; border: none;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)
        
        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00ADB5, stop:1 #00878D);
                color: #0D0D0D;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                padding: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00CED8, stop:1 #00ADB5);
            }
            QPushButton:pressed {
                background-color: #007A80;
            }
        """)
        self.login_btn.clicked.connect(self.attempt_login)
        card_layout.addWidget(self.login_btn)
        
        # Center the card
        card_container = QHBoxLayout()
        card_container.addStretch()
        card_container.addWidget(card)
        card_container.addStretch()
        layout.addLayout(card_container)
        
        # Spacer bottom
        layout.addSpacerItem(QSpacerItem(20, 60, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Focus username on start
        self.username_input.setFocus()
    
    def focus_password(self):
        """Move focus to password field."""
        self.password_input.setFocus()
    
    def attempt_login(self):
        """Attempt to log in with provided credentials."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.show_error("Please enter username and password")
            return
        
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")
        
        success, message = auth.login(username, password)
        
        if success:
            self.error_label.hide()
            self.login_successful.emit()
        else:
            self.show_error(message)
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")
    
    def show_error(self, message: str):
        """Display error message."""
        self.error_label.setText(message)
        self.error_label.show()
    
    def reset(self):
        """Reset the login form."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")
        self.username_input.setFocus()
