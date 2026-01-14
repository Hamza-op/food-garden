"""
Complete cleanup script to remove ALL remaining hardcoded dark mode styles
from main_window.py and improve theme management
"""
import re

# Read the file
with open("ui/main_window.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix reprint button - remove inline styles
content = re.sub(
    r'(reprint_btn = QPushButton\("🖨️ Reprint Last Receipt \(F12\)"\)\s+reprint_btn\.setCursor\(Qt\.CursorShape\.PointingHandCursor\))\s+reprint_btn\.setStyleSheet\("""[^"]+"""\)',
    r'\1',
    content,
    flags=re.DOTALL
)

# 2. Fix menu item buttons - remove inline styles and add object name
old_menu_btn = r'''btn = QPushButton\(\)
            btn\.setMinimumSize\(200, 100\)
            btn\.setMaximumHeight\(120\)
            btn\.setCursor\(Qt\.CursorShape\.PointingHandCursor\)
            btn\.setStyleSheet\("""[^"]+"""\)'''

new_menu_btn = '''btn = QPushButton()
            btn.setMinimumSize(200, 100)
            btn.setMaximumHeight(120)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("menuItemBtn")'''

content = re.sub(old_menu_btn, new_menu_btn, content, flags=re.DOTALL)

# 3. Fix bill tab buttons - remove inline styles
# Replace the _update_bill_tabs_style method entirely
old_method = r'def _update_bill_tabs_style\(self\):.*?(?=\n    def |\n\r\n    def |\Z)'

new_method = '''def _update_bill_tabs_style(self):
        """Update styling of all bill tabs."""
        for bill_id, btn in self.bill_tab_buttons.items():
            cart_count = len(self.bills.get(bill_id, []))
            item_text = f"#{bill_id}" if cart_count == 0 else f"#{bill_id} ({cart_count})"
            btn.setText(item_text)
            
            # Use properties instead of inline styles
            btn.setProperty("billTabActive", bill_id == self.current_bill_id)
            btn.setStyle(btn.style())  # Force style refresh
    '''

content = re.sub(old_method, new_method, content, flags=re.DOTALL)

# 4. Fix empty label inline style
content = re.sub(
    r'empty_label\.setStyleSheet\("color: #555555; font-size: 14px;"\)',
    'empty_label.setProperty("subheading", True)',
    content
)

# 5. Remove theme button inline styles if they exist
content = re.sub(
    r'(self\.theme_btn = QPushButton.*?)\s+self\.theme_btn\.setStyleSheet\("""[^"]+"""\)',
    r'\1',
    content,
    flags=re.DOTALL
)

# 6. Fix new bill and close bill buttons
content = re.sub(
    r'(self\.new_bill_btn = QPushButton.*?)\s+self\.new_bill_btn\.setStyleSheet\("""[^"]+"""\)',
    r'\1\n        self.new_bill_btn.setObjectName("newBillBtn")',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'(self\.close_bill_btn = QPushButton.*?)\s+self\.close_bill_btn\.setStyleSheet\("""[^"]+"""\)',
    r'\1\n        self.close_bill_btn.setObjectName("closeBillBtn")',
    content,
    flags=re.DOTALL
)

# Write back
with open("ui/main_window.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ All hardcoded styles removed from main_window.py!")
print("🧹 Codebase cleaned!")
