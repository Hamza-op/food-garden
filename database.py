"""
AuraPOS Professional - Database Manager (SQLite)
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DB_PATH, DEFAULT_SETTINGS


class DatabaseManager:
    """Handles all SQLite database operations with robust error handling."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
    
    def connect(self) -> sqlite3.Connection:
        """Establish database connection with WAL mode for performance."""
        try:
            # Close existing connection first
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None
            
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            return self._connection
        except sqlite3.Error as e:
            raise RuntimeError(f"Database connection failed: {e}")
    
    def close(self):
        """Close database connection safely."""
        if self._connection:
            try:
                self._connection.commit()  # Commit any pending changes
                self._connection.close()
            except Exception as e:
                print(f"Warning closing connection: {e}")
            self._connection = None
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self.connect()
        return self._connection
    
    def initialize_database(self):
        """Create all required tables if they don't exist."""
        try:
            cursor = self.connection.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Admin', 'Staff')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Menu table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS menu (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'General',
                    price REAL NOT NULL DEFAULT 0,
                    tax_rate REAL DEFAULT 0,
                    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive'))
                )
            """)
            
            # Sales table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_no TEXT UNIQUE NOT NULL,
                    subtotal REAL NOT NULL,
                    tax REAL NOT NULL,
                    discount REAL DEFAULT 0,
                    total REAL NOT NULL,
                    payment_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Sale Items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    price_at_sale REAL NOT NULL,
                    FOREIGN KEY (sale_id) REFERENCES sales(id),
                    FOREIGN KEY (product_id) REFERENCES menu(id)
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            self.connection.commit()
            self._initialize_default_settings()
            self._create_default_admin()
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Database initialization failed: {e}")
    
    def _initialize_default_settings(self):
        """Insert default settings if not present."""
        try:
            cursor = self.connection.cursor()
            for key, value in DEFAULT_SETTINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, str(value))
                )
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Warning: Failed to initialize settings: {e}")
    
    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                import bcrypt
                password_hash = bcrypt.hashpw("adminfood".encode(), bcrypt.gensalt()).decode()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ("admin", password_hash, "Admin")
                )
                self.connection.commit()
                print("Default admin user created (admin/admin123)")
        except sqlite3.Error as e:
            print(f"Warning: Failed to create default admin: {e}")
    
    # ==================== User Operations ====================
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error getting user: {e}")
            return None
    
    def add_user(self, username: str, password_hash: str, role: str) -> bool:
        """Add a new user."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT id, username, role, created_at FROM users")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting users: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False
    
    # ==================== Menu Operations ====================
    
    def get_all_menu_items(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all menu items."""
        try:
            cursor = self.connection.cursor()
            if active_only:
                cursor.execute("SELECT * FROM menu WHERE status = 'active' ORDER BY category, name")
            else:
                cursor.execute("SELECT * FROM menu ORDER BY category, name")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting menu items: {e}")
            return []
    
    def add_menu_item(self, name: str, category: str, price: float, tax_rate: float = 0) -> bool:
        """Add a new menu item."""
        try:
            if not name or not name.strip():
                print("Error: Item name cannot be empty")
                return False
            
            if not category or not category.strip():
                category = "General"
            
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO menu (name, category, price, tax_rate, status) VALUES (?, ?, ?, ?, 'active')",
                (name.strip(), category.strip(), float(price), float(tax_rate))
            )
            self.connection.commit()
            print(f"Menu item '{name}' added successfully")
            return True
        except sqlite3.Error as e:
            print(f"Error adding menu item: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error adding menu item: {e}")
            return False
    
    def update_menu_item(self, item_id: int, name: str, category: str, price: float, tax_rate: float, status: str) -> bool:
        """Update an existing menu item."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE menu SET name=?, category=?, price=?, tax_rate=?, status=? WHERE id=?",
                (name, category, price, tax_rate, status, item_id)
            )
            self.connection.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating menu item: {e}")
            return False
    
    def check_item_usage(self, item_id: int) -> int:
        """Check how many times a menu item has been used in sales."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM sale_items WHERE product_id = ?", (item_id,))
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error checking item usage: {e}")
            return 0

    def permanently_delete_menu_item(self, item_id: int) -> bool:
        """Permanently delete a menu item and its sales history."""
        try:
            cursor = self.connection.cursor()
            # First delete from sale_items to satisfy foreign key constraint
            cursor.execute("DELETE FROM sale_items WHERE product_id = ?", (item_id,))
            # Then delete from menu
            cursor.execute("DELETE FROM menu WHERE id = ?", (item_id,))
            self.connection.commit()
            print(f"Item {item_id} and its history permanently deleted.")
            return True
        except sqlite3.Error as e:
            print(f"Error permanently deleting menu item: {e}")
            return False

    def delete_menu_item(self, item_id: int) -> bool:
        """Soft delete a menu item (mark inactive)."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE menu SET status = 'inactive' WHERE id = ?", (item_id,))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting menu item: {e}")
            return False
    
    def search_menu(self, query: str) -> List[Dict[str, Any]]:
        """Search menu items by name."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM menu WHERE status = 'active' AND name LIKE ? ORDER BY name",
                (f"%{query}%",)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching menu: {e}")
            return []
    
    # ==================== Sales Operations ====================
    
    def generate_receipt_no(self) -> str:
        """Generate a unique receipt number."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM sales")
            count = cursor.fetchone()[0]
            date_str = datetime.now().strftime("%Y%m%d")
            return f"RCP-{date_str}-{count + 1:04d}"
        except sqlite3.Error:
            return f"RCP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def create_sale(self, subtotal: float, tax: float, discount: float, total: float,
                    payment_type: str, user_id: int, items: List[Dict]) -> Optional[int]:
        """Create a new sale with items."""
        try:
            cursor = self.connection.cursor()
            receipt_no = self.generate_receipt_no()
            
            cursor.execute(
                """INSERT INTO sales (receipt_no, subtotal, tax, discount, total, payment_type, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (receipt_no, subtotal, tax, discount, total, payment_type, user_id)
            )
            sale_id = cursor.lastrowid
            
            for item in items:
                cursor.execute(
                    """INSERT INTO sale_items (sale_id, product_id, product_name, qty, price_at_sale)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sale_id, item["product_id"], item["product_name"], item["qty"], item["price"])
                )
            
            self.connection.commit()
            return sale_id
        except sqlite3.Error as e:
            print(f"Error creating sale: {e}")
            try:
                self.connection.rollback()
            except Exception:
                pass
            return None
    
    def get_sale(self, sale_id: int) -> Optional[Dict[str, Any]]:
        """Get sale by ID with items and cashier name."""
        try:
            cursor = self.connection.cursor()
            # Fetch sale with username
            query = """
                SELECT s.*, u.username as cashier_name 
                FROM sales s 
                LEFT JOIN users u ON s.user_id = u.id 
                WHERE s.id = ?
            """
            cursor.execute(query, (sale_id,))
            sale = cursor.fetchone()
            if not sale:
                return None
            
            sale_dict = dict(sale)
            # Map cashier_name to cashier key for consistency
            sale_dict['cashier'] = sale_dict.get('cashier_name', 'Unknown')
            
            cursor.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,))
            sale_dict["items"] = [dict(row) for row in cursor.fetchall()]
            return sale_dict
        except sqlite3.Error as e:
            print(f"Error getting sale: {e}")
            return None
    
    def get_last_sale(self) -> Optional[Dict[str, Any]]:
        """Get the most recent sale."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT id FROM sales ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return self.get_sale(row[0])
            return None
        except sqlite3.Error as e:
            print(f"Error getting last sale: {e}")
            return None
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily sales summary."""
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            cursor = self.connection.cursor()
            
            # Total sales
            cursor.execute(
                """SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total,
                          COALESCE(SUM(tax), 0) as tax, COALESCE(SUM(discount), 0) as discount
                   FROM sales WHERE DATE(timestamp, 'localtime') = ?""",
                (date,)
            )
            summary = dict(cursor.fetchone())
            
            # By payment type
            cursor.execute(
                """SELECT payment_type, COUNT(*) as count, SUM(total) as total
                   FROM sales WHERE DATE(timestamp, 'localtime') = ? GROUP BY payment_type""",
                (date,)
            )
            summary["by_payment"] = [dict(row) for row in cursor.fetchall()]
            
            # Top items
            cursor.execute(
                """SELECT si.product_name, SUM(si.qty) as total_qty
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.id
                   WHERE DATE(s.timestamp, 'localtime') = ?
                   GROUP BY si.product_name
                   ORDER BY total_qty DESC LIMIT 10""",
                (date,)
            )
            summary["top_items"] = [dict(row) for row in cursor.fetchall()]
            
            return summary
        except sqlite3.Error as e:
            print(f"Error getting daily summary: {e}")
            return {"count": 0, "total": 0, "tax": 0, "discount": 0, "by_payment": [], "top_items": []}
    
    # ==================== Settings Operations ====================
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error:
            return None
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting value: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error:
            return {}


# Global database instance
db = DatabaseManager()
