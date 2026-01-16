"""
Test script to preview receipt with logo
"""
from printer import printer
from datetime import datetime

# Sample receipt data
test_receipt = {
    'receipt_no': 'TEST-001',
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'cashier': 'Test User',
    'items': [
        {
            'product_name': 'Chicken Burger',
            'qty': 2,
            'price_at_sale': 450.00
        },
        {
            'product_name': 'French Fries (Large)',
            'qty': 1,
            'price_at_sale': 250.00
        },
        {
            'product_name': 'Coca Cola',
            'qty': 2,
            'price_at_sale': 150.00
        }
    ],
    'subtotal': 1450.00,
    'tax': 0.00,
    'discount': 0.00,
    'total': 1450.00,
    'payment_type': 'Cash'
}

# Receipt settings
settings = {
    'restaurant_name': 'Food Garden',
    'restaurant_address': '123 Main Street, City',
    'restaurant_phone': '+92 300 1234567',
    'currency_symbol': 'Rs',
    'receipt_footer': 'Thank you for dining with us!'
}

# Generate and display receipt
receipt_text = printer.format_receipt_text(test_receipt, settings)
print(receipt_text)
print("\n" + "="*50)
print("Receipt preview generated successfully!")
print("This is how your receipt will look when printed.")
print("="*50)
