"""
AuraPOS Professional - Main Entry Point
"""
import sys
import os

# Ensure the application directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from config import APP_NAME, ASSETS_DIR
from database import db
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from utils.auth import auth


class AuraPOSApp:
    """Main application controller."""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(APP_NAME)
        
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
        print("Creating LoginWindow...")
        self.login_window = LoginWindow()
        print("LoginWindow created. Creating MainWindow...")
        self.main_window = MainWindow()
        print("MainWindow created.")
        
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
            qss_path = os.path.join(os.path.dirname(__file__), "ui", "styles.qss")
            if os.path.exists(qss_path):
                with open(qss_path, "r") as f:
                    self.app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Warning: Could not load stylesheet: {e}")
    
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
                    print("Deploying initial database...")
                    try:
                        shutil.copy2(bundle_path, db.db_path)
                    except Exception as e:
                        print(f"Failed to copy initial DB: {e}")
            
            # Connect and initialize
            db.connect()
            db.initialize_database()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Database error: {e}")
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
        print("\nApplication stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
