"""
Remove the helper method and fix the bill tab call
"""

# Read main_window.py
with open("ui/main_window.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the helper method
helper_to_remove = '''    def _apply_btn_property(self, btn, prop_name, prop_value):
        """Helper to apply button property and force style refresh."""
        btn.setProperty(prop_name, prop_value)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
    '''

content = content.replace(helper_to_remove, '')

# Fix the bill tab call - replace with objectName approach
old_bill_call = '''            # Use properties instead of inline styles
            self._apply_btn_property(btn, "billTabActive", bill_id == self.current_bill_id)'''

new_bill_call = '''            # Set property for active/inactive styling
            btn.setProperty("billTabActive", bill_id == self.current_bill_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)'''

content = content.replace(old_bill_call, new_bill_call)

# Write back
with open("ui/main_window.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Removed helper method and fixed bill tab styling!")
