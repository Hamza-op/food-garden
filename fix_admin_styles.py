"""
Quick script to remove all hardcoded style assignments from admin_panel.py
"""
import re

# Read the file
with open("ui/admin_panel.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove all setStyleSheet calls with the old style constants
replacements = [
    (r'\.setStyleSheet\(INPUT_STYLE\)', ''),
    (r'\.setStyleSheet\(TABLE_STYLE\)', ''),
    (r'\.setStyleSheet\(CARD_STYLE\)', ''),
    (r'\.setStyleSheet\(GROUP_STYLE\)', ''),
    (r'\.setStyleSheet\(BTN_PRIMARY\)', '.setProperty("primary", True)'),
    (r'\.setStyleSheet\(BTN_DANGER\)', '.setProperty("danger", True)'),
    (r'\.setStyleSheet\(BTN_SECONDARY\)', ''),
    (r'\.setStyleSheet\("background-color: #141414;"\)', ''),
    (r'\.setStyleSheet\("background-color: #0A0A0A;"\)', ''),
    (r'\.setStyleSheet\("background: transparent;"\)', ''),
    (r'\.setStyleSheet\("border: none;"\)', ''),
    (r'\.setStyleSheet\("color: #888888; font-size: 13px;"\)', '.setProperty("subheading", True)'),
    (r'\.setStyleSheet\("color: #AAAAAA; font-size: 13px;"\)', '.setProperty("subheading", True)'),
    (r'\.setStyleSheet\("font-size: 20px; font-weight: bold; color: #00ADB5;"\)', '.setProperty("heading", True)'),
    (r'\.setStyleSheet\("font-size: 16px; font-weight: bold; color: #EEEEEE;"\)', '.setObjectName("sectionTitle")'),
    (r'\.setStyleSheet\("color: #00ADB5; font-size: 28px; font-weight: bold;"\)', '.setObjectName("statValue")'),
    (r'\.setStyleSheet\("color: #888888; font-size: 13px;"\)', '.setProperty("subheading", True)'),
]

# Apply all replacements
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Remove the old tab styling that's hardcoded
old_tab_style = r'        self\.tabs\.setStyleSheet\("""[^"]*?"""\)'
content = re.sub(old_tab_style, '', content, flags=re.DOTALL)

# Write back
with open("ui/admin_panel.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Admin panel styles fixed!")
