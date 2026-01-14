"""
Fix button styling by using objectNames instead of properties
This is more reliable in Qt
"""

# Read main_window.py
with open("ui/main_window.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace property-based approach with objectName approach for action buttons
old_clear = '''clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setProperty("danger", True)
        clear_btn.style().unpolish(clear_btn)
        clear_btn.style().polish(clear_btn)
        clear_btn.clicked.connect(self.clear_cart)'''

new_clear = '''clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setObjectName("clearBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_cart)'''

content = content.replace(old_clear, new_clear)

old_pay = '''self.pay_btn = QPushButton("💳 Pay (F5)")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setProperty("primary", True)
        self.pay_btn.style().unpolish(self.pay_btn)
        self.pay_btn.style().polish(self.pay_btn)
        self.pay_btn.clicked.connect(self.process_payment)'''

new_pay = '''self.pay_btn = QPushButton("💳 Pay (F5)")
        self.pay_btn.setObjectName("payBtn")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.clicked.connect(self.process_payment)'''

content = content.replace(old_pay, new_pay)

# Write back
with open("ui/main_window.py", "w", encoding="utf-8") as f:
    f.write(content)

# Now update stylesheets with objectName-based selectors
# Dark mode
dark_btn_styles = """
/* Action Buttons using ObjectName */
QPushButton#clearBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E57373, stop:1 #CF6679);
    color: #0D0D0D;
    border: none;
    border-radius: 10px;
    padding: 14px 20px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#clearBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF9A9A, stop:1 #E57373);
}

QPushButton#payBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #00878D);
    color: #0D0D0D;
    border: none;
    border-radius: 10px;
    padding: 14px 30px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#payBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00CED8, stop:1 #00ADB5);
}
"""

# Light mode
light_btn_styles = """
/* Action Buttons using ObjectName */
QPushButton#clearBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E57373, stop:1 #D32F2F);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 14px 20px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#clearBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF9A9A, stop:1 #E57373);
}

QPushButton#payBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #008C94);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 14px 30px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#payBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00CED8, stop:1 #00ADB5);
}
"""

# Add to dark stylesheet
with open("ui/styles.qss", "r", encoding="utf-8") as f:
    dark_content = f.read()

if "#clearBtn" not in dark_content:
    dark_content += "\n" + dark_btn_styles

with open("ui/styles.qss", "w", encoding="utf-8") as f:
    f.write(dark_content)

# Add to light stylesheet
with open("ui/styles_light.qss", "r", encoding="utf-8") as f:
    light_content = f.read()

if "#clearBtn" not in light_content:
    light_content += "\n" + light_btn_styles

with open("ui/styles_light.qss", "w", encoding="utf-8") as f:
    f.write(light_content)

print("✅ Switched to objectName-based button styling!")
print("🎨 This is more reliable than property-based selectors!")
