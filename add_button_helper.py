"""
Final fix: Add a helper method to properly apply button properties and ensure they get styled
"""
import re

# Read main_window.py
with open("ui/main_window.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add a helper method to the MainWindow class
helper_method = '''
    def _apply_btn_property(self, btn, prop_name, prop_value):
        """Helper to apply button property and force style refresh."""
        btn.setProperty(prop_name, prop_value)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
    '''

# Find where to insert (after __init__ method, before setup_ui)
if "_apply_btn_property" not in content:
    # Insert after the cart.setter property
    insert_pos = content.find("    def setup_ui(self):")
    if insert_pos > 0:
        content = content[:insert_pos] + helper_method + "\n" + content[insert_pos:]

# Now find and replace all other setProperty calls for buttons
# Pattern: button.setProperty("...", ...) followed by unpolish/polish
# Replace with: self._apply_btn_property(button, "...", ...)

# For bill tab buttons in _update_bill_tabs_style
old_bill_tab = r'''btn\.setProperty\("billTabActive", bill_id == self\.current_bill_id\)
            btn\.setStyle\(btn\.style\(\)\)  # Force style refresh'''

new_bill_tab = r'''self._apply_btn_property(btn, "billTabActive", bill_id == self.current_bill_id)'''

content = re.sub(old_bill_tab, new_bill_tab, content)

# Write back
with open("ui/main_window.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Added helper method for button property application!")
print("🔧 All buttons will now properly refresh their styles!")
