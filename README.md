# Food Garden (AuraPOS Professional)

Food Garden is a full-featured Point of Sale (POS) desktop application built with Python and PyQt6. It is designed to manage restaurant or cafe operations efficiently, including menu management, order processing, receipt printing, and daily sales tracking.

## Features

- **User Authentication**: Secure role-based login system using `bcrypt` for password hashing.
- **Menu Management**: Add, update, and categorize menu items.
- **Excel Import/Export**: Import menu items directly from Excel files (`.xlsx`) to perform bulk updates using `openpyxl`.
- **Order Processing**: Intuitive interface for taking orders, calculating taxes, applying discounts, and processing payments.
- **Robust Receipt Printing**:
  - Direct integration with thermal slip printers (ESC/POS compatible) using raw binary commands mapped via `win32print`.
  - Configurable paper sizes (80mm and 58mm).
  - Plain-text fallback methods that utilize PowerShell, Notepad, or the default system text viewer if a thermal printer is not available.
- **Database Management**: Stores relational data locally using an SQLite database with automated initial setup and migration utilities.
- **Executable Distribution**: Easy-to-use packaging script (`build_exe.py`) that uses PyInstaller to bundle the app, stylesheets, and initial database into a single, portable Windows `.exe` file.

## Tech Stack
- **Language**: Python 3.x
- **GUI Framework**: PyQt6
- **Database**: SQLite3
- **Hardware Integration**: `python-escpos` & pywin32 (`win32print`)
- **Excel Handling**: `openpyxl`
- **Security**: `bcrypt`

## Project Structure

```text
food-garden/
├── assets/                  # Images, icons, and bundled resources
├── ui/                      # PyQt6 UI components and QSS stylesheets
│   ├── login_window.py      # App authentication UI
│   ├── main_window.py       # Primary POS dashboard
│   ├── effects.py           # Custom UI animations / visual effects
│   └── styles.qss           # Application dark/light design system
├── utils/                   # Helper functions (authentication, formatting)
├── Backups/                 # Auto-generated database backups location
├── main.py                  # Application entry point
├── config.py                # Global configurations, colors, paths, and settings
├── database.py              # SQLite wrapper and data access layer
├── printer.py               # Thermal and fallback printing service
├── migrate.py               # Database migration scripts
├── build_exe.py             # PyInstaller script to compile `.exe`
├── create_sample_excel.py   # Utility to generate test Excel files for importing
├── requirements.txt         # Project dependencies
└── aura_pos.db              # The local SQLite database (created on first run)
```

## Installation & Setup

1. **Clone the repository** (if applicable) or download the source code folder.
2. **Setup a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If you run into issues with `win32print`, install the Windows extensions explicitly via `pip install pywin32`.*

## Running the Application

To start the Food Garden POS application from the source code, run:
```bash
python main.py
```
*On the first run, the local SQLite database (`aura_pos.db`) will be initialized automatically.*

### Creating Sample Import Files
To test the "Import from Excel" functionality in the admin panel, run:
```bash
python create_sample_excel.py
```
This generates `sample_menu.xlsx` and `minimal_menu.xlsx` within the project root.

## Building the Executable (Windows)

You can package Food Garden into a standalone `.exe` file that users can run without installing Python.

1. Simply run the build script:
   ```bash
   python build_exe.py
   ```
2. The script will automatically check for PyInstaller, bundle the code, load `ui` stylesheets, package `assets/`, and bundle a copy of the default database.
3. Once completed, your compiled application will be located at:
   `dist/Food Garden.exe`

## Printing Configuration

By default, the application attempts to find and send raw ESC/POS commands directly to the default active thermal printer.
- **80mm Roll:** Uses 42 characters per line formatted layout.
- **58mm Roll:** Uses 32 characters per line formatted layout.
- **Testing:** The hardware connection can be verified by running the hardware test print inside the application settings.
- **Fallback:** If a thermal printer fails, a fallback preview `.txt` receipt will be created and opened dynamically using system text viewers.
