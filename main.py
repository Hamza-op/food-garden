"""
AuraPOS Professional - Main Entry Point
"""
import sys
import os
import logging

# Hide console window on Windows when launched via python.exe (prevents startup CMD flicker).
def _hide_console_window() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes  # type: ignore

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


_hide_console_window()

# Ensure the application directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType

from config import APP_NAME, ASSETS_DIR, UI_DIR
from database import db
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from utils.auth import auth


def _configure_logging() -> None:
    try:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        log_dir = os.path.join(base, "Food Garden", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")
        logging.basicConfig(
            level=logging.INFO,
            filename=log_path,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except Exception:
        # Fall back silently; avoid printing (can bring the console back).
        logging.basicConfig(level=logging.CRITICAL)


_configure_logging()
logger = logging.getLogger(__name__)


class AuraPOSApp:
    """Main application controller."""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(APP_NAME)

        # Suppress noisy Qt warnings that can appear on some systems when fonts are stylesheet-driven.
        def _qt_message_handler(mode, context, message):  # type: ignore[no-untyped-def]
            try:
                if isinstance(message, str) and message.startswith("QFont::setPointSize: Point size <= 0"):
                    return
            except Exception:
                pass
            try:
                sys.stderr.write(f"{message}\n")
            except Exception:
                pass

        try:
            qInstallMessageHandler(_qt_message_handler)
        except Exception:
            pass
        
        # Load stylesheet
        self.load_stylesheet()
        
        # Initialize database
        self.init_database()
        
        # Create main stack
        self.stack = QStackedWidget()
        self.stack.setWindowTitle(APP_NAME)
        self.stack.setMinimumSize(1200, 700)
        
        # Set window icon if exists
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.stack.setWindowIcon(QIcon(icon_path))
        
        # Create windows
        logger.info("Creating LoginWindow...")
        self.login_window = LoginWindow()
        logger.info("LoginWindow created. Creating MainWindow...")
        self.main_window = MainWindow()
        logger.info("MainWindow created.")
        
        # Add to stack
        self.stack.addWidget(self.login_window)
        self.stack.addWidget(self.main_window)
        
        # Connect signals
        self.login_window.login_successful.connect(self.on_login_success)
        self.main_window.logout_requested.connect(self.on_logout)
        
        # Start with login
        self.stack.setCurrentIndex(0)
    
    def load_stylesheet(self):
        """Load the QSS stylesheet."""
        try:
            qss_path = os.path.join(UI_DIR, "styles.qss")
            if os.path.exists(qss_path):
                with open(qss_path, "r") as f:
                    self.app.setStyleSheet(f.read())
        except Exception as e:
            logger.warning("Could not load stylesheet: %s", e)
    
    def init_database(self):
        """Initialize the database."""
        try:
            from config import DB_PATH, BACKUP_DIR
            
            # Ensure directories exist
            db_dir = os.path.dirname(DB_PATH)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)

            # Handle first run in frozen mode: Copy bundled DB if missing
            if getattr(sys, 'frozen', False) and not os.path.exists(db.db_path):
                bundle_path = os.path.join(sys._MEIPASS, "initial_data.db")
                if os.path.exists(bundle_path):
                    import shutil
                    logger.info("Deploying initial database...")
                    try:
                        shutil.copy2(bundle_path, db.db_path)
                    except Exception as e:
                        logger.warning("Failed to copy initial DB: %s", e)
            
            # Connect and initialize
            db.connect()
            db.initialize_database()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.exception("Database error")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Database Error", 
                               f"Failed to initialize database.\nError: {e}\n\nPlease check permissions and try again.")
            sys.exit(1)
    
    def on_login_success(self):
        """Handle successful login."""
        self.main_window.set_user(auth.current_user)
        self.main_window.load_menu()
        self.stack.setCurrentIndex(1)
    
    def on_logout(self):
        """Handle logout."""
        self.login_window.reset()
        self.stack.setCurrentIndex(0)
    
    def run(self):
        """Run the application."""
        self.stack.show()
        return self.app.exec()


def main():
    """Application entry point."""
    try:
        app = AuraPOSApp()
        sys.exit(app.run())
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
