"""
AuraPOS Professional - Admin Panel (Fixed UI)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QFrame, QMessageBox,
    QDialog, QFormLayout, QGroupBox, QTextEdit, QFileDialog,
    QHeaderView, QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import bcrypt

from database import db
from utils.auth import auth
from utils.backup import backup_manager


# All styles now handled by global theme stylesheets (styles.qss / styles_light.qss)



class MenuItemDialog(QDialog):
    """Dialog for adding/editing menu items."""
    
    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit Item" if item else "Add New Item")
        self.setMinimumWidth(450)
        self
        self.setup_ui()
        
        if item:
            self.load_item(item)
        else:
            # Load default tax rate for new items
            try:
                settings = db.get_all_settings()
                default_tax = float(settings.get("tax_rate", 5))
                self.tax_input.setValue(default_tax)
            except Exception:
                self.tax_input.setValue(5.0)  # Default 5%

    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Edit Item" if self.item else "Add New Item")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        form = QFrame()
        form
        form_layout = QFormLayout(form)
        form_layout.setSpacing(15)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name")
        self.name_input
        form_layout.addRow(self._label("Name:"), self.name_input)
        
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(["Starters", "Main Course", "Beverages", "Desserts", "Sides", "Fast Food", "General"])
        self.category_input
        form_layout.addRow(self._label("Category:"), self.category_input)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("Rs ")
        self.price_input
        form_layout.addRow(self._label("Price:"), self.price_input)
        
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setDecimals(2)
        self.tax_input.setSuffix(" %")
        self.tax_input
        form_layout.addRow(self._label("Tax Rate:"), self.tax_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(["active", "inactive"])
        self.status_input
        form_layout.addRow(self._label("Status:"), self.status_input)
        
        layout.addWidget(form)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ Save Item")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _label(self, text):
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def validate_and_accept(self):
        """Validate input before accepting."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter an item name")
            self.name_input.setFocus()
            return
        
        if self.price_input.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid price")
            self.price_input.setFocus()
            return
        
        self.accept()
    
    def load_item(self, item):
        self.name_input.setText(item.get("name", ""))
        self.category_input.setCurrentText(item.get("category", "General"))
        self.price_input.setValue(float(item.get("price", 0)))
        self.tax_input.setValue(float(item.get("tax_rate", 0)))
        self.status_input.setCurrentText(item.get("status", "active"))
    
    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "category": self.category_input.currentText().strip() or "General",
            "price": self.price_input.value(),
            "tax_rate": self.tax_input.value(),
            "status": self.status_input.currentText()
        }


class UserDialog(QDialog):
    """Dialog for adding users."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")
        self.setMinimumWidth(450)
        self
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Add New User")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        form = QFrame()
        form
        form_layout = QFormLayout(form)
        form_layout.setSpacing(15)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Minimum 3 characters")
        self.username_input
        form_layout.addRow(self._label("Username:"), self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimum 6 characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input
        form_layout.addRow(self._label("Password:"), self.password_input)
        
        self.role_input = QComboBox()
        self.role_input.addItems(["Staff", "Admin"])
        self.role_input
        form_layout.addRow(self._label("Role:"), self.role_input)
        
        layout.addWidget(form)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ Create User")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _label(self, text):
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def validate_and_accept(self):
        """Validate input before accepting."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if len(username) < 3:
            QMessageBox.warning(self, "Validation Error", "Username must be at least 3 characters")
            self.username_input.setFocus()
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters")
            self.password_input.setFocus()
            return
        
        self.accept()
    
    def get_data(self):
        return {
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "role": self.role_input.currentText()
        }


class AdminPanel(QWidget):
    """Admin panel with menu management, reports, settings, and user management."""
    
    def __init__(self):
        super().__init__()
        self
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()

        
        self.tabs.addTab(self.create_menu_tab(), "📋 Menu Manager")
        self.tabs.addTab(self.create_reports_tab(), "📊 Reports")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ Settings")
        self.tabs.addTab(self.create_users_tab(), "👥 Users")
        self.tabs.addTab(self.create_backup_tab(), "💾 Backup")
        
        layout.addWidget(self.tabs)
    
    def create_menu_tab(self):
        widget = QWidget()
        widget
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        toolbar = QHBoxLayout()
        
        self.menu_search = QLineEdit()
        self.menu_search.setPlaceholderText("🔍 Search menu items...")
        self.menu_search
        self.menu_search.textChanged.connect(self.filter_menu)
        toolbar.addWidget(self.menu_search, 1)
        
        add_btn = QPushButton("+ Add Item")
        add_btn.setProperty("primary", "true")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_menu_item)
        toolbar.addWidget(add_btn)
        
        layout.addLayout(toolbar)
        
        self.menu_table = QTableWidget()
        self.menu_table.setColumnCount(6)
        self.menu_table.setHorizontalHeaderLabels(["ID", "Name", "Category", "Price", "Tax %", "Status"])
        # Set column widths - ID fixed, Name stretches, rest fixed
        self.menu_table.setColumnWidth(0, 60)   # ID
        self.menu_table.setColumnWidth(2, 130)  # Category
        self.menu_table.setColumnWidth(3, 140)  # Price
        self.menu_table.setColumnWidth(4, 70)   # Tax %
        self.menu_table.setColumnWidth(5, 80)   # Status
        self.menu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.menu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.menu_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.menu_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.menu_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.menu_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.menu_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.menu_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.menu_table.setAlternatingRowColors(True)
        self.menu_table
        self.menu_table.doubleClicked.connect(self.edit_menu_item)
        layout.addWidget(self.menu_table)
        
        action_bar = QHBoxLayout()
        action_bar.addStretch()
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self.edit_menu_item)
        action_bar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setObjectName("deleteBtn") # Use objectName for danger style from global sheet
        delete_btn.setProperty("danger", "true") # Or use property if supported, but let's stick to consistent pattern
        delete_btn.clicked.connect(self.delete_menu_item)
        action_bar.addWidget(delete_btn)
        
        layout.addLayout(action_bar)
        
        return widget
    
    def create_reports_tab(self):
        widget = QWidget()
        widget
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        self.total_sales_card = self.create_stat_card("💰 Total Sales", "Rs 0.00")
        cards_layout.addWidget(self.total_sales_card)
        
        self.total_orders_card = self.create_stat_card("📦 Orders Today", "0")
        cards_layout.addWidget(self.total_orders_card)
        
        self.total_tax_card = self.create_stat_card("📊 Tax Collected", "Rs 0.00")
        cards_layout.addWidget(self.total_tax_card)
        
        layout.addLayout(cards_layout)
        
        top_frame = QFrame()
        top_frame
        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(20, 20, 20, 20)
        
        top_title = QLabel("🏆 Top Selling Items Today")
        top_title.setObjectName("sectionTitle")
        top_layout.addWidget(top_title)
        
        self.top_items_table = QTableWidget()
        self.top_items_table.setColumnCount(2)
        self.top_items_table.setHorizontalHeaderLabels(["Item", "Quantity Sold"])
        self.top_items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_items_table
        top_layout.addWidget(self.top_items_table)
        
        layout.addWidget(top_frame)
        
        refresh_btn = QPushButton("🔄 Refresh Reports")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setProperty("primary", "true")
        refresh_btn.clicked.connect(self.load_reports)
        layout.addWidget(refresh_btn)
        
        return widget
    
    def create_stat_card(self, title, value):
        frame = QFrame()
        frame
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel(title)
        title_label.setProperty("subheading", True)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        return frame
    
    def create_settings_tab(self):
        widget = QWidget()
        widget
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        info_group = QGroupBox("🏪 Restaurant Information")
        info_group
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(12)
        
        self.restaurant_name = QLineEdit()
        self.restaurant_name
        info_layout.addRow(self._label("Name:"), self.restaurant_name)
        
        self.restaurant_address = QLineEdit()
        self.restaurant_address
        info_layout.addRow(self._label("Address:"), self.restaurant_address)
        
        self.restaurant_phone = QLineEdit()
        self.restaurant_phone
        info_layout.addRow(self._label("Phone:"), self.restaurant_phone)
        
        layout.addWidget(info_group)
        
        tax_group = QGroupBox("💵 Tax & Currency")
        tax_group
        tax_layout = QFormLayout(tax_group)
        tax_layout.setSpacing(12)
        
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 100)
        self.tax_rate.setSuffix(" %")
        self.tax_rate
        tax_layout.addRow(self._label("Default Tax Rate:"), self.tax_rate)
        
        self.currency_symbol = QLineEdit()
        self.currency_symbol.setMaximumWidth(100)
        self.currency_symbol
        tax_layout.addRow(self._label("Currency Symbol:"), self.currency_symbol)
        
        layout.addWidget(tax_group)
        
        receipt_group = QGroupBox("🧾 Receipt Settings")
        receipt_group
        receipt_layout = QFormLayout(receipt_group)
        receipt_layout.setSpacing(12)
        
        self.receipt_footer = QLineEdit()
        self.receipt_footer
        receipt_layout.addRow(self._label("Footer Message:"), self.receipt_footer)
        
        test_print_btn = QPushButton("🖨️ Test Print")
        test_print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #888888;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #252525;
                color: #EEEEEE;
                border-color: #00ADB5;
            }
        """)
        test_print_btn.clicked.connect(self.test_print)
        receipt_layout.addRow(self._label("Printer:"), test_print_btn)
        
        layout.addWidget(receipt_group)
        
        layout.addStretch()
        
        save_btn = QPushButton("✓ Save Settings")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        return widget
    
    def _label(self, text):
        lbl = QLabel(text)
        lbl.setProperty("subheading", True)
        return lbl
    
    def create_users_tab(self):
        widget = QWidget()
        widget
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        add_user_btn = QPushButton("+ Add User")
        add_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_user_btn.setProperty("primary", "true")
        add_user_btn.clicked.connect(self.add_user)
        toolbar.addWidget(add_user_btn)
        
        layout.addLayout(toolbar)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Created"])
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.users_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.users_table.setColumnWidth(2, 120)
        self.users_table.setColumnWidth(3, 180)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.verticalHeader().setVisible(False)
        layout.addWidget(self.users_table)
        
        action_bar = QHBoxLayout()
        action_bar.addStretch()
        
        delete_btn = QPushButton("🗑️ Delete User")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setProperty("danger", "true")
        delete_btn.clicked.connect(self.delete_user)
        action_bar.addWidget(delete_btn)
        
        layout.addLayout(action_bar)
        
        return widget
    
    def create_backup_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        actions_frame = QFrame()
        actions_frame.setProperty("card", True)
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(20, 20, 20, 20)
        
        backup_btn = QPushButton("📥 Create Backup")
        backup_btn.setProperty("primary", "true")
        backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        backup_btn.clicked.connect(self.create_backup)
        actions_layout.addWidget(backup_btn)
        
        restore_btn = QPushButton("📤 Restore from File...")
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.clicked.connect(self.restore_backup)
        actions_layout.addWidget(restore_btn)
        
        actions_layout.addStretch()
        layout.addWidget(actions_frame)
        
        backups_frame = QFrame()
        backups_frame.setProperty("card", True)
        backups_layout = QVBoxLayout(backups_frame)
        backups_layout.setContentsMargins(20, 20, 20, 20)
        
        backups_title = QLabel("📁 Available Backups")
        backups_title.setObjectName("sectionTitle")
        backups_layout.addWidget(backups_title)
        
        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(3)
        self.backups_table.setHorizontalHeaderLabels(["Filename", "Size", "Created"])
        self.backups_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.backups_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.backups_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.backups_table.setColumnWidth(1, 100)
        self.backups_table.setColumnWidth(2, 180)
        self.backups_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.backups_table.verticalHeader().setVisible(False)
        backups_layout.addWidget(self.backups_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        restore_selected_btn = QPushButton("📤 Restore Selected")
        restore_selected_btn
        restore_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_selected_btn.clicked.connect(self.restore_selected_backup)
        btn_layout.addWidget(restore_selected_btn)
        
        delete_backup_btn = QPushButton("🗑️ Delete")
        delete_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_backup_btn.setProperty("danger", "true")
        delete_backup_btn.clicked.connect(self.delete_backup)
        btn_layout.addWidget(delete_backup_btn)
        
        backups_layout.addLayout(btn_layout)
        layout.addWidget(backups_frame)
        
        return widget
    
    # ==================== Data Loading ====================
    
    def load_data(self):
        """Load all data for admin panel."""
        try:
            self.load_menu()
        except Exception as e:
            print(f"Error loading menu: {e}")
        
        try:
            self.load_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        try:
            self.load_users()
        except Exception as e:
            print(f"Error loading users: {e}")
        
        try:
            self.load_backups()
        except Exception as e:
            print(f"Error loading backups: {e}")
        
        try:
            self.load_reports()
        except Exception as e:
            print(f"Error loading reports: {e}")
    
    def load_menu(self):
        items = db.get_all_menu_items(active_only=False)
        self.menu_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            self.menu_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
            self.menu_table.setItem(row, 1, QTableWidgetItem(item["name"]))
            self.menu_table.setItem(row, 2, QTableWidgetItem(item.get("category", "General")))
            self.menu_table.setItem(row, 3, QTableWidgetItem(f"Rs {item.get('price', 0):,.2f}"))
            self.menu_table.setItem(row, 4, QTableWidgetItem(f"{item.get('tax_rate', 0):.1f}%"))
            
            status_item = QTableWidgetItem(item.get("status", "active"))
            if item.get("status") == "active":
                status_item.setForeground(QColor("#4CAF50"))
            else:
                status_item.setForeground(QColor("#CF6679"))
            self.menu_table.setItem(row, 5, status_item)
    
    def filter_menu(self, text):
        for row in range(self.menu_table.rowCount()):
            name_item = self.menu_table.item(row, 1)
            category_item = self.menu_table.item(row, 2)
            if name_item and category_item:
                match = text.lower() in name_item.text().lower() or text.lower() in category_item.text().lower()
                self.menu_table.setRowHidden(row, not match)
    
    def load_settings(self):
        settings = db.get_all_settings()
        self.restaurant_name.setText(settings.get("restaurant_name", ""))
        self.restaurant_address.setText(settings.get("restaurant_address", ""))
        self.restaurant_phone.setText(settings.get("restaurant_phone", ""))
        self.tax_rate.setValue(float(settings.get("tax_rate", 5)))
        self.currency_symbol.setText(settings.get("currency_symbol", "Rs"))
        self.receipt_footer.setText(settings.get("receipt_footer", "Thank you for visiting!"))
    
    def load_users(self):
        users = db.get_all_users()
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user["username"]))
            
            role_item = QTableWidgetItem(user["role"])
            if user["role"] == "Admin":
                role_item.setForeground(QColor("#00ADB5"))
            self.users_table.setItem(row, 2, role_item)
            
            created = str(user.get("created_at", ""))[:19]  # Trim microseconds
            self.users_table.setItem(row, 3, QTableWidgetItem(created))
    
    def load_backups(self):
        backups = backup_manager.list_backups()
        self.backups_table.setRowCount(len(backups))
        
        for row, backup in enumerate(backups):
            self.backups_table.setItem(row, 0, QTableWidgetItem(backup["filename"]))
            size_kb = backup["size"] / 1024
            self.backups_table.setItem(row, 1, QTableWidgetItem(f"{size_kb:.1f} KB"))
            self.backups_table.setItem(row, 2, QTableWidgetItem(backup["created"]))
    
    def load_reports(self):
        summary = db.get_daily_summary()
        
        total_label = self.total_sales_card.findChild(QLabel, "value")
        if total_label:
            total_label.setText(f"Rs {summary.get('total', 0):,.2f}")
        
        orders_label = self.total_orders_card.findChild(QLabel, "value")
        if orders_label:
            orders_label.setText(str(summary.get("count", 0)))
        
        tax_label = self.total_tax_card.findChild(QLabel, "value")
        if tax_label:
            tax_label.setText(f"Rs {summary.get('tax', 0):,.2f}")
        
        top_items = summary.get("top_items", [])
        self.top_items_table.setRowCount(len(top_items))
        for row, item in enumerate(top_items):
            self.top_items_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.top_items_table.setItem(row, 1, QTableWidgetItem(str(item["total_qty"])))
    
    # ==================== Menu Actions ====================
    
    def add_menu_item(self):
        dialog = MenuItemDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            print(f"Adding menu item: {data}")  # Debug
            
            success = db.add_menu_item(
                name=data["name"],
                category=data["category"],
                price=data["price"],
                tax_rate=data["tax_rate"]
            )
            
            if success:
                self.load_menu()
                QMessageBox.information(self, "Success", f"Item '{data['name']}' added successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to add item. Check console for details.")
    
    def edit_menu_item(self):
        row = self.menu_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select an item to edit")
            return
        
        item_id = int(self.menu_table.item(row, 0).text())
        
        # Parse price - handle "Rs " prefix and commas
        price_text = self.menu_table.item(row, 3).text()
        price_text = price_text.replace("Rs", "").replace(",", "").strip()
        try:
            price = float(price_text)
        except ValueError:
            price = 0
        
        # Parse tax rate
        tax_text = self.menu_table.item(row, 4).text().replace("%", "").strip()
        try:
            tax_rate = float(tax_text)
        except ValueError:
            tax_rate = 0
        
        item = {
            "id": item_id,
            "name": self.menu_table.item(row, 1).text(),
            "category": self.menu_table.item(row, 2).text(),
            "price": price,
            "tax_rate": tax_rate,
            "status": self.menu_table.item(row, 5).text()
        }
        
        dialog = MenuItemDialog(self, item)
        if dialog.exec():
            data = dialog.get_data()
            if db.update_menu_item(item_id, data["name"], data["category"], data["price"], data["tax_rate"], data["status"]):
                self.load_menu()
                QMessageBox.information(self, "Success", "Item updated successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to update item")
    
    def delete_menu_item(self):
        """Handle menu item deletion with options."""
        row = self.menu_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select an item to delete")
            return
        
        item_id = int(self.menu_table.item(row, 0).text())
        name = self.menu_table.item(row, 1).text()
        
        # Check usage count
        count = db.check_item_usage(item_id)
        
        if count == 0:
            # Safe to delete permanently immediately
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       f"Permanently delete '{name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if db.permanently_delete_menu_item(item_id):
                     QMessageBox.information(self, "Success", "Item permanently deleted")
                     self.load_menu()
        else:
            # Has history - ask what to do
            msg = QMessageBox(self)
            msg.setWindowTitle("Item Has Sales History")
            msg.setText(f"'{name}' has been sold {count} times.")
            msg.setInformativeText("How would you like to delete this item?")
            
            # Add custom buttons
            archive_btn = msg.addButton("Archive (Soft Delete)", QMessageBox.ButtonRole.ActionRole)
            perm_btn = msg.addButton("Permanently Delete", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = msg.addButton(QMessageBox.StandardButton.Cancel)
            
            msg.exec()
            
            if msg.clickedButton() == archive_btn:
                # Soft delete
                if db.delete_menu_item(item_id):
                    QMessageBox.information(self, "Success", "Item archived (marked inactive)")
                    self.load_menu()
            elif msg.clickedButton() == perm_btn:
                # Double confirmation for permanent delete
                confirm = QMessageBox.warning(self, "Warning: Data Loss",
                                            f"Permanently deleting '{name}' will REMOVE it from {count} past receipts!\n\nThis cannot be undone. Are you sure?",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm == QMessageBox.StandardButton.Yes:
                    if db.permanently_delete_menu_item(item_id):
                        QMessageBox.information(self, "Success", "Item and history deleted")
                        self.load_menu()
    
    # ==================== Settings Actions ====================
    
    def save_settings(self):
        try:
            db.set_setting("restaurant_name", self.restaurant_name.text())
            db.set_setting("restaurant_address", self.restaurant_address.text())
            db.set_setting("restaurant_phone", self.restaurant_phone.text())
            db.set_setting("tax_rate", str(self.tax_rate.value()))
            db.set_setting("currency_symbol", self.currency_symbol.text())
            db.set_setting("receipt_footer", self.receipt_footer.text())
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")
    
    def test_print(self):
        from printer import printer
        success, message = printer.test_print()
        if success:
            QMessageBox.information(self, "Test Print", "Print dialog opened!\nSelect your printer to print the test page.")
        else:
            QMessageBox.warning(self, "Print Error", message)
    
    # ==================== User Actions ====================
    
    def add_user(self):
        dialog = UserDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Check if user exists
            existing = db.get_user(data["username"])
            if existing:
                QMessageBox.warning(self, "Error", "Username already exists!")
                return
            
            try:
                # Hash password
                password_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
                
                if db.add_user(data["username"], password_hash, data["role"]):
                    self.load_users()
                    QMessageBox.information(self, "Success", f"User '{data['username']}' created successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to create user")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create user: {e}")
    
    def delete_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select a user to delete")
            return
        
        user_id = int(self.users_table.item(row, 0).text())
        username = self.users_table.item(row, 1).text()
        
        if auth.current_user and username == auth.current_user.get("username"):
            QMessageBox.warning(self, "Error", "You cannot delete yourself!")
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete user '{username}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if db.delete_user(user_id):
                self.load_users()
                QMessageBox.information(self, "Success", f"User '{username}' deleted!")
    
    # ==================== Backup Actions ====================
    
    def create_backup(self):
        try:
            success, result = backup_manager.create_backup()
            if success:
                self.load_backups()
                QMessageBox.information(self, "Backup Created", f"Backup saved successfully!\n\n{result}")
            else:
                QMessageBox.warning(self, "Backup Error", result)
        except Exception as e:
            QMessageBox.warning(self, "Backup Error", str(e))
    
    def restore_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup File", "", "Database Files (*.db)")
        if file_path:
            reply = QMessageBox.warning(self, "Confirm Restore",
                                       "⚠️ This will replace ALL current data!\n\nAre you sure you want to continue?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._do_restore(file_path)
    
    def restore_selected_backup(self):
        row = self.backups_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select a backup from the list")
            return
        
        filename = self.backups_table.item(row, 0).text()
        backups = backup_manager.list_backups()
        backup_path = next((b["path"] for b in backups if b["filename"] == filename), None)
        
        if backup_path:
            reply = QMessageBox.warning(self, "Confirm Restore",
                                       f"⚠️ Restore from '{filename}'?\n\nThis will replace ALL current data!",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._do_restore(backup_path)
    
    def _do_restore(self, backup_path):
        """Perform the actual restore operation."""
        try:
            success, message = backup_manager.restore_backup(backup_path)
            
            if success:
                # Reload all data
                self.load_data()
                QMessageBox.information(self, "Restore Complete", 
                                       "Database restored successfully!\n\nAll data has been reloaded.")
            else:
                QMessageBox.warning(self, "Restore Error", message)
        except Exception as e:
            QMessageBox.warning(self, "Restore Error", str(e))
    
    def delete_backup(self):
        row = self.backups_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select a backup to delete")
            return
        
        filename = self.backups_table.item(row, 0).text()
        backups = backup_manager.list_backups()
        backup_path = next((b["path"] for b in backups if b["filename"] == filename), None)
        
        if backup_path:
            reply = QMessageBox.question(self, "Confirm Delete", f"Delete backup '{filename}'?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    success, message = backup_manager.delete_backup(backup_path)
                    if success:
                        self.load_backups()
                except Exception as e:
                    QMessageBox.warning(self, "Delete Error", str(e))
