"""
AuraPOS Professional - Main Billing Dashboard
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QFrame, QScrollArea, QMessageBox, QDialog, QComboBox,
    QDoubleSpinBox, QSpacerItem, QSizePolicy, QHeaderView,
    QAbstractItemView, QStackedWidget, QFormLayout, QGraphicsDropShadowEffect,
    QSpinBox, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QColor, QPixmap
import os

from database import db
from utils.auth import auth
from printer import printer
from ui.admin_panel import AdminPanel
from config import ASSETS_DIR


class CartItem:
    """Represents an item in the cart."""
    def __init__(self, product_id: int, name: str, price: float, qty: int = 1, tax_rate: float = 0):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.qty = qty
        self.tax_rate = tax_rate
    
    @property
    def subtotal(self) -> float:
        return self.price * self.qty
    
    @property
    def tax(self) -> float:
        return 0.0  # Tax is now calculated globally on subtotal
    
    @property
    def total(self) -> float:
        return self.subtotal


class PaymentDialog(QDialog):
    """Payment dialog for completing a sale."""
    
    def __init__(self, total: float, parent=None):
        super().__init__(parent)
        self.total = total
        self.setWindowTitle("Complete Payment")
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: #141414;")
        self.setup_ui()
    


    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Complete Payment")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ADB5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Total display
        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E1E1E, stop:1 #161616);
                border: 1px solid #2A2A2A;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        total_layout = QVBoxLayout(total_frame)
        
        total_label = QLabel("Total Amount")
        total_label.setStyleSheet("color: #888888; font-size: 13px;")
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_layout.addWidget(total_label)
        
        amount_label = QLabel(f"Rs {self.total:,.2f}")
        amount_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #00ADB5;")
        amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_layout.addWidget(amount_label)
        
        layout.addWidget(total_frame)
        
        # Payment options
        form_frame = QFrame()
        form_frame.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(15)
        
        # Payment type
        type_label = QLabel("Payment Method")
        type_label.setStyleSheet("color: #888888; font-size: 13px;")
        self.payment_type = QComboBox()
        self.payment_type.addItems(["Cash", "Card", "JazzCash", "Easypaisa", "Bank Transfer"])
        self.payment_type.setStyleSheet("""
            QComboBox {
                background-color: #1E1E1E;
                border: 2px solid #2A2A2A;
                border-radius: 8px;
                padding: 12px;
                color: #EEEEEE;
                font-size: 14px;
            }
            QComboBox:hover { border-color: #00ADB5; }
            QComboBox:focus { border-color: #00ADB5; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #00ADB5;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 8px;
                color: #EEEEEE;
                selection-background-color: #00ADB5;
                selection-color: #0A0A0A;
                padding: 5px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2A2A2A;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #00ADB5;
                color: #0A0A0A;
            }
        """)
        form_layout.addRow(type_label, self.payment_type)
        
        # Discount
        disc_label = QLabel("Discount")
        disc_label.setStyleSheet("color: #888888; font-size: 13px;")
        self.discount = QDoubleSpinBox()
        self.discount.setRange(0, self.total)
        self.discount.setPrefix("Rs ")
        self.discount.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1E1E1E;
                border: 2px solid #2A2A2A;
                border-radius: 8px;
                padding: 12px;
                color: #EEEEEE;
                font-size: 14px;
            }
            QDoubleSpinBox:focus { border-color: #00ADB5; }
        """)
        self.discount.valueChanged.connect(self.update_final)
        form_layout.addRow(disc_label, self.discount)
        
        # Final total
        final_title = QLabel("Final Total")
        final_title.setStyleSheet("color: #888888; font-size: 13px;")
        self.final_label = QLabel(f"Rs {self.total:,.2f}")
        self.final_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 18px;")
        form_layout.addRow(final_title, self.final_label)
        
        layout.addWidget(form_frame)
        
        layout.addSpacing(10)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2A2A2A;
                color: #EEEEEE;
                border: none;
                border-radius: 8px;
                padding: 14px 30px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #333333; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        pay_btn = QPushButton("✓ Complete Payment")
        pay_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #00878D);
                color: #0D0D0D;
                border: none;
                border-radius: 8px;
                padding: 14px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00CED8, stop:1 #00ADB5);
            }
        """)
        pay_btn.clicked.connect(self.accept)
        btn_layout.addWidget(pay_btn)
        
        layout.addLayout(btn_layout)
        
        # Auto-clear checkbox
        self.auto_clear_cb = QCheckBox("Auto-clear bill after payment")
        self.auto_clear_cb.setChecked(True)
        self.auto_clear_cb.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout.addWidget(self.auto_clear_cb)
    
    def update_final(self):
        final = self.total - self.discount.value()
        self.final_label.setText(f"Rs {final:,.2f}")
    
    def get_data(self):
        return {
            "payment_type": self.payment_type.currentText(),
            "discount": self.discount.value(),
            "auto_clear": self.auto_clear_cb.isChecked()
        }


class MainWindow(QMainWindow):
    """Main billing dashboard window."""
    
    logout_requested = pyqtSignal()
    MAX_BILLS = 5  # Maximum number of concurrent bills
    
    def __init__(self):
        super().__init__()
        # Multi-bill support: dict of bill_id -> list of CartItems
        self.bills = {1: []}  # Start with Bill 1
        self.current_bill_id = 1
        self.menu_items = []
        self._menu_items_cache = {}  # Cache menu items by id for speed
        self.is_dark_mode = True  # Default to dark mode
        
        self.setWindowTitle("Food Garden")
        self.setMinimumSize(1024, 600)  # Reduced for smaller screens
        self.showMaximized()            # Auto-maximize
        print("MainWindow: setup_ui starting...")
        self.setup_ui()
        print("MainWindow: setup_ui done. setup_shortcuts starting...")
        self.setup_shortcuts()
        print("MainWindow: load_menu starting...")
        self.load_menu()
        print("MainWindow: init done.")
    
    @property
    def cart(self) -> list:
        """Get current bill's cart."""
        return self.bills.get(self.current_bill_id, [])
    
    @cart.setter
    def cart(self, value):
        """Set current bill's cart."""
        self.bills[self.current_bill_id] = value
    
    def setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: #0A0A0A;")
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area
        self.content_stack = QStackedWidget()
        
        # Billing page
        billing_page = self.create_billing_page()
        self.content_stack.addWidget(billing_page)
        
        # Admin page
        self.admin_panel = AdminPanel()
        self.content_stack.addWidget(self.admin_panel)
        
        main_layout.addWidget(self.content_stack, 1)
    
    def create_header(self):
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(65)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 0, 25, 0)
        layout.setSpacing(15)
        
        # Logo
        logo_container = QWidget()
        logo_container.setCursor(Qt.CursorShape.PointingHandCursor)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)
        
        logo_img = QLabel()
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_img.setPixmap(pixmap.scaled(45, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_img.setText("🥒")
            logo_img.setStyleSheet("font-size: 24px;")
        
        logo_layout.addWidget(logo_img)
        
        logo_text = QLabel("Food Garden")
        logo_text.setObjectName("logoLabel")
        logo_layout.addWidget(logo_text)
        
        layout.addWidget(logo_container)
        
        layout.addStretch()
        
        # Navigation buttons
        self.billing_btn = QPushButton("💰 Billing")
        self.billing_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.billing_btn.setStyleSheet(self._get_nav_btn_style(True))
        self.billing_btn.clicked.connect(lambda: self.switch_page(0))
        layout.addWidget(self.billing_btn)
        
        self.admin_btn = QPushButton("⚙️ Admin")
        self.admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_btn.setStyleSheet(self._get_nav_btn_style(False))
        self.admin_btn.clicked.connect(lambda: self.switch_page(1))
        layout.addWidget(self.admin_btn)
        
        # Theme Toggle
        self.theme_btn = QPushButton("🌙" if self.is_dark_mode else "☀️")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Toggle Theme")
        self.theme_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EEEEEE;
                border: 1px solid #555555;
                font-size: 18px;
                border-radius: 18px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                border-color: #00ADB5;
                background-color: #252525;
            }
        """)
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)
        
        layout.addSpacing(10)
        
        # User info
        self.user_label = QLabel()
        self.user_label.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(self.user_label)
        
        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #CF6679;
                border-color: #CF6679;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        
        return header

    def toggle_theme(self):
        """Toggle between light and dark mode."""
        self.is_dark_mode = not self.is_dark_mode
        self.theme_btn.setText("🌙" if self.is_dark_mode else "☀️")
        
        # Determine stylesheet to load
        style_file = "styles.qss" if self.is_dark_mode else "styles_light.qss"
        try:
            with open(f"ui/{style_file}", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
        
        # Update dynamic styles
        bg_color = "#0A0A0A" if self.is_dark_mode else "#F5F5F5"
        self.central_widget.setStyleSheet(f"background-color: {bg_color};")
        
        nav_text_color = "#AAAAAA" if self.is_dark_mode else "#666666"
        nav_hover_bg = "#252525" if self.is_dark_mode else "#E0E0E0"
        
        # Refresh UI components
        self._update_bill_tabs_style()
        self.update_cart_display()
        
        # Update Admin Panel if active (it has its own style methods)
        if isinstance(self.admin_panel, AdminPanel):
            self.admin_panel.load_data()  # Reload data instead of UI re-setup if needed

    
    def _get_nav_btn_style(self, active):
        if active:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #00878D);
                    color: #0A0A0A;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00CED8, stop:1 #00ADB5);
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #1E1E1E;
                    color: #AAAAAA;
                    border: 1px solid #2A2A2A;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #252525;
                    color: #EEEEEE;
                    border-color: #00ADB5;
                }
            """
    
    def create_billing_page(self):
        page = QWidget()
        # page.setStyleSheet("background-color: #0A0A0A;") # Removed to allow inheritance
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Left side - Menu items
        left_panel = self.create_menu_panel()
        layout.addWidget(left_panel, 3)
        
        # Right side - Cart
        right_panel = self.create_cart_panel()
        layout.addWidget(right_panel, 2)
        
        return page
    
    def create_menu_panel(self):
        panel = QFrame()
        panel.setObjectName("menuPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        self.menu_title_label = QLabel("📋 Menu Items")
        self.menu_title_label.setObjectName("menuTitle")
        layout.addWidget(self.menu_title_label)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search items... (Press F1)")
        self.search_input.setProperty("search", True)
        self.search_input.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_input)
        
        # Category filter row
        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_label.setProperty("subheading", True)
        cat_layout.addWidget(cat_label)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self.filter_items)
        cat_layout.addWidget(self.category_filter)
        cat_layout.addStretch()
        layout.addLayout(cat_layout)
        
        # Items grid (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #333333;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00ADB5;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.items_container = QWidget()
        self.items_container.setStyleSheet("background-color: transparent;")
        self.items_layout = QGridLayout(self.items_container)
        self.items_layout.setSpacing(12)
        self.items_layout.setContentsMargins(5, 5, 5, 5)
        scroll.setWidget(self.items_container)
        
        layout.addWidget(scroll)
        
        return panel
    
    def create_cart_panel(self):
        panel = QFrame()
        panel.setObjectName("cartPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Bill tabs header
        tabs_header = QHBoxLayout()
        tabs_header.setSpacing(8)
        
        self.cart_header_label = QLabel("🛒 Current Order")
        self.cart_header_label.setObjectName("cartTitle")
        tabs_header.addWidget(self.cart_header_label)
        
        tabs_header.addStretch()
        
        # Bill tabs container
        self.bill_tabs_layout = QHBoxLayout()
        self.bill_tabs_layout.setSpacing(4)
        self.bill_tab_buttons = {}
        
        # Create first bill tab
        self._create_bill_tab(1)
        tabs_header.addLayout(self.bill_tabs_layout)
        
        # New bill button
        self.new_bill_btn = QPushButton("+")
        self.new_bill_btn.setFixedSize(32, 32)
        self.new_bill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_bill_btn.setToolTip("New Bill (F2)")
        self.new_bill_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #00ADB5;
                border: 2px solid #00ADB5;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #00ADB5;
                color: #0A0A0A;
            }
        """)
        self.new_bill_btn.clicked.connect(self.create_new_bill)
        tabs_header.addWidget(self.new_bill_btn)
        
        # Close bill button
        self.close_bill_btn = QPushButton("-")
        self.close_bill_btn.setFixedSize(32, 32)
        self.close_bill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_bill_btn.setToolTip("Close Current Bill")
        self.close_bill_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #CF6679;
                border: 2px solid #CF6679;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #CF6679;
                color: #0A0A0A;
            }
        """)
        self.close_bill_btn.clicked.connect(self.request_close_bill)
        tabs_header.addWidget(self.close_bill_btn)
        
        layout.addLayout(tabs_header)
        
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["Item", "Price", "Qty", "Total", "Action"])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.cart_table.setColumnWidth(2, 80) # Qty column Wider for SpinBox
        self.cart_table.setColumnWidth(4, 70) # Action column
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # self.cart_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Removed to allow SpinBox interaction logic if needed (though CellWidget ignores this)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(38)  # Reduced height for more visible items
        self.cart_table.setAlternatingRowColors(True)
        
        # Context Menu
        self.cart_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cart_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.cart_table)
        
        # Totals section
        totals_frame = QFrame()
        totals_frame.setObjectName("totalsFrame")
        totals_layout = QVBoxLayout(totals_frame)
        totals_layout.setContentsMargins(20, 15, 20, 15)
        totals_layout.setSpacing(8)
        
        # Subtotal row
        sub_row = QHBoxLayout()
        sub_row.addWidget(QLabel("Subtotal"))
        self.subtotal_label = QLabel("Rs 0.00")
        self.subtotal_label.setProperty("subheading", True)
        self.subtotal_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        sub_row.addWidget(self.subtotal_label)
        totals_layout.addLayout(sub_row)
        
        # Tax row
        tax_row = QHBoxLayout()
        tax_row.addWidget(QLabel("Tax"))
        self.tax_label = QLabel("Rs 0.00")
        self.tax_label.setProperty("subheading", True)
        self.tax_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        tax_row.addWidget(self.tax_label)
        totals_layout.addLayout(tax_row)
        
        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        totals_layout.addWidget(divider)
        
        # Total row
        total_row = QHBoxLayout()
        total_title = QLabel("TOTAL")
        total_title.setObjectName("totalTitle")
        total_row.addWidget(total_title)
        self.total_label = QLabel("Rs 0.00")
        self.total_label.setObjectName("totalAmount")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_row.addWidget(self.total_label)
        totals_layout.addLayout(total_row)
        
        layout.addWidget(totals_frame)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E57373, stop:1 #CF6679);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 14px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF9A9A, stop:1 #E57373);
            }
        """)
        clear_btn.clicked.connect(self.clear_cart)
        btn_layout.addWidget(clear_btn)
        
        self.pay_btn = QPushButton("💳 Pay (F5)")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #00878D);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 14px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00CED8, stop:1 #00ADB5);
            }
        """)
        self.pay_btn.clicked.connect(self.process_payment)
        btn_layout.addWidget(self.pay_btn, 1)
        
        layout.addLayout(btn_layout)
        
        # Reprint button
        reprint_btn = QPushButton("🖨️ Reprint Last Receipt (F12)")
        reprint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reprint_btn.clicked.connect(self.reprint_last)
        layout.addWidget(reprint_btn)
        
        return panel
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        search_shortcut = QShortcut(QKeySequence("F1"), self)
        search_shortcut.activated.connect(self.focus_search)
        
        # New bill shortcut
        new_bill_shortcut = QShortcut(QKeySequence("F2"), self)
        new_bill_shortcut.activated.connect(self.create_new_bill)
        
        # Switch bills with F3 (prev) and F4 (next)
        prev_bill_shortcut = QShortcut(QKeySequence("F3"), self)
        prev_bill_shortcut.activated.connect(self.switch_to_prev_bill)
        
        next_bill_shortcut = QShortcut(QKeySequence("F4"), self)
        next_bill_shortcut.activated.connect(self.switch_to_next_bill)
        
        pay_shortcut = QShortcut(QKeySequence("F5"), self)
        pay_shortcut.activated.connect(self.process_payment)
        
        print_shortcut = QShortcut(QKeySequence("F12"), self)
        print_shortcut.activated.connect(self.reprint_last)
        
        # Number keys 1-9 to quickly add filtered items (only when search not focused)
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(str(i)), self)
            shortcut.activated.connect(lambda idx=i-1: self.add_item_by_index(idx))
    
    def add_item_by_index(self, index):
        """Add item by its position in the current filtered list."""
        # Get visible items
        search_text = self.search_input.text().lower()
        category = self.category_filter.currentText()
        
        filtered = []
        for item in self.menu_items:
            if search_text and search_text not in item["name"].lower():
                continue
            if category != "All Categories" and item["category"] != category:
                continue
            filtered.append(item)
        
        if 0 <= index < len(filtered):
            self.add_to_cart(filtered[index])
    
    def load_menu(self):
        """Load menu items from database."""
        self.menu_items = db.get_all_menu_items()
        
        # Cache menu items by id for fast lookup
        self._menu_items_cache = {item["id"]: item for item in self.menu_items}
        
        # Cache default tax rate
        try:
            settings = db.get_all_settings()
            self._default_tax_rate = float(settings.get("tax_rate", 0))
        except Exception:
            self._default_tax_rate = 0
        
        # Update category filter
        categories = sorted(set(item["category"] for item in self.menu_items))
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(categories)
        
        self.display_items(self.menu_items)
    
    def display_items(self, items):
        """Display menu items in grid."""
        # Clear existing items
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not items:
            empty_label = QLabel("No items found.\nAdd items from Admin → Menu Manager")
            empty_label.setProperty("subheading", True)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_layout.addWidget(empty_label, 0, 0, 1, 3)
            return
        
        # Add items - use 3 columns for good sizing
        col_count = 3
        for i, item in enumerate(items):
            row = i // col_count
            col = i % col_count
            
            btn = QPushButton()
            btn.setMinimumSize(200, 100)
            btn.setMaximumHeight(120)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("menuItemBtn")
            # Format: Name on top, Price below
            btn.setText(f"{item['name']}\n\nRs {item['price']:,.0f}")
            btn.clicked.connect(lambda checked, i=item: self.add_to_cart(i))
            
            self.items_layout.addWidget(btn, row, col)
        
        # Add stretch at the end
        self.items_layout.setRowStretch(len(items) // col_count + 1, 1)
    
    def filter_items(self):
        """Filter menu items based on search and category."""
        search_text = self.search_input.text().lower()
        category = self.category_filter.currentText()
        
        filtered = []
        for item in self.menu_items:
            if search_text and search_text not in item["name"].lower():
                continue
            if category != "All Categories" and item["category"] != category:
                continue
            filtered.append(item)
        
        self.display_items(filtered)
    
    # ==================== Multi-Bill Methods ====================
    
    def _create_bill_tab(self, bill_id: int):
        """Create a tab button for a bill."""
        btn = QPushButton(f"#{bill_id}")
        btn.setFixedHeight(32)
        btn.setMinimumWidth(45)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.switch_to_bill(bill_id))
        self.bill_tab_buttons[bill_id] = btn
        self.bill_tabs_layout.addWidget(btn)
        self._update_bill_tabs_style()
    
    def _update_bill_tabs_style(self):
        """Update styling of all bill tabs."""
        for bill_id, btn in self.bill_tab_buttons.items():
            cart_count = len(self.bills.get(bill_id, []))
            item_text = f"#{bill_id}" if cart_count == 0 else f"#{bill_id} ({cart_count})"
            btn.setText(item_text)
            
            # Apply inline styles based on active state
            if bill_id == self.current_bill_id:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00ADB5;
                        color: #0A0A0A;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 10px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1E1E1E;
                        color: #888888;
                        border: 1px solid #333333;
                        border-radius: 6px;
                        padding: 6px 10px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #252525;
                        color: #EEEEEE;
                        border-color: #00ADB5;
                    }
                """)
    
    def create_new_bill(self):
        """Create a new bill tab."""
        if len(self.bills) >= self.MAX_BILLS:
            QMessageBox.warning(self, "Limit Reached", f"Maximum {self.MAX_BILLS} bills allowed.\nComplete or clear a bill to create a new one.")
            return
        
        # Find next available bill ID
        new_id = 1
        while new_id in self.bills:
            new_id += 1
        
        self.bills[new_id] = []
        self._create_bill_tab(new_id)
        self.switch_to_bill(new_id)
    
    def switch_to_bill(self, bill_id: int):
        """Switch to a specific bill."""
        if bill_id not in self.bills:
            return
        
        self.current_bill_id = bill_id
        self._update_bill_tabs_style()
        self.update_cart_display()
        self.cart_header_label.setText(f"🛒 Bill #{bill_id}")
    
    def switch_to_prev_bill(self):
        """Switch to previous bill (F3)."""
        bill_ids = sorted(self.bills.keys())
        if len(bill_ids) <= 1:
            return
        
        current_idx = bill_ids.index(self.current_bill_id)
        prev_idx = (current_idx - 1) % len(bill_ids)
        self.switch_to_bill(bill_ids[prev_idx])
    
    def switch_to_next_bill(self):
        """Switch to next bill (F4)."""
        bill_ids = sorted(self.bills.keys())
        if len(bill_ids) <= 1:
            return
        
        current_idx = bill_ids.index(self.current_bill_id)
        next_idx = (current_idx + 1) % len(bill_ids)
        self.switch_to_bill(bill_ids[next_idx])
    
    def request_close_bill(self):
        """Request to close the current bill."""
        if self.cart:
            reply = QMessageBox.question(self, "Close Bill", 
                                        f"Bill #{self.current_bill_id} has items.\nAre you sure you want to close/delete this bill?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.close_current_bill()
        self.update_cart_display()
    
    def close_current_bill(self):
        """Close current bill after payment or when cleared."""
        if len(self.bills) <= 1:
            # Keep at least one bill, just clear it
            self.bills[self.current_bill_id] = []
            self._update_bill_tabs_style()
            self.update_cart_display()  # Ensure UI updates for the last bill
            return
        
        # Remove current bill
        bill_id = self.current_bill_id
        del self.bills[bill_id]
        
        # Remove tab button
        if bill_id in self.bill_tab_buttons:
            btn = self.bill_tab_buttons.pop(bill_id)
            self.bill_tabs_layout.removeWidget(btn)
            btn.deleteLater()
        
        # Switch to first available bill
        remaining_ids = sorted(self.bills.keys())
        self.switch_to_bill(remaining_ids[0])
    
    def add_to_cart(self, item):
        """Add an item to the cart."""
        # Check if item already in cart (fast path)
        for i, cart_item in enumerate(self.cart):
            if cart_item.product_id == item["id"]:
                cart_item.qty += 1
                self.update_cart_display()
                self.cart_table.scrollToItem(self.cart_table.item(i, 0))
                return
        
        # Get tax rate - use item's tax rate, or cached default if 0
        item_tax = item.get("tax_rate", 0)
        if item_tax == 0:
            item_tax = getattr(self, '_default_tax_rate', 0)
        
        cart_item = CartItem(
            product_id=item["id"],
            name=item["name"],
            price=item["price"],
            qty=1,
            tax_rate=item_tax
        )
        self.cart.append(cart_item)
        self.update_cart_display()
        self.cart_table.scrollToBottom()
    
    def update_cart_display(self):
        """Update the cart table and totals."""
        self.cart_table.setRowCount(len(self.cart))
        
        subtotal = 0
        tax = 0
        
        for row, item in enumerate(self.cart):
            # Item name
            name_item = QTableWidgetItem(item.name)
            name_item.setForeground(QColor("#EEEEEE"))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.cart_table.setItem(row, 0, name_item)
            
            # Price
            price_item = QTableWidgetItem(f"Rs {item.price:,.2f}")
            price_item.setForeground(QColor("#AAAAAA"))
            price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.cart_table.setItem(row, 1, price_item)
            
            # Quantity (SpinBox)
            qty_spin = QSpinBox()
            qty_spin.setRange(1, 999)
            qty_spin.setValue(item.qty)
            qty_spin.setObjectName("qtySpin")
            qty_spin.valueChanged.connect(lambda val, r=row: self.update_item_qty(r, val))
            # Block scroll event to prevent accidental changes
            qty_spin.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.cart_table.setCellWidget(row, 2, qty_spin)
            
            # Total
            total_item = QTableWidgetItem(f"Rs {item.subtotal:,.2f}")
            total_item.setForeground(QColor("#EEEEEE"))
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.cart_table.setItem(row, 3, total_item)
            
            # Remove button
            remove_btn = QPushButton("🗑️")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setToolTip("Remove Item")
            remove_btn.setObjectName("removeBtn")
            remove_btn.clicked.connect(lambda checked, r=row: self.remove_from_cart(r))
            self.cart_table.setCellWidget(row, 4, remove_btn)
            
        # Calculate Totals
        subtotal = sum(item.subtotal for item in self.cart)
        
        # Global Tax Calculation
        try:
            tax_rate = float(db.get_setting("tax_rate", 0))
        except:
            tax_rate = 0.0
            
        tax = subtotal * (tax_rate / 100)
        total = subtotal + tax
        
        self.subtotal_label.setText(f"Rs {subtotal:,.2f}")
        self.tax_label.setText(f"Rs {tax:,.2f} ({tax_rate}%)")
        self.total_label.setText(f"Rs {total:,.2f}")
        
        # Update bill tabs to show item counts
        self._update_bill_tabs_style()
    
    def update_item_qty(self, row, new_qty):
        """Update quantity of item in cart."""
        if 0 <= row < len(self.cart):
            self.cart[row].qty = new_qty
            
            # Update Total cell immediately without full redraw to keep focus
            # But full redraw is safer to ensure totals match. 
            # To avoid losing focus on spinbox, we can just update the labels and the total cell.
            item = self.cart[row]
            
            # Update Total Cell
            total_item = self.cart_table.item(row, 3)
            if total_item:
                total_item.setText(f"Rs {item.subtotal:,.2f}")
            
            # Recalculate Totals
            subtotal = sum(i.subtotal for i in self.cart)
            tax = sum(i.tax for i in self.cart)
            total = subtotal + tax
            
            self.subtotal_label.setText(f"Rs {subtotal:,.2f}")
            self.tax_label.setText(f"Rs {tax:,.2f}")
            self.total_label.setText(f"Rs {total:,.2f}")
    
    def show_context_menu(self, pos):
        """Show context menu for cart table."""
        menu = QMenu(self)
        remove_action = menu.addAction("🗑️ Remove Item")
        action = menu.exec(self.cart_table.mapToGlobal(pos))
        
        if action == remove_action:
            row = self.cart_table.currentRow()
            if row >= 0:
                self.remove_from_cart(row)

    def remove_from_cart(self, row):
        """Remove item from cart."""
        if 0 <= row < len(self.cart):
            del self.cart[row]
            self.update_cart_display()
    
    def clear_cart(self):
        """Clear the cart."""
        if self.cart:
            reply = QMessageBox.question(self, "Clear Cart", "Clear all items from this bill?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Just empty the list, don't close the bill tab
                self.bills[self.current_bill_id] = []
                self.update_cart_display()
                self._update_bill_tabs_style()
    
    def process_payment(self):
        """Process payment for current cart."""
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart")
            return
        
        subtotal = sum(item.subtotal for item in self.cart)
        
        # Global Tax Calculation
        try:
            tax_rate = float(db.get_setting("tax_rate", 0))
        except:
            tax_rate = 0.0
            
        tax = subtotal * (tax_rate / 100)
        total = subtotal + tax
        
        dialog = PaymentDialog(total, self)
        if dialog.exec():
            data = dialog.get_data()
            final_total = total - data["discount"]
            
            items = [
                {
                    "product_id": item.product_id,
                    "product_name": item.name,
                    "qty": item.qty,
                    "price": item.price
                }
                for item in self.cart
            ]
            
            sale_id = db.create_sale(
                subtotal=subtotal,
                tax=tax,
                discount=data["discount"],
                total=final_total,
                payment_type=data["payment_type"],
                user_id=auth.current_user.get("id", 1),
                items=items
            )
            
            if sale_id:
                sale_data = db.get_sale(sale_id)
                settings = db.get_all_settings()
                
                # Ask if user wants to print
                reply = QMessageBox.question(
                    self, "✓ Payment Complete",
                    f"Sale completed!\nReceipt: {sale_data.get('receipt_no', 'N/A')}\n\nPrint receipt?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    printer.print_receipt(sale_data, settings)
                
                # Close/reset the current bill after successful payment if auto-clear is checked
                if data.get("auto_clear", True):
                    self.close_current_bill()
            else:
                QMessageBox.warning(self, "Error", "Failed to save sale")
    
    def reprint_last(self):
        """Reprint the last receipt using Windows print."""
        sale = db.get_last_sale()
        if sale:
            settings = db.get_all_settings()
            
            reply = QMessageBox.question(
                self, f"Receipt: {sale.get('receipt_no', 'N/A')}",
                "Print this receipt?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = printer.print_receipt(sale, settings)
                if not success:
                    QMessageBox.warning(self, "Print Error", msg)
        else:
            QMessageBox.information(self, "No Sales", "No previous sales found")
    
    def focus_search(self):
        """Focus the search input."""
        self.content_stack.setCurrentIndex(0)
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def switch_page(self, index):
        """Switch between billing and admin pages."""
        if index == 1 and not auth.is_admin:
            QMessageBox.warning(self, "Access Denied", "Admin access required")
            return
        
        self.content_stack.setCurrentIndex(index)
        
        # Update button styles
        self.billing_btn.setStyleSheet(self._get_nav_btn_style(index == 0))
        self.admin_btn.setStyleSheet(self._get_nav_btn_style(index == 1))
        
        if index == 0:
            self.load_menu()
        elif index == 1:
            self.admin_panel.load_data()
    
    def set_user(self, user):
        """Set the current user and update display."""
        if user:
            self.user_label.setText(f"👤 {user.get('username', 'User')} ({user.get('role', 'Staff')})")
            self.admin_btn.setVisible(auth.is_admin)
    
    def logout(self):
        """Log out the current user."""
        auth.logout()
        self.cart.clear()
        self.update_cart_display()
        self.content_stack.setCurrentIndex(0)
        self.logout_requested.emit()
