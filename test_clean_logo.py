"""
Quick test to show receipt with new clean text logo
"""
from printer import printer
from datetime import datetime

# Sample receipt
test_receipt = {
    'receipt_no': 'RCP-0012423',
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'cashier': 'Admin User',
    'items': [
        {'product_name': 'Chicken Burger Deluxe', 'qty': 2, 'price_at_sale': 450.00},
        {'product_name': 'French Fries Large', 'qty': 1, 'price_at_sale': 250.00},
        {'product_name': 'Coca Cola 500ml', 'qty': 2, 'price_at_sale': 150.00}
    ],
    'subtotal': 1450.00,
    'tax': 145.00,
    'discount': 50.00,
    'total': 1545.00,
    'payment_type': 'Cash'
}

settings = {
    'restaurant_name': 'Food Garden',
    'restaurant_address': '123 Main Street, Karachi',
    'restaurant_phone': '+92 300 1234567',
    'currency_symbol': 'Rs',
    'receipt_footer': 'Thank you for visiting! Please come again.'
}

print(printer.format_receipt_text(test_receipt, settings))
