"""
AuraPOS Professional - Configuration Constants
"""
import os
import sys

# Application Info
APP_NAME = "Food Garden"
APP_VERSION = "1.0.0"

# Paths
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# External directory for writable files (DB, Backups)
if getattr(sys, 'frozen', False):
    # Running as compiled exe: Use the executable's directory for writable data
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running from source: Use the script's directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "aura_pos.db")
BACKUP_DIR = os.path.join(BASE_DIR, "Backups")

# Resource directory for bundled assets (Images, Styles)
ASSETS_DIR = resource_path("assets")
UI_DIR = resource_path("ui")

# Bill Retention Settings
BILL_RETENTION_DAYS = 180  # 6 months - bills older than this are archived

# Design System Colors
COLORS = {
    "primary": "#00ADB5",
    "primary_hover": "#00CED8",
    "background": "#121212",
    "surface": "#1E1E1E",
    "surface_light": "#2D2D2D",
    "text": "#EEEEEE",
    "text_secondary": "#AAAAAA",
    "error": "#CF6679",
    "success": "#4CAF50",
    "warning": "#FFC107",
}

# Default Settings
DEFAULT_SETTINGS = {
    "restaurant_name": "My Restaurant",
    "restaurant_address": "123 Main Street",
    "restaurant_phone": "",
    "tax_rate": 5.0,
    "currency_symbol": "Rs",
    "printer_id": "",
    "receipt_footer": "Thank you for visiting!",
}

# Keyboard Shortcuts
SHORTCUTS = {
    "search": "F1",
    "pay": "F5",
    "print": "F12",
}
