"""
AuraPOS Professional - Admin Panel (Revamped)
"""
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QFrame, QMessageBox,
    QDialog, QFormLayout, QGroupBox, QTextEdit, QFileDialog,
    QHeaderView, QAbstractItemView, QScrollArea, QStackedWidget,
    QGridLayout, QMenu, QDateEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QDate
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
import bcrypt
from datetime import datetime
import os

from database import db
from utils.auth import auth
from utils.backup import backup_manager
from config import ASSETS_DIR
from ui.effects import apply_shadow

# ==================== Constants ====================
CURRENCY_PREFIX = "Rs "
DEFAULT_TAX_RATE = 5.0
MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 6

CATEGORIES = ["Starters", "Main Course", "Beverages", "Desserts", "Sides", "Fast Food", "General"]
EXPENSE_CATEGORIES = ["General", "Inventory", "Utilities", "Maintenance", "Salary", "Other"]
USER_ROLES = ["Staff", "Admin"]
ITEM_STATUSES = ["active", "inactive"]

COLORS = {
    "success": "#4CAF50",
    "danger": "#CF6679",
    "primary": "#00ADB5",
    "warning": "#FF5252"
}

PAGE_TITLES = {
    0: ("Dashboard", "Overview of your business performance"),
    1: ("Sales History", "Review completed bills and totals"),
    2: ("Menu Manager", "Manage your product catalog"),
    3: ("Expenses", "Track your daily spending"),
    4: ("Users", "Manage staff access and roles"),
    5: ("Settings", "Configure system preferences"),
    6: ("Backups", "Secure your data")
}


class MenuItemDialog(QDialog):
    """Dialog for adding/editing menu items."""
    
    def __init__(self, parent: Optional[QWidget] = None, item: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit Item" if item else "Add New Item")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._initialize_values()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Edit Item" if self.item else "Add New Item")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        # Form
        layout.addWidget(self._create_form())
        
        # Buttons
        layout.addLayout(self._create_button_layout())
    
    def _create_form(self) -> QFrame:
        """Create and return the form frame."""
        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(15)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name")
        form_layout.addRow(self._create_label("Name:"), self.name_input)
        
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(CATEGORIES)
        form_layout.addRow(self._create_label("Category:"), self.category_input)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix(CURRENCY_PREFIX)
        form_layout.addRow(self._create_label("Price:"), self.price_input)
        
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setDecimals(2)
        self.tax_input.setSuffix(" %")
        form_layout.addRow(self._create_label("Tax Rate:"), self.tax_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(ITEM_STATUSES)
        form_layout.addRow(self._create_label("Status:"), self.status_input)
        
        return form
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Create and return the button layout."""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ Save Item")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        return btn_layout
    
    def _create_label(self, text: str) -> QLabel:
        """Create a styled label."""
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def _initialize_values(self) -> None:
        """Initialize form values from item or defaults."""
        if self.item:
            self._load_item(self.item)
        else:
            self._load_default_tax_rate()
    
    def _load_default_tax_rate(self) -> None:
        """Load the default tax rate from settings."""
        try:
            settings = db.get_all_settings()
            default_tax = float(settings.get("tax_rate", DEFAULT_TAX_RATE))
            self.tax_input.setValue(default_tax)
        except (ValueError, TypeError, AttributeError):
            self.tax_input.setValue(DEFAULT_TAX_RATE)
    
    def _validate_and_accept(self) -> None:
        """Validate input before accepting."""
        name = self.name_input.text().strip()
        
        if not name:
            self._show_validation_error("Please enter an item name", self.name_input)
            return
        
        if self.price_input.value() <= 0:
            self._show_validation_error("Please enter a valid price", self.price_input)
            return
        
        self.accept()
    
    def _show_validation_error(self, message: str, widget: QWidget) -> None:
        """Show validation error and focus the widget."""
        QMessageBox.warning(self, "Validation Error", message)
        widget.setFocus()
    
    def _load_item(self, item: Dict[str, Any]) -> None:
        """Load item data into the form."""
        self.name_input.setText(item.get("name", ""))
        self.category_input.setCurrentText(item.get("category", "General"))
        self.price_input.setValue(float(item.get("price", 0)))
        self.tax_input.setValue(float(item.get("tax_rate", 0)))
        self.status_input.setCurrentText(item.get("status", "active"))
    
    def get_data(self) -> Dict[str, Any]:
        """Return the form data as a dictionary."""
        return {
            "name": self.name_input.text().strip(),
            "category": self.category_input.currentText().strip() or "General",
            "price": self.price_input.value(),
            "tax_rate": self.tax_input.value(),
            "status": self.status_input.currentText()
        }


class UserDialog(QDialog):
    """Dialog for adding users."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")
        self.setMinimumWidth(450)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Add New User")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        layout.addWidget(self._create_form())
        layout.addLayout(self._create_button_layout())
    
    def _create_form(self) -> QFrame:
        """Create and return the form frame."""
        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(15)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(f"Minimum {MIN_USERNAME_LENGTH} characters")
        form_layout.addRow(self._create_label("Username:"), self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(f"Minimum {MIN_PASSWORD_LENGTH} characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(self._create_label("Password:"), self.password_input)
        
        self.role_input = QComboBox()
        self.role_input.addItems(USER_ROLES)
        form_layout.addRow(self._create_label("Role:"), self.role_input)
        
        return form
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Create and return the button layout."""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ Create User")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        return btn_layout
    
    def _create_label(self, text: str) -> QLabel:
        """Create a styled label."""
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def _validate_and_accept(self) -> None:
        """Validate input before accepting."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if len(username) < MIN_USERNAME_LENGTH:
            self._show_validation_error(
                f"Username must be at least {MIN_USERNAME_LENGTH} characters",
                self.username_input
            )
            return
        
        if len(password) < MIN_PASSWORD_LENGTH:
            self._show_validation_error(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
                self.password_input
            )
            return
        
        self.accept()
    
    def _show_validation_error(self, message: str, widget: QWidget) -> None:
        """Show validation error and focus the widget."""
        QMessageBox.warning(self, "Validation Error", message)
        widget.setFocus()
    
    def get_data(self) -> Dict[str, Any]:
        """Return the form data as a dictionary."""
        return {
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "role": self.role_input.currentText()
        }


class ExpenseDialog(QDialog):
    """Dialog for adding expenses."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Add Expense")
        self.setMinimumWidth(400)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Add Expense")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        layout.addWidget(self._create_form())
        layout.addLayout(self._create_button_layout())
    
    def _create_form(self) -> QFrame:
        """Create and return the form frame."""
        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(15)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("e.g. Vegetables, Cleaning Supplies")
        form_layout.addRow(self._create_label("Description:"), self.desc_input)
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 999999)
        self.amount_input.setPrefix(CURRENCY_PREFIX)
        form_layout.addRow(self._create_label("Amount:"), self.amount_input)
        
        self.category_input = QComboBox()
        self.category_input.addItems(EXPENSE_CATEGORIES)
        self.category_input.setEditable(True)
        form_layout.addRow(self._create_label("Category:"), self.category_input)
        
        return form
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Create and return the button layout."""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ Add Expense")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        return btn_layout
    
    def _create_label(self, text: str) -> QLabel:
        """Create a styled label."""
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def _validate_and_accept(self) -> None:
        """Validate input before accepting."""
        if not self.desc_input.text().strip():
            QMessageBox.warning(self, "Error", "Please enter a description")
            self.desc_input.setFocus()
            return
        
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "Error", "Amount must be greater than 0")
            self.amount_input.setFocus()
            return
        
        self.accept()
    
    def get_data(self) -> Dict[str, Any]:
        """Return the form data as a dictionary."""
        return {
            "description": self.desc_input.text().strip(),
            "amount": self.amount_input.value(),
            "category": self.category_input.currentText()
        }


class ExcelImportDialog(QDialog):
    """Dialog for importing menu items from Excel files."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Import Menu from Excel")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.file_path: Optional[str] = None
        self.import_results: List[Dict] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("📥 Import Menu from Excel")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        # Info label
        info = QLabel(
            "Select an Excel file (.xlsx) with columns: name, category, price, tax_rate, status\n"
            "Required columns: name, price. Other columns are optional."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        layout.addWidget(info)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("No file selected")
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)
        
        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # Preview / Results area
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Row", "Status", "Message"])
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.results_table)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.setProperty("primary", "true")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._do_import)
        btn_layout.addWidget(self.import_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_file(self) -> None:
        """Open file browser to select Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if file_path:
            self.file_path = file_path
            self.file_input.setText(file_path)
            self.import_btn.setEnabled(True)
            self.status_label.setText("Ready to import. Click 'Import' to proceed.")
            self.status_label.setStyleSheet("color: #00ADB5; font-weight: bold;")
    
    def _do_import(self) -> None:
        """Execute the import operation."""
        if not self.file_path:
            return
        
        self.import_btn.setEnabled(False)
        self.status_label.setText("Importing...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        
        # Process import
        success, message, results = db.import_menu_from_excel(self.file_path)
        self.import_results = results
        
        # Display results
        self.results_table.setRowCount(len(results))
        for i, result in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(str(result.get("row", ""))))
            status_item = QTableWidgetItem(result.get("status", "").upper())
            if result.get("status") == "success":
                status_item.setForeground(QColor("#4CAF50"))
            elif result.get("status") == "error":
                status_item.setForeground(QColor("#CF6679"))
            else:
                status_item.setForeground(QColor("#FFC107"))
            self.results_table.setItem(i, 1, status_item)
            self.results_table.setItem(i, 2, QTableWidgetItem(result.get("message", "")))
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #CF6679; font-weight: bold;")
            self.import_btn.setEnabled(True)


class BillsHistoryDialog(QDialog):
    """Dialog for viewing all generated bills (active sales)."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Sales History")
        self.setMinimumWidth(900)
        self.setMinimumHeight(650)
        self._setup_ui()
        self._load_bills()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(22, 22, 22, 22)

        header = QFrame()
        header.setProperty("card", True)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(12)

        header_left = QWidget()
        header_left_layout = QVBoxLayout(header_left)
        header_left_layout.setContentsMargins(0, 0, 0, 0)
        header_left_layout.setSpacing(4)

        title = QLabel("📋 Sales History")
        title.setProperty("heading", True)
        header_left_layout.addWidget(title)

        subtitle = QLabel("Search and review completed bills")
        subtitle.setProperty("subheading", True)
        header_left_layout.addWidget(subtitle)

        header_layout.addWidget(header_left, 1)

        close_btn = QPushButton("Close")
        close_btn.setProperty("secondary", "true")
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(header)
        apply_shadow(header, blur_radius=26, y_offset=10)

        # Filters + Search
        filters = QFrame()
        filters.setProperty("card", True)
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(18, 14, 18, 14)
        filters_layout.setSpacing(10)

        filters_layout.addWidget(self._make_label("From"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        filters_layout.addWidget(self.start_date)

        filters_layout.addWidget(self._make_label("To"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filters_layout.addWidget(self.end_date)

        today_btn = QPushButton("Today")
        today_btn.setProperty("secondary", "true")
        today_btn.clicked.connect(self._filter_today)
        filters_layout.addWidget(today_btn)

        week_btn = QPushButton("7 days")
        week_btn.setProperty("secondary", "true")
        week_btn.clicked.connect(lambda: self._set_last_days(7))
        filters_layout.addWidget(week_btn)

        month_btn = QPushButton("30 days")
        month_btn.setProperty("secondary", "true")
        month_btn.clicked.connect(lambda: self._set_last_days(30))
        filters_layout.addWidget(month_btn)

        filter_btn = QPushButton("Apply")
        filter_btn.setProperty("primary", "true")
        filter_btn.clicked.connect(self._load_bills)
        filters_layout.addWidget(filter_btn)

        filters_layout.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search receipt / payment…")
        self.search_input.setProperty("search", "true")
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._apply_text_filter)
        filters_layout.addWidget(self.search_input)

        layout.addWidget(filters)
        apply_shadow(filters, blur_radius=22, y_offset=8)

        # KPIs
        kpis = QWidget()
        kpi_layout = QHBoxLayout(kpis)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(12)

        self.kpi_bills = self._make_kpi("Bills", "0", icon="🧾", tone="neutral")
        self.kpi_sales = self._make_kpi("Total Sales", "Rs 0.00", icon="💰", tone="primary")
        self.kpi_tax = self._make_kpi("Tax Collected", "Rs 0.00", icon="📊", tone="primary")

        kpi_layout.addWidget(self.kpi_bills)
        kpi_layout.addWidget(self.kpi_sales)
        kpi_layout.addWidget(self.kpi_tax)

        layout.addWidget(kpis)

        # Table (card)
        table_card = QFrame()
        table_card.setProperty("card", True)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(10)

        self.bills_table = QTableWidget()
        self.bills_table.setObjectName("historyTable")
        self.bills_table.setProperty("embedded", True)
        self.bills_table.setShowGrid(False)
        self.bills_table.setColumnCount(7)
        self.bills_table.setHorizontalHeaderLabels([
            "ID", "Receipt No", "Date/Time", "Subtotal", "Tax", "Total", "Payment"
        ])
        self.bills_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bills_table.setColumnWidth(0, 50)
        self.bills_table.setColumnWidth(2, 150)
        self.bills_table.setColumnWidth(3, 100)
        self.bills_table.setColumnWidth(4, 80)
        self.bills_table.setColumnWidth(5, 100)
        self.bills_table.setColumnWidth(6, 80)
        self.bills_table.setAlternatingRowColors(True)
        self.bills_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bills_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bills_table.setSortingEnabled(True)
        self.bills_table.verticalHeader().setVisible(False)
        self.bills_table.verticalHeader().setDefaultSectionSize(44)
        self.bills_table.doubleClicked.connect(self._view_bill_details)
        table_layout.addWidget(self.bills_table)

        hint = QLabel("Tip: Double-click a bill to view item details.")
        hint.setProperty("subheading", True)
        table_layout.addWidget(hint)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(10)
        footer_layout.addStretch(1)

        view_btn = QPushButton("View Details")
        view_btn.setProperty("primary", "true")
        view_btn.clicked.connect(self._open_selected_details)
        footer_layout.addWidget(view_btn)

        table_layout.addWidget(footer)

        layout.addWidget(table_card, 1)
        apply_shadow(table_card, blur_radius=22, y_offset=8)

        self._all_bills: List[Dict[str, Any]] = []

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl

    def _make_kpi(self, title: str, value: str, *, icon: str, tone: str) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        card.setProperty("statTone", tone)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        top_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        top_layout.addWidget(title_label, 1)

        layout.addWidget(top)

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        layout.addWidget(value_label)

        apply_shadow(card, blur_radius=18, y_offset=6)
        return card
    
    def _filter_today(self) -> None:
        """Set filter to today only."""
        today = QDate.currentDate()
        self.start_date.setDate(today)
        self.end_date.setDate(today)
        self._load_bills()

    def _set_last_days(self, days: int) -> None:
        end = QDate.currentDate()
        start = end.addDays(-max(0, int(days)))
        self.start_date.setDate(start)
        self.end_date.setDate(end)
        self._load_bills()
    
    def _load_bills(self) -> None:
        """Load bills from the database."""
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        
        bills = db.get_bills_by_date_range(start, end)
        self._all_bills = list(bills or [])
        self._apply_text_filter()

    def _apply_text_filter(self) -> None:
        q = ""
        try:
            q = (self.search_input.text() or "").strip().lower()
        except Exception:
            q = ""

        if not q:
            self._render_bills(self._all_bills)
            return

        filtered: List[Dict[str, Any]] = []
        for b in self._all_bills:
            receipt = str(b.get("receipt_no", "")).lower()
            pay = str(b.get("payment_type", "")).lower()
            bid = str(b.get("id", "")).lower()
            if q in receipt or q in pay or q in bid:
                filtered.append(b)

        self._render_bills(filtered)

    def _render_bills(self, bills: List[Dict[str, Any]]) -> None:
        self.bills_table.setSortingEnabled(False)
        self.bills_table.setRowCount(len(bills))
        
        total_sales = 0
        total_tax = 0
        
        for i, bill in enumerate(bills):
            self.bills_table.setItem(i, 0, QTableWidgetItem(str(bill.get("id", ""))))
            self.bills_table.setItem(i, 1, QTableWidgetItem(bill.get("receipt_no", "")))
            
            timestamp = str(bill.get("timestamp", ""))[:19]
            self.bills_table.setItem(i, 2, QTableWidgetItem(timestamp))
            
            subtotal = bill.get("subtotal", 0)
            tax = bill.get("tax", 0)
            total = bill.get("total", 0)
            
            sub_item = QTableWidgetItem(f"Rs {subtotal:,.2f}")
            sub_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.bills_table.setItem(i, 3, sub_item)

            tax_item = QTableWidgetItem(f"Rs {tax:,.2f}")
            tax_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.bills_table.setItem(i, 4, tax_item)

            total_item = QTableWidgetItem(f"Rs {total:,.2f}")
            total_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.bills_table.setItem(i, 5, total_item)
            self.bills_table.setItem(i, 6, QTableWidgetItem(bill.get("payment_type", "")))
            
            total_sales += total
            total_tax += tax

        self._set_kpi_value(self.kpi_bills, str(len(bills)))
        self._set_kpi_value(self.kpi_sales, f"Rs {total_sales:,.2f}")
        self._set_kpi_value(self.kpi_tax, f"Rs {total_tax:,.2f}")

        self.bills_table.setSortingEnabled(True)

    def _set_kpi_value(self, card: QFrame, value: str) -> None:
        lbl = card.findChild(QLabel, "statValue")
        if lbl:
            lbl.setText(value)
    
    def _view_bill_details(self) -> None:
        """Show details of the selected bill."""
        row = self.bills_table.currentRow()
        if row < 0:
            return
        
        bill_id = int(self.bills_table.item(row, 0).text())
        receipt_no = self.bills_table.item(row, 1).text()
        
        # Get bill with items
        bill = db.get_sale(bill_id)
        if not bill:
            QMessageBox.warning(self, "Error", "Could not load bill details.")
            return
        
        items = bill.get("items", [])
        items_text = "\n".join([
            f"  • {item.get('product_name', '')} x{item.get('qty', 0)} @ Rs {item.get('price_at_sale', 0):,.2f}"
            for item in items
        ])
        
        details = f"""Receipt: {receipt_no}
Date: {str(bill.get('timestamp', ''))[:19]}
Cashier: {bill.get('cashier', 'Unknown')}
Payment: {bill.get('payment_type', '')}

Items:
{items_text}

Subtotal: Rs {bill.get('subtotal', 0):,.2f}
Tax: Rs {bill.get('tax', 0):,.2f}
Discount: Rs {bill.get('discount', 0):,.2f}
Total: Rs {bill.get('total', 0):,.2f}"""
        
        dialog = BillDetailsDialog(bill, receipt_no, self)
        dialog.exec()

    def _open_selected_details(self) -> None:
        self._view_bill_details()


class BillDetailsDialog(QDialog):
    def __init__(self, bill: Dict[str, Any], receipt_no: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bill = bill
        self.receipt_no = receipt_no
        self.setWindowTitle(f"Bill Details - {receipt_no}")
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        header = QFrame()
        header.setProperty("card", True)
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 16, 18, 16)
        h.setSpacing(12)

        left = QWidget()
        l = QVBoxLayout(left)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)

        title = QLabel(f"Receipt {self.receipt_no}")
        title.setProperty("heading", True)
        l.addWidget(title)

        meta = QLabel(
            f"{str(self.bill.get('timestamp', ''))[:19]} • "
            f"Cashier: {self.bill.get('cashier', 'Unknown')} • "
            f"Payment: {self.bill.get('payment_type', '')}"
        )
        meta.setProperty("subheading", True)
        l.addWidget(meta)

        h.addWidget(left, 1)

        close_btn = QPushButton("Close")
        close_btn.setProperty("secondary", "true")
        close_btn.clicked.connect(self.accept)
        h.addWidget(close_btn)

        layout.addWidget(header)
        apply_shadow(header, blur_radius=26, y_offset=10)

        table_card = QFrame()
        table_card.setProperty("card", True)
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(16, 16, 16, 16)
        tl.setSpacing(10)

        items_table = QTableWidget()
        items_table.setObjectName("billItemsTable")
        items_table.setProperty("embedded", True)
        items_table.setShowGrid(False)
        items_table.setColumnCount(4)
        items_table.setHorizontalHeaderLabels(["Item", "Qty", "Unit", "Total"])
        items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        items_table.setColumnWidth(1, 70)
        items_table.setColumnWidth(2, 90)
        items_table.setColumnWidth(3, 110)
        items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        items_table.setAlternatingRowColors(True)
        items_table.verticalHeader().setVisible(False)
        items_table.verticalHeader().setDefaultSectionSize(42)

        items = list(self.bill.get("items", []) or [])
        items_table.setRowCount(len(items))
        for i, item in enumerate(items):
            name = str(item.get("product_name", ""))
            qty = int(item.get("qty", 0) or 0)
            unit = float(item.get("price_at_sale", 0) or 0)
            total = qty * unit

            items_table.setItem(i, 0, QTableWidgetItem(name))

            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            items_table.setItem(i, 1, qty_item)

            unit_item = QTableWidgetItem(f"Rs {unit:,.2f}")
            unit_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            items_table.setItem(i, 2, unit_item)

            total_item = QTableWidgetItem(f"Rs {total:,.2f}")
            total_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            items_table.setItem(i, 3, total_item)

        tl.addWidget(items_table)
        layout.addWidget(table_card, 1)
        apply_shadow(table_card, blur_radius=22, y_offset=8)

        totals = QFrame()
        totals.setProperty("card", True)
        t = QHBoxLayout(totals)
        t.setContentsMargins(18, 14, 18, 14)
        t.setSpacing(18)

        def kv(label: str, value: str) -> QWidget:
            w = QWidget()
            wl = QVBoxLayout(w)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(2)
            a = QLabel(label)
            a.setProperty("subheading", True)
            b = QLabel(value)
            b.setObjectName("detailValue")
            wl.addWidget(a)
            wl.addWidget(b)
            return w

        subtotal = float(self.bill.get("subtotal", 0) or 0)
        tax = float(self.bill.get("tax", 0) or 0)
        discount = float(self.bill.get("discount", 0) or 0)
        total = float(self.bill.get("total", 0) or 0)

        t.addWidget(kv("Subtotal", f"Rs {subtotal:,.2f}"))
        t.addWidget(kv("Tax", f"Rs {tax:,.2f}"))
        t.addWidget(kv("Discount", f"Rs {discount:,.2f}"))
        t.addStretch(1)
        total_box = kv("Total", f"Rs {total:,.2f}")
        total_value = total_box.findChild(QLabel, "detailValue")
        if total_value:
            total_value.setObjectName("detailTotal")
        t.addWidget(total_box)

        layout.addWidget(totals)
        apply_shadow(totals, blur_radius=22, y_offset=8)


class ArchiveManagerDialog(QDialog):
    """Dialog for viewing and managing archived bills."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Bill Archive Manager")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self._setup_ui()
        self._load_archive_stats()
        self._load_archived_bills()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(22, 22, 22, 22)

        header = QFrame()
        header.setProperty("card", True)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(12)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        title = QLabel("📦 Bill Archive")
        title.setProperty("heading", True)
        left_layout.addWidget(title)

        subtitle = QLabel("Archived bills (older or manually archived)")
        subtitle.setProperty("subheading", True)
        left_layout.addWidget(subtitle)

        header_layout.addWidget(left, 1)

        archive_now_btn = QPushButton("🗃️ Archive Old Bills")
        archive_now_btn.setProperty("primary", "true")
        archive_now_btn.clicked.connect(self._archive_old_bills)
        header_layout.addWidget(archive_now_btn)

        close_btn = QPushButton("Close")
        close_btn.setProperty("secondary", "true")
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)
        apply_shadow(header, blur_radius=26, y_offset=10)

        # Filters + Search
        filters = QFrame()
        filters.setProperty("card", True)
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(18, 14, 18, 14)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(self._make_label("From"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-12))
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(self._make_label("To"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date)

        filter_btn = QPushButton("Apply")
        filter_btn.setProperty("primary", "true")
        filter_btn.clicked.connect(self._load_archived_bills)
        filter_layout.addWidget(filter_btn)

        filter_layout.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search receipt / payment…")
        self.search_input.setProperty("search", "true")
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._apply_text_filter)
        filter_layout.addWidget(self.search_input)

        layout.addWidget(filters)
        apply_shadow(filters, blur_radius=22, y_offset=8)

        # KPIs
        kpis = QWidget()
        kpi_layout = QHBoxLayout(kpis)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(12)

        self.kpi_archived = self._make_kpi("Archived Bills", "0", icon="📦", tone="neutral")
        self.kpi_value = self._make_kpi("Total Value", "Rs 0.00", icon="💰", tone="primary")
        kpi_layout.addWidget(self.kpi_archived)
        kpi_layout.addWidget(self.kpi_value)
        kpi_layout.addStretch(1)
        layout.addWidget(kpis)

        # Table (card)
        table_card = QFrame()
        table_card.setProperty("card", True)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(10)

        self.archive_table = QTableWidget()
        self.archive_table.setObjectName("historyTable")
        self.archive_table.setProperty("embedded", True)
        self.archive_table.setShowGrid(False)
        self.archive_table.setColumnCount(6)
        self.archive_table.setHorizontalHeaderLabels(["ID", "Receipt No", "Date", "Total", "Payment", "Archived At"])
        self.archive_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.archive_table.setAlternatingRowColors(True)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.archive_table.setSortingEnabled(True)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.verticalHeader().setDefaultSectionSize(44)
        table_layout.addWidget(self.archive_table)

        # Footer actions
        btn_bar = QWidget()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch(1)

        restore_btn = QPushButton("♻️ Restore Selected")
        restore_btn.clicked.connect(self._restore_selected_bill)
        btn_layout.addWidget(restore_btn)

        table_layout.addWidget(btn_bar)

        layout.addWidget(table_card, 1)
        apply_shadow(table_card, blur_radius=22, y_offset=8)

        self._all_bills: List[Dict[str, Any]] = []

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl

    def _make_kpi(self, title: str, value: str, *, icon: str, tone: str) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        card.setProperty("statTone", tone)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        top_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        top_layout.addWidget(title_label, 1)

        layout.addWidget(top)

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        layout.addWidget(value_label)

        apply_shadow(card, blur_radius=18, y_offset=6)
        return card

    def _apply_text_filter(self) -> None:
        q = ""
        try:
            q = (self.search_input.text() or "").strip().lower()
        except Exception:
            q = ""

        if not q:
            self._render_bills(self._all_bills)
            return

        filtered: List[Dict[str, Any]] = []
        for b in self._all_bills:
            receipt = str(b.get("receipt_no", "")).lower()
            pay = str(b.get("payment_type", "")).lower()
            bid = str(b.get("id", "")).lower()
            if q in receipt or q in pay or q in bid:
                filtered.append(b)

        self._render_bills(filtered)

    def _render_bills(self, bills: List[Dict[str, Any]]) -> None:
        self.archive_table.setSortingEnabled(False)
        self.archive_table.setRowCount(len(bills))

        total_value = 0.0
        for i, bill in enumerate(bills):
            self.archive_table.setItem(i, 0, QTableWidgetItem(str(bill.get("id", ""))))
            self.archive_table.setItem(i, 1, QTableWidgetItem(bill.get("receipt_no", "")))
            self.archive_table.setItem(i, 2, QTableWidgetItem(str(bill.get("timestamp", ""))[:19]))
            total = float(bill.get("total", 0) or 0)
            total_value += total
            total_item = QTableWidgetItem(f"Rs {total:,.2f}")
            total_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.archive_table.setItem(i, 3, total_item)
            self.archive_table.setItem(i, 4, QTableWidgetItem(bill.get("payment_type", "")))
            self.archive_table.setItem(i, 5, QTableWidgetItem(str(bill.get("archived_at", ""))[:19]))

        self._set_kpi_value(self.kpi_archived, str(len(bills)))
        self._set_kpi_value(self.kpi_value, f"Rs {total_value:,.2f}")

        self.archive_table.setSortingEnabled(True)

    def _set_kpi_value(self, card: QFrame, value: str) -> None:
        lbl = card.findChild(QLabel, "statValue")
        if lbl:
            lbl.setText(value)
    
    def _load_archive_stats(self) -> None:
        """Load and display archive statistics."""
        stats = db.get_archive_stats()
        count = stats.get("count", 0)
        total_value = stats.get("total_value", 0)
        if hasattr(self, "kpi_archived"):
            self._set_kpi_value(self.kpi_archived, str(count))
        if hasattr(self, "kpi_value"):
            self._set_kpi_value(self.kpi_value, f"Rs {float(total_value or 0):,.2f}")
    
    def _load_archived_bills(self) -> None:
        """Load archived bills into the table."""
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        
        bills = db.get_archived_bills(start, end)
        self._all_bills = list(bills or [])
        self._apply_text_filter()
    
    def _archive_old_bills(self) -> None:
        """Trigger archiving of old bills."""
        reply = QMessageBox.question(
            self,
            "Confirm Archive",
            "This will archive all bills older than 6 months.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message, count = db.archive_old_bills()
            if success:
                QMessageBox.information(self, "Success", message)
                self._load_archive_stats()
                self._load_archived_bills()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def _restore_selected_bill(self) -> None:
        """Restore the selected archived bill."""
        row = self.archive_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a bill to restore.")
            return
        
        bill_id = int(self.archive_table.item(row, 0).text())
        receipt_no = self.archive_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Restore bill {receipt_no} to active sales?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = db.restore_archived_bill(bill_id)
            if success:
                QMessageBox.information(self, "Success", message)
                self._load_archive_stats()
                self._load_archived_bills()
            else:
                QMessageBox.warning(self, "Error", message)


class AdminPanel(QWidget):
    """Refactored Admin Panel with Sidebar Layout."""
    
    def __init__(self):
        super().__init__()
        self.nav_btns: List[QPushButton] = []
        self._setup_ui()
        self._init_header_actions_widgets()
        self._set_header_actions(0)
        
    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # Sidebar
        self._setup_sidebar()
        main_layout.addWidget(self.sidebar_frame)
        
        # Content Area
        main_layout.addWidget(self._create_content_area())
    
    def _create_content_area(self) -> QWidget:
        """Create and return the content area widget."""
        content_frame = QWidget()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(16)
        
        # Header
        content_layout.addWidget(self._create_header())
        
        # Stacked Widget for Pages
        self.stack = QStackedWidget()
        self._create_pages()
        content_layout.addWidget(self.stack)
        
        return content_frame
    
    def _create_header(self) -> QFrame:
        """Create and return the header frame."""
        self.header_frame = QFrame()
        self.header_frame.setObjectName("contentHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(16)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.header_title = QLabel("Dashboard")
        self.header_title.setObjectName("headerTitle")
        left_layout.addWidget(self.header_title)

        self.header_subtitle = QLabel("Overview of your business performance")
        self.header_subtitle.setObjectName("headerSubtitle")
        left_layout.addWidget(self.header_subtitle)

        header_layout.addWidget(left, 1)

        self.header_actions = QWidget()
        self.header_actions_layout = QHBoxLayout(self.header_actions)
        self.header_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.header_actions_layout.setSpacing(10)
        header_layout.addWidget(self.header_actions, 0, Qt.AlignmentFlag.AlignRight)
        apply_shadow(self.header_frame, blur_radius=26, y_offset=10)
        return self.header_frame
    
    def _create_pages(self) -> None:
        """Create all pages and add them to the stack."""
        self.dashboard_page = self._create_dashboard_page()
        self.sales_history_page = self._create_sales_history_page()
        self.menu_page = self._create_menu_page()
        self.expenses_page = self._create_expenses_page()
        self.users_page = self._create_users_page()
        self.settings_page = self._create_settings_page()
        self.backup_page = self._create_backup_page()
        
        pages = [
            self.dashboard_page,
            self.sales_history_page,
            self.menu_page,
            self.expenses_page,
            self.users_page,
            self.settings_page,
            self.backup_page,
        ]
        for page in pages:
            self.stack.addWidget(page)
        
    def _setup_sidebar(self) -> None:
        """Set up the sidebar navigation."""
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("adminSidebar")
        
        layout = QVBoxLayout(self.sidebar_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo Area
        logo_area = QWidget()
        logo_area.setObjectName("adminLogo")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(10, 20, 10, 20)
        logo_layout.setSpacing(10)
        
        logo_img = QLabel()
        logo_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_img.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_img.setText("🥒")
            logo_img.setStyleSheet(f"font-size: 40px; color: {COLORS['primary']};")
        
        logo_layout.addWidget(logo_img)
        
        admin_lbl = QLabel("Admin Panel")
        admin_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        admin_lbl.setObjectName("adminPanelTitle")
        logo_layout.addWidget(admin_lbl)
        
        layout.addWidget(logo_area)
        
        # Navigation Buttons
        nav_items = [
            ("Dashboard", "📊"),
            ("Sales History", "🧾"),
            ("Menu Manager", "📋"),
            ("Expenses", "💸"),
            ("Users", "👥"),
            ("Settings", "⚙️"),
            ("Backups", "💾"),
        ]
        
        for index, (text, icon) in enumerate(nav_items):
            self._add_sidebar_btn(text, icon, index, layout)
        
        layout.addStretch()
        apply_shadow(self.sidebar_frame, blur_radius=30, x_offset=8, y_offset=0)
            
    def _add_sidebar_btn(self, text: str, icon: str, index: int, layout: QVBoxLayout) -> None:
        """Add a navigation button to the sidebar."""
        btn = QPushButton(f"{icon}  {text}")
        btn.setObjectName("sidebarBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, i=index, b=btn, t=text: self._switch_page(i, b, t))
        layout.addWidget(btn)
        self.nav_btns.append(btn)
        
        if index == 0:
            btn.setProperty("active", "true")
            
    def _switch_page(self, index: int, btn: QPushButton, title: str) -> None:
        """Switch to the specified page and update UI state."""
        self.stack.setCurrentIndex(index)
        self.header_title.setText(title)
        
        # Update subtitle
        _, subtitle = PAGE_TITLES.get(index, ("", ""))
        self.header_subtitle.setText(subtitle)

        self._set_header_actions(index)
        
        # Update active state for all buttons
        self._update_nav_button_states(btn)
        
        # Refresh data
        self._refresh_page_data(index)

    def _clear_layout(self, layout: QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setVisible(False)

    def _init_header_actions_widgets(self) -> None:
        """Create header action widgets once and reuse them across pages."""
        # Dashboard
        self.dashboard_refresh_btn = QPushButton("🔄 Refresh")
        self.dashboard_refresh_btn.setProperty("primary", "true")
        self.dashboard_refresh_btn.clicked.connect(self.load_dashboard)

        # Sales History
        self.sales_refresh_btn = QPushButton("🔄 Refresh")
        self.sales_refresh_btn.setProperty("primary", "true")
        self.sales_refresh_btn.clicked.connect(self.load_sales_history)

        # Menu
        self.menu_search = QLineEdit()
        self.menu_search.setPlaceholderText("🔍 Search menu...")
        self.menu_search.setProperty("search", "true")
        self.menu_search.setMinimumWidth(260)
        self.menu_search.textChanged.connect(self._filter_menu)

        self.menu_more_btn = QPushButton("More ▾")
        self.menu_more_btn.setProperty("secondary", "true")
        more_menu = QMenu(self.menu_more_btn)
        more_menu.addAction("📥 Import Excel", self._import_from_excel)
        more_menu.addAction("🧾 Sales History", self._open_sales_history)
        more_menu.addAction("📦 Bill Archive", self._open_archive_manager)
        self.menu_more_btn.setMenu(more_menu)

        self.menu_add_btn = QPushButton("+ New Item")
        self.menu_add_btn.setProperty("primary", "true")
        self.menu_add_btn.clicked.connect(self._add_menu_item)

        # Expenses
        self.expenses_date_label = QLabel("Date")
        self.expenses_date_label.setProperty("subheading", True)
        self.expense_date_filter = QDateEdit()
        self.expense_date_filter.setCalendarPopup(True)
        self.expense_date_filter.setDate(QDate.currentDate())
        self.expense_date_filter.dateChanged.connect(self.load_expenses)

        self.expense_add_btn = QPushButton("+ Add Expense")
        self.expense_add_btn.setProperty("primary", "true")
        self.expense_add_btn.clicked.connect(self._add_expense)

        # Users
        self.user_add_btn = QPushButton("+ New User")
        self.user_add_btn.setProperty("primary", "true")
        self.user_add_btn.clicked.connect(self._add_user)

        # Settings
        self.settings_save_btn = QPushButton("✓ Save")
        self.settings_save_btn.setProperty("primary", "true")
        self.settings_save_btn.clicked.connect(self._save_settings)

        # Backups
        self.backup_create_btn = QPushButton("📥 New Backup")
        self.backup_create_btn.setProperty("primary", "true")
        self.backup_create_btn.clicked.connect(self._create_backup)

        self.backup_restore_btn = QPushButton("📤 Restore…")
        self.backup_restore_btn.setProperty("secondary", "true")
        self.backup_restore_btn.clicked.connect(self._restore_backup_from_file)

    def _set_header_actions(self, index: int) -> None:
        if not hasattr(self, "header_actions_layout"):
            return

        self._clear_layout(self.header_actions_layout)

        actions: List[QWidget] = []
        if index == 0:
            actions = [self.dashboard_refresh_btn]
        elif index == 1:
            actions = [self.sales_refresh_btn]
        elif index == 2:
            actions = [self.menu_search, self.menu_more_btn, self.menu_add_btn]
        elif index == 3:
            actions = [self.expenses_date_label, self.expense_date_filter, self.expense_add_btn]
        elif index == 4:
            actions = [self.user_add_btn]
        elif index == 5:
            actions = [self.settings_save_btn]
        elif index == 6:
            actions = [self.backup_create_btn, self.backup_restore_btn]

        for w in actions:
            w.setVisible(True)
            self.header_actions_layout.addWidget(w)
    
    def _update_nav_button_states(self, active_btn: QPushButton) -> None:
        """Update the active state of navigation buttons."""
        for b in self.nav_btns:
            is_active = b == active_btn
            b.setProperty("active", "true" if is_active else "false")
            b.style().unpolish(b)
            b.style().polish(b)
    
    def _refresh_page_data(self, index: int) -> None:
        """Refresh data for the specified page."""
        refresh_methods = {
            0: self.load_dashboard,
            1: self.load_sales_history,
            2: self.load_menu,
            3: self.load_expenses,
            4: self.load_users,
            5: self.load_settings,
            6: self.load_backups,
        }
        
        if index in refresh_methods:
            try:
                refresh_methods[index]()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load data: {e}")

    # ==================== Page Creation Methods ====================

    def _create_scrolled_page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        scroll = self._create_scroll_area()
        scroll.setObjectName("adminScroll")

        content = QWidget()
        content.setObjectName("adminPageContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        return page, layout

    def _create_plain_page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        return page, layout

    def _create_card(
        self,
        layout_cls=QVBoxLayout,
        *,
        margins: tuple[int, int, int, int] = (16, 16, 16, 16),
        spacing: int = 12,
    ):
        frame = QFrame()
        frame.setProperty("card", True)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = layout_cls(frame)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        return frame, layout

    def _create_card_header(self, title: str, *, right_widget: Optional[QWidget] = None) -> QWidget:
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        lbl = QLabel(title)
        lbl.setObjectName("sectionTitle")
        header_layout.addWidget(lbl)

        header_layout.addStretch()

        if right_widget is not None:
            header_layout.addWidget(right_widget)

        return header
    
    def _create_dashboard_page(self) -> QWidget:
        """Create the dashboard page."""
        page, layout = self._create_scrolled_page()
        layout.setSpacing(24)
        
        # Stats Grid
        layout.addLayout(self._create_stats_grid())
        
        # Top Items Section
        self.top_items_count = QLabel("")
        self.top_items_count.setProperty("subheading", True)

        top_items_card, top_items_card_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        top_items_card_layout.addWidget(self._create_card_header("🏆 Top Selling Items Today", right_widget=self.top_items_count))

        self.top_items_table = self._create_table(
            columns=["Item", "Qty"],
            stretch_column=0,
            min_height=300
        )
        top_items_card_layout.addWidget(self.top_items_table)
        layout.addWidget(top_items_card)
        return page
    
    def _create_stats_grid(self) -> QGridLayout:
        """Create the statistics grid layout."""
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(20)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        
        self.total_sales_card = self._create_stat_card("Revenue Today", "Rs 0.00", icon="💰", tone="primary")
        self.total_expenses_card = self._create_stat_card("Total Expenses", "Rs 0.00", icon="💸", tone="danger")
        self.net_profit_card = self._create_stat_card("Net Profit", "Rs 0.00", icon="📈", tone="success")
        self.total_orders_card = self._create_stat_card("Orders", "0", icon="📦", tone="neutral")
        self.total_tax_card = self._create_stat_card("Tax Collected", "Rs 0.00", icon="📊", tone="primary")
        self.avg_order_card = self._create_stat_card("Avg Order", "Rs 0.00", icon="🧾", tone="neutral")
        
        grid.addWidget(self.total_sales_card, 0, 0)
        grid.addWidget(self.total_expenses_card, 0, 1)
        grid.addWidget(self.net_profit_card, 0, 2)
        grid.addWidget(self.total_orders_card, 1, 0)
        grid.addWidget(self.total_tax_card, 1, 1)
        grid.addWidget(self.avg_order_card, 1, 2)
        
        return grid

    def _create_stat_card(self, title: str, value: str, *, icon: str = "•", tone: str = "neutral") -> QFrame:
        """Create a statistics card widget."""
        frame = QFrame()
        frame.setProperty("card", True)
        frame.setProperty("statTone", tone)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        frame.setMinimumHeight(96)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        top_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        title_label.setWordWrap(True)
        top_layout.addWidget(title_label, 1)

        layout.addWidget(top)
        
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        layout.addWidget(value_label)

        return frame

    def _create_sales_history_page(self) -> QWidget:
        """Create the Sales History page (full-size within the admin panel)."""
        page, layout = self._create_scrolled_page()
        layout.setSpacing(18)
        layout.setContentsMargins(16, 16, 16, 16)

        # Filters
        filters_card, filters_layout = self._create_card(layout_cls=QHBoxLayout, margins=(12, 12, 12, 12), spacing=10)
        filters_layout.addWidget(self._create_label("From"))
        self.sales_start_date = QDateEdit()
        self.sales_start_date.setCalendarPopup(True)
        self.sales_start_date.setDate(QDate.currentDate().addDays(-30))
        filters_layout.addWidget(self.sales_start_date)

        filters_layout.addWidget(self._create_label("To"))
        self.sales_end_date = QDateEdit()
        self.sales_end_date.setCalendarPopup(True)
        self.sales_end_date.setDate(QDate.currentDate())
        filters_layout.addWidget(self.sales_end_date)

        today_btn = QPushButton("Today")
        today_btn.setProperty("secondary", "true")
        today_btn.clicked.connect(self._sales_filter_today)
        filters_layout.addWidget(today_btn)

        week_btn = QPushButton("7 days")
        week_btn.setProperty("secondary", "true")
        week_btn.clicked.connect(lambda: self._sales_set_last_days(7))
        filters_layout.addWidget(week_btn)

        month_btn = QPushButton("30 days")
        month_btn.setProperty("secondary", "true")
        month_btn.clicked.connect(lambda: self._sales_set_last_days(30))
        filters_layout.addWidget(month_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("primary", "true")
        apply_btn.clicked.connect(self.load_sales_history)
        filters_layout.addWidget(apply_btn)

        filters_layout.addStretch(1)

        self.sales_search = QLineEdit()
        self.sales_search.setPlaceholderText("🔍 Search receipt / payment / ID...")
        self.sales_search.setProperty("search", "true")
        self.sales_search.setMinimumWidth(280)
        self.sales_search.textChanged.connect(self._apply_sales_text_filter)
        filters_layout.addWidget(self.sales_search)

        layout.addWidget(filters_card)

        # KPIs
        kpis = QHBoxLayout()
        kpis.setSpacing(16)
        self.sales_kpi_bills = self._create_stat_card("Bills", "0", icon="🧾", tone="neutral")
        self.sales_kpi_sales = self._create_stat_card("Total Sales", "Rs 0.00", icon="💰", tone="primary")
        self.sales_kpi_tax = self._create_stat_card("Total Tax", "Rs 0.00", icon="📊", tone="neutral")
        kpis.addWidget(self.sales_kpi_bills)
        kpis.addWidget(self.sales_kpi_sales)
        kpis.addWidget(self.sales_kpi_tax)
        layout.addLayout(kpis)

        # Table
        table_card, table_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        self.sales_count = QLabel("")
        self.sales_count.setProperty("subheading", True)
        table_layout.addWidget(self._create_card_header("🧾 Bills", right_widget=self.sales_count))

        self.sales_table = self._create_table(
            columns=["ID", "Receipt", "Date", "Subtotal", "Tax", "Total", "Payment"],
            stretch_column=1,
            column_widths={0: 70, 2: 170, 3: 120, 4: 110, 5: 120, 6: 120},
            min_height=520,
        )
        self.sales_table.setObjectName("historyTable")
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sales_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.doubleClicked.connect(self._open_selected_sale_details)
        table_layout.addWidget(self.sales_table)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch(1)
        details_btn = QPushButton("👁 View Details")
        details_btn.clicked.connect(self._open_selected_sale_details)
        footer_layout.addWidget(details_btn)
        table_layout.addWidget(footer)

        layout.addWidget(table_card, 1)

        self._sales_all_bills: List[Dict[str, Any]] = []
        QTimer.singleShot(0, self.load_sales_history)
        return page

    def _create_menu_page(self) -> QWidget:
        """Create the menu management page."""
        page, layout = self._create_plain_page()
        
        # Table
        self.menu_count = QLabel("")
        self.menu_count.setProperty("subheading", True)

        table_card, table_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        table_layout.addWidget(self._create_card_header("📋 Menu Items", right_widget=self.menu_count))

        self.menu_table = self._create_table(
            columns=["ID", "Name", "Category", "Price", "Tax %", "Status"],
            stretch_column=1,
            column_widths={0: 60, 2: 130, 3: 120, 4: 90, 5: 100}
        )
        self.menu_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.menu_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.menu_table.setAlternatingRowColors(True)
        self.menu_table.doubleClicked.connect(self._edit_menu_item)
        table_layout.addWidget(self.menu_table)

        # Footer actions (kept inside the same card for a cleaner hierarchy)
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)

        hint = QLabel("Tip: Double-click a row to edit.")
        hint.setProperty("subheading", True)
        footer_layout.addWidget(hint)
        footer_layout.addStretch()

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(self._edit_menu_item)
        footer_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setProperty("danger", "true")
        delete_btn.clicked.connect(self._delete_menu_item)
        footer_layout.addWidget(delete_btn)

        table_layout.addWidget(footer)
        layout.addWidget(table_card, 1)
        
        return page
    
    def _create_expenses_page(self) -> QWidget:
        """Create the expenses page."""
        page, layout = self._create_plain_page()
        
        # Table
        self.expenses_count = QLabel("")
        self.expenses_count.setProperty("subheading", True)

        table_card, table_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        table_layout.addWidget(self._create_card_header("💸 Expenses", right_widget=self.expenses_count))

        self.expenses_table = self._create_table(
            columns=["Description", "Category", "Amount", "Time"],
            stretch_column=0,
            column_widths={1: 150, 2: 120, 3: 100}
        )
        self.expenses_table.setAlternatingRowColors(True)
        self.expenses_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.expenses_table)

        # Footer actions
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addStretch()
        delete_btn = QPushButton("🗑️ Delete Expense")
        delete_btn.setProperty("danger", "true")
        delete_btn.clicked.connect(self._delete_expense)
        action_layout.addWidget(delete_btn)
        table_layout.addWidget(action_bar)

        layout.addWidget(table_card, 1)
        
        return page

    def _create_users_page(self) -> QWidget:
        """Create the users management page."""
        page, layout = self._create_plain_page()
        
        # Table
        self.users_count = QLabel("")
        self.users_count.setProperty("subheading", True)

        table_card, table_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        table_layout.addWidget(self._create_card_header("👥 Users", right_widget=self.users_count))

        self.users_table = self._create_table(
            columns=["ID", "Username", "Role", "Created"],
            stretch_column=1,
            column_widths={0: 60, 2: 120, 3: 180}
        )
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.users_table)

        # Footer actions
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addStretch()
        delete_btn = QPushButton("🗑️ Delete User")
        delete_btn.setProperty("danger", "true")
        delete_btn.clicked.connect(self._delete_user)
        action_layout.addWidget(delete_btn)
        table_layout.addWidget(action_bar)

        layout.addWidget(table_card, 1)
        
        return page

    def _create_settings_page(self) -> QWidget:
        """Create the settings page."""
        page, layout = self._create_scrolled_page()
        info = self._create_restaurant_info_section()
        tax = self._create_tax_settings_section()
        receipt = self._create_receipt_settings_section()
        security = self._create_security_section()

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(info, 0, 0)
        grid.addWidget(tax, 0, 1)
        grid.addWidget(receipt, 1, 0, 1, 2)
        grid.addWidget(security, 2, 0, 1, 2)

        layout.addLayout(grid)

        return page
    
    def _create_restaurant_info_section(self) -> QWidget:
        card, card_layout = self._create_card(margins=(18, 18, 18, 18), spacing=14)
        card_layout.addWidget(self._create_card_header("🏪 Restaurant Information"))

        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.restaurant_name = QLineEdit()
        form_layout.addRow(self._create_label("Name"), self.restaurant_name)

        self.restaurant_address = QLineEdit()
        form_layout.addRow(self._create_label("Address"), self.restaurant_address)

        self.restaurant_phone = QLineEdit()
        form_layout.addRow(self._create_label("Phone"), self.restaurant_phone)

        card_layout.addWidget(form)
        return card
    
    def _create_tax_settings_section(self) -> QWidget:
        card, card_layout = self._create_card(margins=(18, 18, 18, 18), spacing=14)
        card_layout.addWidget(self._create_card_header("💵 Tax & Currency"))

        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 100)
        self.tax_rate.setSuffix(" %")
        form_layout.addRow(self._create_label("Default Tax Rate"), self.tax_rate)

        self.currency_symbol = QLineEdit()
        self.currency_symbol.setMaximumWidth(140)
        form_layout.addRow(self._create_label("Currency Symbol"), self.currency_symbol)

        card_layout.addWidget(form)
        return card
    
    def _create_receipt_settings_section(self) -> QWidget:
        card, card_layout = self._create_card(margins=(18, 18, 18, 18), spacing=14)
        card_layout.addWidget(self._create_card_header("🧾 Receipt Settings"))

        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.receipt_footer = QLineEdit()
        form_layout.addRow(self._create_label("Footer Message"), self.receipt_footer)

        self.paper_size = QComboBox()
        self.paper_size.addItems(["80mm", "58mm"])
        self.paper_size.setToolTip("Select the physical width of your thermal printer paper.")
        form_layout.addRow(self._create_label("Paper Size"), self.paper_size)

        test_print_btn = QPushButton("🖨️ Test Print")
        test_print_btn.setProperty("secondary", "true")
        test_print_btn.clicked.connect(self._test_print)
        form_layout.addRow(self._create_label("Printer"), test_print_btn)

        card_layout.addWidget(form)
        return card

    def _create_security_section(self) -> QWidget:
        card, card_layout = self._create_card(margins=(18, 18, 18, 18), spacing=14)
        card_layout.addWidget(self._create_card_header("🔐 Security"))

        hint = QLabel("Change the admin password (current user).")
        hint.setProperty("subheading", True)
        card_layout.addWidget(hint)

        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(self._create_label("Current Password"), self.old_password_input)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(self._create_label("New Password"), self.new_password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(self._create_label("Confirm Password"), self.confirm_password_input)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch(1)
        change_btn = QPushButton("Change Password")
        change_btn.setProperty("primary", "true")
        change_btn.clicked.connect(self._change_admin_password)
        btn_layout.addWidget(change_btn)

        card_layout.addWidget(form)
        card_layout.addWidget(btn_row)
        return card
    
    def _create_label(self, text: str) -> QLabel:
        """Create a styled label."""
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl

    def _create_backup_page(self) -> QWidget:
        """Create the backup management page."""
        page, layout = self._create_plain_page()
        
        # List (in card)
        self.backups_count = QLabel("")
        self.backups_count.setProperty("subheading", True)

        table_card, table_layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        table_layout.addWidget(self._create_card_header("📁 Available Backups", right_widget=self.backups_count))
        
        self.backups_table = self._create_table(
            columns=["Filename", "Size", "Created"],
            stretch_column=0
        )
        self.backups_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.backups_table)

        # Footer actions
        btn_bar = QWidget()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        restore_sel_btn = QPushButton("📤 Restore Selected")
        restore_sel_btn.clicked.connect(self._restore_selected_backup)
        btn_layout.addWidget(restore_sel_btn)
        
        del_btn = QPushButton("🗑️ Delete")
        del_btn.setProperty("danger", "true")
        del_btn.clicked.connect(self._delete_backup)
        btn_layout.addWidget(del_btn)

        table_layout.addWidget(btn_bar)
        layout.addWidget(table_card, 1)
        
        return page

    # ==================== Helper Methods ====================
    
    def _create_scroll_area(self) -> QScrollArea:
        """Create a configured scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background-color: transparent;")
        return scroll
    
    def _create_table(
        self,
        columns: List[str],
        stretch_column: int = 0,
        column_widths: Optional[Dict[int, int]] = None,
        min_height: Optional[int] = None
    ) -> QTableWidget:
        """Create a configured table widget."""
        table = QTableWidget()
        table.setProperty("embedded", True)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setShowGrid(False)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Set stretch column
        table.horizontalHeader().setSectionResizeMode(
            stretch_column, QHeaderView.ResizeMode.Stretch
        )
        
        # Set fixed columns
        for col in range(len(columns)):
            if col != stretch_column:
                table.horizontalHeader().setSectionResizeMode(
                    col, QHeaderView.ResizeMode.Fixed
                )
        
        # Set column widths
        if column_widths:
            for col, width in column_widths.items():
                table.setColumnWidth(col, width)
        
        if min_height:
            table.setMinimumHeight(min_height)
        
        return table
    
    def _get_selected_row(self, table: QTableWidget) -> int:
        """Get the currently selected row index, or -1 if none."""
        return table.currentRow()
    
    def _show_selection_warning(self, message: str = "Please select an item first.") -> None:
        """Show a warning about missing selection."""
        QMessageBox.warning(self, "Selection Required", message)
    
    def _confirm_action(self, title: str, message: str) -> bool:
        """Show a confirmation dialog and return the result."""
        result = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return result == QMessageBox.StandardButton.Yes

    # ==================== Data Loading Methods ====================
    
    def load_data(self) -> None:
        """Load all data for all pages."""
        loaders = [
            self.load_dashboard,
            self.load_menu,
            self.load_expenses,
            self.load_users,
            self.load_settings,
            self.load_backups
        ]
        
        for loader in loaders:
            try:
                loader()
            except Exception as e:
                print(f"Error loading data: {e}")
        
    def load_dashboard(self) -> None:
        """Load dashboard data."""
        try:
            summary = db.get_daily_summary()
            profit_data = db.get_daily_profit()
            
            self._update_card_value(
                self.total_sales_card,
                f"{CURRENCY_PREFIX}{profit_data.get('total_revenue', 0):,.2f}"
            )
            self._update_card_value(
                self.total_expenses_card,
                f"{CURRENCY_PREFIX}{profit_data.get('total_expenses', 0):,.2f}",
                color=COLORS["warning"]
            )
            self._update_card_value(
                self.total_orders_card,
                str(summary.get("count", 0))
            )
            self._update_card_value(
                self.total_tax_card,
                f"{CURRENCY_PREFIX}{summary.get('tax', 0):,.2f}"
            )

            try:
                orders = float(summary.get("count", 0) or 0)
                revenue = float(profit_data.get("total_revenue", 0) or 0)
                avg = (revenue / orders) if orders > 0 else 0.0
            except Exception:
                avg = 0.0

            if hasattr(self, "avg_order_card") and self.avg_order_card is not None:
                self._update_card_value(self.avg_order_card, f"{CURRENCY_PREFIX}{avg:,.2f}")
            
            profit = profit_data.get('net_profit', 0)
            profit_color = COLORS["success"] if profit >= 0 else COLORS["danger"]
            self._update_card_value(
                self.net_profit_card,
                f"{CURRENCY_PREFIX}{profit:,.2f}",
                color=profit_color
            )
            
            # Update Top Items
            top_items = summary.get("top_items", [])
            if hasattr(self, "top_items_count") and self.top_items_count is not None:
                self.top_items_count.setText(f"{len(top_items)} items")
            self.top_items_table.setRowCount(len(top_items))
            for row, item in enumerate(top_items):
                self.top_items_table.setItem(
                    row, 0, QTableWidgetItem(item.get("product_name", "Unknown"))
                )
                self.top_items_table.setItem(
                    row, 1, QTableWidgetItem(str(item.get("total_qty", 0)))
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load dashboard: {e}")

    def _update_card_value(
        self, card: QFrame, text: str, color: Optional[str] = None
    ) -> None:
        """Update the value displayed in a stat card."""
        label = card.findChild(QLabel, "statValue")
        if label:
            label.setText(text)
            if color:
                label.setStyleSheet(f"color: {color};")
            else:
                label.setStyleSheet("")

    def load_menu(self) -> None:
        """Load menu items into the table."""
        try:
            items = db.get_all_menu_items(active_only=False)
            if hasattr(self, "menu_count") and self.menu_count is not None:
                self.menu_count.setText(f"{len(items)} items")
            self.menu_table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                self.menu_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.menu_table.setItem(row, 1, QTableWidgetItem(item["name"]))
                self.menu_table.setItem(
                    row, 2, QTableWidgetItem(item.get("category", "General"))
                )
                self.menu_table.setItem(
                    row, 3, QTableWidgetItem(f"{CURRENCY_PREFIX}{item.get('price', 0):,.2f}")
                )
                self.menu_table.setItem(
                    row, 4, QTableWidgetItem(f"{item.get('tax_rate', 0):.1f}%")
                )
                
                status = item.get("status", "active")
                status_item = QTableWidgetItem(status)
                status_color = COLORS["success"] if status == "active" else COLORS["danger"]
                status_item.setForeground(QColor(status_color))
                self.menu_table.setItem(row, 5, status_item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load menu: {e}")

    def load_expenses(self) -> None:
        """Load expenses into the table."""
        try:
            # Get date from filter
            selected_date = self.expense_date_filter.date().toString("yyyy-MM-dd")
            expenses = db.get_expenses(selected_date)
            if hasattr(self, "expenses_count") and self.expenses_count is not None:
                self.expenses_count.setText(f"{len(expenses)} entries • {selected_date}")
            self.expenses_table.setRowCount(len(expenses))
            
            for row, expense in enumerate(expenses):
                desc_item = QTableWidgetItem(str(expense["description"]))
                desc_item.setData(Qt.ItemDataRole.UserRole, expense["id"])
                self.expenses_table.setItem(row, 0, desc_item)
                
                self.expenses_table.setItem(
                    row, 1, QTableWidgetItem(expense.get("category", "General"))
                )
                
                amt_item = QTableWidgetItem(f"{CURRENCY_PREFIX}{expense['amount']:,.2f}")
                amt_item.setForeground(QColor(COLORS["warning"]))
                self.expenses_table.setItem(row, 2, amt_item)
                
                # Use the local_timestamp from our improved query
                timestamp_str = expense.get("local_timestamp", "")
                if timestamp_str and " " in timestamp_str:
                    time_str = timestamp_str.split(" ")[1][:5] # HH:MM
                else:
                    # Fallback to UTC timestamp column if local_timestamp missing
                    utc_ts = str(expense.get("timestamp", ""))
                    time_str = utc_ts.split(" ")[1][:5] if " " in utc_ts else "N/A"
                
                self.expenses_table.setItem(row, 3, QTableWidgetItem(time_str))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load expenses: {e}")

    def load_users(self) -> None:
        """Load users into the table."""
        try:
            users = db.get_all_users()
            if hasattr(self, "users_count") and self.users_count is not None:
                self.users_count.setText(f"{len(users)} users")
            self.users_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                self.users_table.setItem(row, 1, QTableWidgetItem(user["username"]))
                
                role_item = QTableWidgetItem(user["role"])
                if user["role"] == "Admin":
                    role_item.setForeground(QColor(COLORS["primary"]))
                self.users_table.setItem(row, 2, role_item)
                
                created = str(user.get("created_at", ""))[:19]
                self.users_table.setItem(row, 3, QTableWidgetItem(created))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load users: {e}")

    def load_settings(self) -> None:
        """Load settings into the form."""
        try:
            settings = db.get_all_settings()
            
            self.restaurant_name.setText(settings.get("restaurant_name", ""))
            self.restaurant_address.setText(settings.get("restaurant_address", ""))
            self.restaurant_phone.setText(settings.get("restaurant_phone", ""))
            self.tax_rate.setValue(float(settings.get("tax_rate", DEFAULT_TAX_RATE)))
            self.currency_symbol.setText(settings.get("currency_symbol", "Rs"))
            self.receipt_footer.setText(
                settings.get("receipt_footer", "Thank you for visiting!")
            )
            
            # Load paper size setting
            paper_val = settings.get("receipt_paper_size", "80mm")
            if "58" in paper_val:
                self.paper_size.setCurrentText("58mm")
            else:
                self.paper_size.setCurrentText("80mm")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load settings: {e}")

    def load_backups(self) -> None:
        """Load available backups into the table."""
        try:
            backups = backup_manager.list_backups()
            if hasattr(self, "backups_count") and self.backups_count is not None:
                self.backups_count.setText(f"{len(backups)} files")
            self.backups_table.setRowCount(len(backups))
            
            for row, backup in enumerate(backups):
                self.backups_table.setItem(
                    row, 0, QTableWidgetItem(backup["filename"])
                )
                self.backups_table.setItem(
                    row, 1, QTableWidgetItem(f"{backup['size']/1024:.1f} KB")
                )
                self.backups_table.setItem(
                    row, 2, QTableWidgetItem(backup["created"])
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load backups: {e}")

    # ==================== Action Handlers ====================

    def _add_menu_item(self) -> None:
        """Open dialog to add a new menu item."""
        dialog = MenuItemDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                success = db.add_menu_item(
                    data["name"], data["category"],
                    data["price"], data["tax_rate"]
                )
                if success:
                    self.load_menu()
                    QMessageBox.information(
                        self, "Success", f"Item '{data['name']}' added!"
                    )
                else:
                    QMessageBox.warning(self, "Error", "Failed to add item.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add item: {e}")

    def _edit_menu_item(self) -> None:
        """Open dialog to edit the selected menu item."""
        row = self._get_selected_row(self.menu_table)
        if row < 0:
            return
        
        try:
            item_id = int(self.menu_table.item(row, 0).text())
            
            price_text = self.menu_table.item(row, 3).text()
            price = float(price_text.replace(CURRENCY_PREFIX, "").replace(",", "").strip())
            
            tax_text = self.menu_table.item(row, 4).text()
            tax = float(tax_text.replace("%", "").strip())
            
            item = {
                "id": item_id,
                "name": self.menu_table.item(row, 1).text(),
                "category": self.menu_table.item(row, 2).text(),
                "price": price,
                "tax_rate": tax,
                "status": self.menu_table.item(row, 5).text()
            }
            
            dialog = MenuItemDialog(self, item)
            if dialog.exec():
                data = dialog.get_data()
                success = db.update_menu_item(
                    item_id, data["name"], data["category"],
                    data["price"], data["tax_rate"], data["status"]
                )
                if success:
                    self.load_menu()
                    QMessageBox.information(self, "Success", "Item updated!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update item.")
        except (ValueError, AttributeError) as e:
            QMessageBox.warning(self, "Error", f"Invalid data format: {e}")

    def _delete_menu_item(self) -> None:
        """Delete or archive the selected menu item."""
        row = self._get_selected_row(self.menu_table)
        if row < 0:
            self._show_selection_warning("Select an item to delete.")
            return
        
        try:
            item_id = int(self.menu_table.item(row, 0).text())
            name = self.menu_table.item(row, 1).text()
            count = db.check_item_usage(item_id)
            
            if count == 0:
                if self._confirm_action("Confirm Delete", f"Delete '{name}'?"):
                    db.permanently_delete_menu_item(item_id)
                    self.load_menu()
            else:
                self._handle_item_in_use(item_id, name, count)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete item: {e}")
    
    def _handle_item_in_use(self, item_id: int, name: str, count: int) -> None:
        """Handle deletion of an item that has sales history."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Item in Use")
        msg.setText(f"'{name}' has been sold {count} times.")
        msg.setInformativeText("Archive (soft delete) or Permanently Delete?")
        
        archive_btn = msg.addButton("Archive", QMessageBox.ButtonRole.ActionRole)
        perm_btn = msg.addButton("Permanent Delete", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == archive_btn:
            db.delete_menu_item(item_id)
            self.load_menu()
        elif clicked == perm_btn:
            if self._confirm_action(
                "Warning", "This deletes sales history! Continue?"
            ):
                db.permanently_delete_menu_item(item_id)
                self.load_menu()

    def _import_from_excel(self) -> None:
        """Open dialog to import menu items from Excel."""
        dialog = ExcelImportDialog(self)
        dialog.exec()
        self.load_menu()  # Refresh menu after import
    
    def _open_archive_manager(self) -> None:
        """Open the bill archive manager dialog."""
        dialog = ArchiveManagerDialog(self)
        dialog.exec()
    
    def _open_sales_history(self) -> None:
        """Go to the Sales History page (full-screen in the admin panel)."""
        try:
            btn = self.nav_btns[1] if len(self.nav_btns) > 1 else None
            if btn is not None:
                self._switch_page(1, btn, "Sales History")
            else:
                self.stack.setCurrentIndex(1)
        except Exception:
            pass

    def _sales_filter_today(self) -> None:
        today = QDate.currentDate()
        self.sales_start_date.setDate(today)
        self.sales_end_date.setDate(today)
        self.load_sales_history()

    def _sales_set_last_days(self, days: int) -> None:
        end = QDate.currentDate()
        start = end.addDays(-max(0, int(days)))
        self.sales_start_date.setDate(start)
        self.sales_end_date.setDate(end)
        self.load_sales_history()

    def load_sales_history(self) -> None:
        try:
            start = self.sales_start_date.date().toString("yyyy-MM-dd")
            end = self.sales_end_date.date().toString("yyyy-MM-dd")
            bills = db.get_bills_by_date_range(start, end)
            self._sales_all_bills = list(bills or [])
            self._apply_sales_text_filter()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load sales history: {e}")

    def _apply_sales_text_filter(self) -> None:
        q = ""
        try:
            q = (self.sales_search.text() or "").strip().lower()
        except Exception:
            q = ""

        if not q:
            self._render_sales(self._sales_all_bills)
            return

        filtered: List[Dict[str, Any]] = []
        for b in self._sales_all_bills:
            receipt = str(b.get("receipt_no", "")).lower()
            pay = str(b.get("payment_type", "")).lower()
            bid = str(b.get("id", "")).lower()
            if q in receipt or q in pay or q in bid:
                filtered.append(b)

        self._render_sales(filtered)

    def _render_sales(self, bills: List[Dict[str, Any]]) -> None:
        self.sales_table.setSortingEnabled(False)
        self.sales_table.setRowCount(len(bills))

        total_sales = 0.0
        total_tax = 0.0

        for i, bill in enumerate(bills):
            self.sales_table.setItem(i, 0, QTableWidgetItem(str(bill.get("id", ""))))
            self.sales_table.setItem(i, 1, QTableWidgetItem(str(bill.get("receipt_no", ""))))
            self.sales_table.setItem(i, 2, QTableWidgetItem(str(bill.get("timestamp", ""))[:19]))

            subtotal = float(bill.get("subtotal", 0) or 0)
            tax = float(bill.get("tax", 0) or 0)
            total = float(bill.get("total", 0) or 0)

            sub_item = QTableWidgetItem(f"{CURRENCY_PREFIX}{subtotal:,.2f}")
            sub_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.sales_table.setItem(i, 3, sub_item)

            tax_item = QTableWidgetItem(f"{CURRENCY_PREFIX}{tax:,.2f}")
            tax_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.sales_table.setItem(i, 4, tax_item)

            total_item = QTableWidgetItem(f"{CURRENCY_PREFIX}{total:,.2f}")
            total_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.sales_table.setItem(i, 5, total_item)

            self.sales_table.setItem(i, 6, QTableWidgetItem(str(bill.get("payment_type", ""))))

            total_sales += total
            total_tax += tax

        if hasattr(self, "sales_count") and self.sales_count is not None:
            start = self.sales_start_date.date().toString("yyyy-MM-dd")
            end = self.sales_end_date.date().toString("yyyy-MM-dd")
            self.sales_count.setText(f"{len(bills)} bills • {start} → {end}")

        self._update_card_value(self.sales_kpi_bills, str(len(bills)))
        self._update_card_value(self.sales_kpi_sales, f"{CURRENCY_PREFIX}{total_sales:,.2f}")
        self._update_card_value(self.sales_kpi_tax, f"{CURRENCY_PREFIX}{total_tax:,.2f}")

        self.sales_table.setSortingEnabled(True)

    def _open_selected_sale_details(self) -> None:
        row = self.sales_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a bill to view details.")
            return

        try:
            bill_id = int(self.sales_table.item(row, 0).text())
            receipt_no = self.sales_table.item(row, 1).text()
            bill = db.get_sale(bill_id)
            if not bill:
                QMessageBox.warning(self, "Error", "Could not load bill details.")
                return
            dialog = BillDetailsDialog(bill, receipt_no, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open details: {e}")

    def _filter_menu(self, text: str) -> None:
        """Filter menu items by search text."""
        search_text = text.lower()
        for row in range(self.menu_table.rowCount()):
            match = False
            for col in [1, 2]:  # Name and Category columns
                item = self.menu_table.item(row, col)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.menu_table.setRowHidden(row, not match)

    def _add_expense(self) -> None:
        """Open dialog to add a new expense."""
        dialog = ExpenseDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                user_id = auth.current_user.get("id") if auth.current_user else None
                # Call add_expense (which now raises on error)
                db.add_expense(
                    data["description"], data["amount"],
                    data["category"], user_id
                )
                self.load_expenses()
                self.load_dashboard()
                QMessageBox.information(self, "Success", "Expense added successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add expense: {e}")

    def _delete_expense(self) -> None:
        """Delete the selected expense."""
        row = self._get_selected_row(self.expenses_table)
        if row < 0:
            self._show_selection_warning("Select an expense to delete.")
            return
        
        try:
            item = self.expenses_table.item(row, 0)
            if item is None:
                return
            
            exp_id = item.data(Qt.ItemDataRole.UserRole)
            if self._confirm_action("Confirm Delete", "Delete this expense?"):
                db.delete_expense(exp_id)
                self.load_expenses()
                self.load_dashboard()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete expense: {e}")

    def _add_user(self) -> None:
        """Open dialog to add a new user."""
        dialog = UserDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            if db.get_user(data["username"]):
                QMessageBox.warning(self, "Error", "Username already taken")
                return
            
            try:
                hashed = bcrypt.hashpw(
                    data["password"].encode(), bcrypt.gensalt()
                ).decode()
                
                if db.add_user(data["username"], hashed, data["role"]):
                    self.load_users()
                    QMessageBox.information(self, "Success", "User created")
                else:
                    QMessageBox.warning(self, "Error", "Failed to create user")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create user: {e}")

    def _delete_user(self) -> None:
        """Delete the selected user."""
        row = self._get_selected_row(self.users_table)
        if row < 0:
            self._show_selection_warning("Select a user to delete.")
            return
        
        try:
            user_id = int(self.users_table.item(row, 0).text())
            
            # Prevent self-deletion
            if auth.current_user and user_id == auth.current_user.get("id"):
                QMessageBox.warning(self, "Error", "Cannot delete your own account")
                return
            
            if self._confirm_action("Confirm Delete", "Delete this user?"):
                if db.delete_user(user_id):
                    self.load_users()
                    QMessageBox.information(self, "Success", "User deleted successfully.")
                else:
                    QMessageBox.warning(
                        self, "Error",
                        "Could not delete user. They may have associated records."
                    )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete user: {e}")

    def _save_settings(self) -> None:
        """Save all settings to the database."""
        try:
            settings_to_save = {
                "restaurant_name": self.restaurant_name.text(),
                "restaurant_address": self.restaurant_address.text(),
                "restaurant_phone": self.restaurant_phone.text(),
                "tax_rate": str(self.tax_rate.value()),
                "currency_symbol": self.currency_symbol.text(),
                "receipt_footer": self.receipt_footer.text(),
                "receipt_paper_size": self.paper_size.currentText()
            }
            
            for key, value in settings_to_save.items():
                db.set_setting(key, value)
            
            QMessageBox.information(self, "Success", "Settings saved successfully")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")

    def _change_admin_password(self) -> None:
        if not auth.current_user or auth.current_user.get("role") != "Admin":
            QMessageBox.warning(self, "Not Allowed", "Only an admin can change the admin password.")
            return

        old_pw = (self.old_password_input.text() or "").strip()
        new_pw = (self.new_password_input.text() or "").strip()
        confirm = (self.confirm_password_input.text() or "").strip()

        if not old_pw or not new_pw:
            QMessageBox.warning(self, "Missing", "Please enter current and new password.")
            return
        if new_pw != confirm:
            QMessageBox.warning(self, "Mismatch", "New password and confirm password do not match.")
            return

        success, msg = auth.change_password(old_pw, new_pw)
        if success:
            self.old_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _test_print(self) -> None:
        """Test the printer configuration."""
        try:
            from printer import printer
            success, msg = printer.test_print()
            if success:
                QMessageBox.information(self, "Print Test", "Print dialog opened")
            else:
                QMessageBox.warning(self, "Print Error", msg)
        except ImportError:
            QMessageBox.warning(self, "Error", "Printer module not available")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Print test failed: {e}")

    def _create_backup(self) -> None:
        """Create a new database backup."""
        try:
            success, result = backup_manager.create_backup()
            if success:
                self.load_backups()
                QMessageBox.information(self, "Backup", f"Backup created!\n{result}")
            else:
                QMessageBox.warning(self, "Error", result)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Backup failed: {e}")

    def _restore_backup_from_file(self) -> None:
        """Restore database from a user-selected file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Database Backup", "", "Database Files (*.db)"
        )
        if path:
            self._perform_restore(path)

    def _restore_selected_backup(self) -> None:
        """Restore the selected backup from the list."""
        row = self._get_selected_row(self.backups_table)
        if row < 0:
            self._show_selection_warning("Select a backup to restore.")
            return
        
        filename = self.backups_table.item(row, 0).text()
        backups = backup_manager.list_backups()
        path = next(
            (b["path"] for b in backups if b["filename"] == filename), None
        )
        
        if path:
            self._perform_restore(path)

    def _perform_restore(self, path: str) -> None:
        """Perform the actual restore operation."""
        warning_msg = (
            "This will overwrite all current data with the backup.\n"
            "This action cannot be undone. Continue?"
        )
        
        result = QMessageBox.warning(
            self, "Confirm Restore", warning_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                success, msg = backup_manager.restore_backup(path)
                if success:
                    self.load_data()
                    QMessageBox.information(
                        self, "Success", "Database restored successfully"
                    )
                else:
                    QMessageBox.warning(self, "Error", msg)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Restore failed: {e}")

    def _delete_backup(self) -> None:
        """Delete the selected backup file."""
        row = self._get_selected_row(self.backups_table)
        if row < 0:
            self._show_selection_warning("Select a backup to delete.")
            return
        
        filename = self.backups_table.item(row, 0).text()
        backups = backup_manager.list_backups()
        path = next(
            (b["path"] for b in backups if b["filename"] == filename), None
        )
        
        if path and self._confirm_action("Confirm Delete", "Delete this backup?"):
            try:
                if backup_manager.delete_backup(path):
                    self.load_backups()
                    QMessageBox.information(self, "Success", "Backup deleted")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete backup: {e}")
