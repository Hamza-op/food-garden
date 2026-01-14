"""
Script to add demo menu items for Food Garden.
"""
from database import db
import random

def add_demo_menu():
    print("🌱 Seeding Food Garden Menu...")
    
    # Clear existing items if desired? No, let's just append.
    # Actually, let's add them if they don't exist.
    
    demo_items = [
        # Starters
        {"name": "Crispy Spring Rolls", "category": "Starters", "price": 450.0, "tax": 5.0},
        {"name": "Loaded Nachos", "category": "Starters", "price": 850.0, "tax": 5.0},
        {"name": "Garlic Butter Shrimp", "category": "Starters", "price": 1200.0, "tax": 5.0},
        {"name": "Garden Fresh Soup", "category": "Starters", "price": 350.0, "tax": 5.0},
        
        # Main Course
        {"name": "Grilled Chicken Steak", "category": "Main Course", "price": 1500.0, "tax": 10.0},
        {"name": "Beef Smash Burger", "category": "Main Course", "price": 950.0, "tax": 10.0},
        {"name": "Creamy Pasta Alfredo", "category": "Main Course", "price": 1100.0, "tax": 10.0},
        {"name": "Margherita Pizza (L)", "category": "Main Course", "price": 1800.0, "tax": 10.0},
        {"name": "Veggie Delight Panini", "category": "Main Course", "price": 750.0, "tax": 5.0},

        # Fast Food
        {"name": "Club Sandwich", "category": "Fast Food", "price": 650.0, "tax": 5.0},
        {"name": "Zinger Burger Deal", "category": "Fast Food", "price": 850.0, "tax": 5.0},
        {"name": "Chicken Strips (5pcs)", "category": "Fast Food", "price": 550.0, "tax": 5.0},

        # Beverages
        {"name": "Fresh Lime Soda", "category": "Beverages", "price": 250.0, "tax": 16.0},
        {"name": "Mint Margarita", "category": "Beverages", "price": 350.0, "tax": 16.0},
        {"name": "Iced Americano", "category": "Beverages", "price": 400.0, "tax": 16.0},
        {"name": "Mineral Water (L)", "category": "Beverages", "price": 150.0, "tax": 0.0},
        
        # Desserts
        {"name": "Sizzling Brownie", "category": "Desserts", "price": 650.0, "tax": 5.0},
        {"name": "Cheesecake Slice", "category": "Desserts", "price": 750.0, "tax": 5.0},
        {"name": "Vanilla Ice Cream", "category": "Desserts", "price": 300.0, "tax": 5.0},
        
        # Sides
        {"name": "Masala Fries", "category": "Sides", "price": 350.0, "tax": 5.0},
        {"name": "Coleslaw", "category": "Sides", "price": 150.0, "tax": 5.0},
        {"name": "Garlic Mayo Dip", "category": "Sides", "price": 80.0, "tax": 5.0},
    ]

    added_count = 0
    for item in demo_items:
        # Check if exists (simple check by name)
        existing = db.search_menu(item["name"])
        if not existing:
            db.add_menu_item(item["name"], item["category"], item["price"], item["tax"])
            added_count += 1
            print(f"  + Added: {item['name']}")
        else:
            print(f"  . Skipped: {item['name']} (Already exists)")
            
    print(f"\n✅ Done! Added {added_count} new items to the menu.")

if __name__ == "__main__":
    db.connect()
    add_demo_menu()
