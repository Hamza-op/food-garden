"""
AuraPOS Professional - Login Window
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
import os

from utils.auth import auth
from database import db
from config import ASSETS_DIR
from ui.effects import apply_shadow


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
        self.setObjectName("loginRoot")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(16)
        
        layout.addStretch(2)
        
        # Logo/Title Section
        title_container = QFrame()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo_path):
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(logo_path)
            logo.setPixmap(
                pixmap.scaled(
                    68,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            logo.setText("🥒")
            logo.setStyleSheet("font-size: 44px;")
        title_layout.addWidget(logo)
        
        title_label = QLabel("Food Garden")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("loginBrand")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Professional Billing System")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setObjectName("loginSubtitle")
        title_layout.addWidget(subtitle_label)
        
        layout.addWidget(title_container)
        layout.addSpacing(18)
        
        # Login Card
        card = QFrame()
        card.setObjectName("loginCard")
        card.setProperty("card", True)
        card.setMaximumWidth(440)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(14)
        
        # Welcome text
        welcome_label = QLabel("Welcome Back")
        welcome_label.setObjectName("loginCardTitle")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(welcome_label)
        
        card_layout.addSpacing(6)
        
        # Username
        username_label = QLabel("Username")
        username_label.setProperty("subheading", True)
        card_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.returnPressed.connect(self.focus_password)
        card_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setProperty("subheading", True)
        card_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)
        
        card_layout.addSpacing(4)
        
        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("loginError")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)
        
        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setProperty("primary", True)
        self.login_btn.clicked.connect(self.attempt_login)
        card_layout.addWidget(self.login_btn)

        github = QLabel(
            'GitHub: <a style="color:#00ADB5; text-decoration:none; font-weight:600;" href="https://github.com/Hamza-op">Hamza-op</a>'
        )
        github.setObjectName("loginGithub")
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github.setOpenExternalLinks(True)
        card_layout.addWidget(github)
        
        # Center the card
        card_container = QHBoxLayout()
        card_container.addStretch()
        card_container.addWidget(card)
        card_container.addStretch()
        layout.addLayout(card_container)
        apply_shadow(card, blur_radius=28, y_offset=12)
        
        layout.addStretch(3)
        
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
