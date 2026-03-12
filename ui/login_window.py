"""
AuraPOS Professional - Login Window
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QInputDialog, QMessageBox
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
        card_layout.setSpacing(12)
        
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
        self.username_input.textChanged.connect(self._clear_error_state)
        card_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setProperty("subheading", True)
        card_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        self.password_input.textChanged.connect(self._clear_error_state)
        card_layout.addWidget(self.password_input)
        
        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setObjectName("loginError")
        self.error_label.setProperty("banner", "error")
        self.error_label.setProperty("active", "false")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)
        
        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setProperty("primary", True)
        self.login_btn.clicked.connect(self.attempt_login)
        card_layout.addWidget(self.login_btn)

        forgot_btn = QPushButton("Forgot password?")
        forgot_btn.setProperty("link", "true")
        forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_btn.setFlat(True)
        forgot_btn.clicked.connect(self.forgot_password)
        card_layout.addWidget(forgot_btn)

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
        self._set_error_banner(False)
        self._set_error_state(False)

    def forgot_password(self) -> None:
        """
        Password reset flow using a fixed key as requested.
        If the key matches, reset the 'admin' password to 'adminadmin'.
        """
        key, ok = QInputDialog.getText(
            self,
            "Reset Password",
            "Enter reset key:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        key = (key or "").strip()
        if key != "YWRtaW5hZG1pbg==":
            QMessageBox.warning(self, "Invalid Key", "Reset key is incorrect.")
            return

        new_pw = "adminadmin"
        success, msg = auth.reset_admin_password(new_pw, username="admin")
        if not success:
            QMessageBox.warning(self, "Error", msg)
            return

        # Help the user immediately sign in.
        self.username_input.setText("admin")
        self.password_input.setText(new_pw)
        self.error_label.hide()
        QMessageBox.information(
            self,
            "Password Reset",
            "Admin password has been reset to: adminadmin",
        )
    
    def focus_password(self):
        """Move focus to password field."""
        self.password_input.setFocus()
    
    def attempt_login(self):
        """Attempt to log in with provided credentials."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            # Missing fields: show message but don't paint fields as "wrong password".
            self.show_error("Please enter username and password", highlight_fields=False)
            return
        
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")
        
        success, message = auth.login(username, password)
        
        if success:
            self._set_error_banner(False)
            self.login_successful.emit()
        else:
            self.show_error(message, highlight_fields=True)
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")
    
    def show_error(self, message: str, *, highlight_fields: bool = True):
        """Display error message."""
        self.error_label.setText(message)
        self._set_error_banner(True)
        self._set_error_state(bool(highlight_fields))

    def _set_error_banner(self, is_active: bool) -> None:
        self.error_label.setProperty("active", "true" if is_active else "false")
        self.error_label.style().unpolish(self.error_label)
        self.error_label.style().polish(self.error_label)
        self.error_label.setVisible(bool(is_active))
        if not is_active:
            self.error_label.setText("")

    def _set_error_state(self, is_error: bool) -> None:
        for field in (self.username_input, self.password_input):
            field.setProperty("error", "true" if is_error else "")
            field.style().unpolish(field)
            field.style().polish(field)

    def _clear_error_state(self) -> None:
        if not self.error_label.isVisible():
            return
        self._set_error_banner(False)
        self._set_error_state(False)
    
    def reset(self):
        """Reset the login form."""
        self.username_input.clear()
        self.password_input.clear()
        self._set_error_banner(False)
        self._set_error_state(False)
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")
        self.username_input.setFocus()
