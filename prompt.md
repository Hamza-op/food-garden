# **PROJECT SPECIFICATION: AuraPOS Professional**

**Objective:** Build a high-performance, production-ready, 100% offline Windows Desktop Billing Application.
**Developer Role:** Senior Software Architect & UI/UX Designer.
**Target Environment:** Windows 10/11 (Single PC, No Internet).

## **1. THE TECH STACK (STABILITY & SPEED)**

* **Language:** Python 3.12+
* **GUI Framework:** PyQt6 (for professional, hardware-accelerated Windows UI).
* **Database:** SQLite (Local file-based storage, high ACID compliance).
* **Printing:** `python-escpos` for direct thermal printer communication.
* **Compilation:** `Nuitka` or `PyInstaller` (to produce a standalone .exe).

---

## **2. MODERN UI/UX GUIDELINES**

The interface must look like a premium 2026 SaaS application but run natively.

* **Design System:** Dark Mode by default. Primary: #00ADB5 (Teal), Background: #121212, Surface: #1E1E1E, Text: #EEEEEE.
* **Responsiveness:** Use `QGridLayout` and `stretch factors`. The UI must automatically adapt to any screen resolution (720p to 4K).
* **Workflow:** Search-First. The cursor should default to a "Global Search" bar. Typing "CH" should instantly filter "Chicken Burger," "Cheese Fries," etc.
* **Animations:** Use `QPropertyAnimation` for smooth tab transitions and button hovers.

---

## **3. DATABASE ARCHITECTURE**

Initialize a local SQLite database (`aura_pos.db`) with the following tables:

* `users`: (id, username, password_hash, role [Admin/Staff], created_at)
* `menu`: (id, name, category, price, tax_rate, status)
* `sales`: (id, receipt_no, total, tax, discount, payment_type, timestamp, user_id)
* `sale_items`: (id, sale_id, product_id, qty, price_at_sale)
* `settings`: (key, value) -- To store Restaurant Name, Address, Printer ID, and Tax Rules.

---

## **4. CORE FUNCTIONALITY**

### **A. Security & Users**

* Create a secure login system.
* **Admin:** Access to Sales Reports, Price Editing, and User Management.
* **Staff:** Access only to the "New Bill" screen and "Reprint Last Receipt."

### **B. The Billing Engine**

* **Keyboard Shortcuts:** F1 for Search, F5 for Pay, F12 for Print.
* **Real-time Totals:** Cart must update Subtotal, Tax, and Final Total instantly upon item addition.
* **Tax/Discounts:** Apply percentages defined in the Admin Panel.

### **C. Admin & Maintenance**

* **Menu Manager:** Simple table to Add/Edit/Delete 50+ items.
* **Reports:** A "Daily Summary" view showing total cash/card and most sold items.
* **Backup System:** A "Backup Data" button that exports the `.db` file to a `Backups` folder. A "Restore" button to import a previous `.db` file.

---

## **5. HARDWARE & PRINTING**

* Provide a dedicated `PrinterService` class.
* Receipts must include: Header (Center-aligned Name/Addr), Body (Item Name - Qty - Price), Footer (Tax Breakdown, Total in Bold, "Thank You" Message).
* Include a "Test Print" button in the settings to verify the USB/Thermal connection.

---

## **6. EXECUTION PLAN (DO THIS NOW)**

**Please provide the response in these specific phases:**

1. **Environment Setup:** List the exact `pip install` commands needed.
2. **File Structure:** Define a modular structure (e.g., `main.py`, `database.py`, `styles.qss`, `printer.py`).
3. **The Core Logic:** Write the **Database Initialization** script and the **Authentication Logic** first.
4. **The UI Layout:** Provide the code for the **Main Billing Dashboard** (Modern Responsive Layout) and the **Admin Management Panel**.
5. **EXE Compilation:** Provide the specific command to turn this into a single, icon-branded `.exe` using Nuitka.

**Constraint:** Do not use any external APIs. Every image, font, and data point must be local. Focus on code that is "Crash-Proof"—use `try/except` blocks for all database and printer operations.

---

### **How this prompt helps you:**

* **No Guesswork:** It explicitly tells Claude to use **PyQt6** and **SQLite**, which are the best for stability.
* **Visual Quality:** By defining specific hex colors and "2026 design" standards, you avoid the "ugly" default Windows look.
* **Self-Correcting:** It asks for a "Modular" structure, which means if there is a bug in the printer logic, it won't break the whole billing screen.
* **Complete Package:** It includes the "Compilation" instructions, so you don't have to ask "how do I make this an EXE?" later.
