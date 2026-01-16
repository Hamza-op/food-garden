"""Show clean receipt preview"""
from printer import printer
from datetime import datetime

test = {
    'receipt_no': 'RCP-12423',
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'cashier': 'Admin',
    'items': [
        {'product_name': 'Burger', 'qty': 2, 'price_at_sale': 450},
        {'product_name': 'Fries', 'qty': 1, 'price_at_sale': 250}
    ],
    'subtotal': 1150,
    'tax': 115,
    'discount': 0,
    'total': 1265,
    'payment_type': 'Cash'}

settings = {
    'restaurant_name': 'Food Garden',
    'restaurant_address': '123 Main St, Karachi',
    'restaurant_phone': '+92 300 1234567',
    'currency_symbol': 'Rs',
    'receipt_footer': 'Thank you!'}

receipt = printer.format_receipt_text(test, settings)

# Write to file
with open('receipt_output.txt', 'w', encoding='utf-8') as f:
    f.write(receipt)

print("Receipt saved to receipt_output.txt")
print("\n" + "="*42)
print(receipt)
print("="*42)
