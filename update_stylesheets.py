"""
Add all missing component styles to both theme stylesheets
"""

# Dark mode stylesheet additions
dark_additions = """
/* Menu Item Buttons */
QPushButton#menuItemBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252525, stop:1 #1A1A1A);
    border: 2px solid #333333;
    border-radius: 12px;
    padding: 15px;
    color: #EEEEEE;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#menuItemBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2D2D2D, stop:1 #222222);
    border-color: #00ADB5;
}

QPushButton#menuItemBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00ADB5, stop:1 #00878D);
    color: #0A0A0A;
    font-weight: bold;
}

/* Bill Tab Buttons */
QPushButton[billTabActive="true"] {
    background-color: #00ADB5;
    color: #0A0A0A;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton[billTabActive="false"] {
    background-color: #1E1E1E;
    color: #888888;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QPushButton[billTabActive="false"]:hover {
    background-color: #252525;
    color: #EEEEEE;
    border-color: #00ADB5;
}

/* New Bill Button */
QPushButton#newBillBtn {
    background-color: #1E1E1E;
    color: #00ADB5;
    border: 1px solid #333333;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton#newBillBtn:hover {
    background-color: #00ADB5;
    color: #0A0A0A;
}

/* Close Bill Button */
QPushButton#closeBillBtn {
    background-color: #1E1E1E;
    color: #CF6679;
    border: 1px solid #333333;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton#closeBillBtn:hover {
    background-color: #CF6679;
    color: #0A0A0A;
}
"""

# Light mode stylesheet additions
light_additions = """
/* Menu Item Buttons */
QPushButton#menuItemBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F5F5F5);
    border: 2px solid #DDDDDD;
    border-radius: 12px;
    padding: 15px;
    color: #333333;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#menuItemBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F5F5F5, stop:1 #EEEEEE);
    border-color: #00ADB5;
}

QPushButton#menuItemBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00ADB5, stop:1 #008C94);
    color: #FFFFFF;
    font-weight: bold;
}

/* Bill Tab Buttons */
QPushButton[billTabActive="true"] {
    background-color: #00ADB5;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton[billTabActive="false"] {
    background-color: #FFFFFF;
    color: #666666;
    border: 1px solid #CCCCCC;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QPushButton[billTabActive="false"]:hover {
    background-color: #EEEEEE;
    color: #333333;
    border-color: #00ADB5;
}

/* New Bill Button */
QPushButton#newBillBtn {
    background-color: #FFFFFF;
    color: #00ADB5;
    border: 1px solid #CCCCCC;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton#newBillBtn:hover {
    background-color: #00ADB5;
    color: #FFFFFF;
}

/* Close Bill Button */
QPushButton#closeBillBtn {
    background-color: #FFFFFF;
    color: #D32F2F;
    border: 1px solid #CCCCCC;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton#closeBillBtn:hover {
    background-color: #D32F2F;
    color: #FFFFFF;
}
"""

# Read and update dark mode stylesheet
with open("ui/styles.qss", "r", encoding="utf-8") as f:
    dark_content = f.read()

if "#menuItemBtn" not in dark_content:
    dark_content += dark_additions

with open("ui/styles.qss", "w", encoding="utf-8") as f:
    f.write(dark_content)

# Read and update light mode stylesheet
with open("ui/styles_light.qss", "r", encoding="utf-8") as f:
    light_content = f.read()

if "#menuItemBtn" not in light_content:
    light_content += light_additions

with open("ui/styles_light.qss", "w", encoding="utf-8") as f:
    f.write(light_content)

print("✅ Added all button styles to both theme stylesheets!")
print("🎨 Themes are now complete!")
