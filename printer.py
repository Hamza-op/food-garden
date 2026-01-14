"""
AuraPOS Professional - Printer Service (Windows)
Uses Windows built-in printing functionality
"""
import os
import subprocess
import tempfile
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime


class PrinterService:
    """Handles printing via Windows."""
    
    def __init__(self):
        self._last_error: Optional[str] = None
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    def print_receipt(self, sale_data: Dict[str, Any], settings: Dict[str, str]) -> tuple[bool, str]:
        """Print a sales receipt asynchronously to prevent UI freeze."""
        try:
            # Start printing in a separate thread
            import threading
            thread = threading.Thread(target=self._run_print_job, args=(sale_data, settings))
            thread.daemon = True
            thread.start()
            return True, "Printing started in background..."
        except Exception as e:
            self._last_error = f"Failed to start print job: {str(e)}"
            return False, self._last_error

    def _run_print_job(self, sale_data: Dict[str, Any], settings: Dict[str, str]):
        """Background worker for printing."""
        try:
            receipt_text = self.format_receipt_text(sale_data, settings)
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            receipt_path = os.path.join(temp_dir, f"receipt_{sale_data.get('receipt_no', 'temp')}.txt")
            
            with open(receipt_path, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            # Print using different methods
            success, msg = self._print_file(receipt_path)
            if not success:
               print(f"Background print failed: {msg}")
               
        except Exception as e:
            print(f"Background print error: {e}")
    
    def _print_file(self, file_path: str) -> tuple[bool, str]:
        """Print a file using available Windows methods."""
        
        # Method 1: Try using PowerShell to print
        try:
            cmd = f'powershell -Command "Get-Content -Path \'{file_path}\' | Out-Printer"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True, "Sent to default printer"
        except Exception as e:
            print(f"PowerShell print failed: {e}")
        
        # Method 2: Try notepad /p
        try:
            # CREATE_NO_WINDOW = 0x08000000
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            process = subprocess.Popen(
                ['notepad.exe', '/p', file_path],
                startupinfo=startupinfo
            )
            return True, "Print dialog opened"
        except Exception as e:
            print(f"Notepad print failed: {e}")
        
        # Method 3: Just open the file for manual printing
        try:
            os.startfile(file_path)
            return True, "Opened receipt. Use File→Print to print."
        except Exception as e:
            return False, f"Could not print: {e}"
    
    def test_print(self) -> tuple[bool, str]:
        """Print a test page."""
        try:
            test_content = f"""
==========================================
           AURAPOS TEST PRINT
==========================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Printer is working correctly!

This is a test receipt to verify
that your printer is configured
properly.

==========================================
"""
            
            temp_dir = tempfile.gettempdir()
            test_path = os.path.join(temp_dir, "aurapos_test_print.txt")
            
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            return self._print_file(test_path)
                
        except Exception as e:
            self._last_error = f"Test print failed: {str(e)}"
            return False, self._last_error
    
    def format_receipt_text(self, sale_data: Dict[str, Any], settings: Dict[str, str]) -> str:
        """Format receipt as text for printing."""
        restaurant_name = settings.get("restaurant_name", "Restaurant")
        restaurant_address = settings.get("restaurant_address", "")
        restaurant_phone = settings.get("restaurant_phone", "")
        currency = settings.get("currency_symbol", "Rs")
        footer = settings.get("receipt_footer", "Thank you!")
        
        width = 42
        lines = []
        
        # Header
        lines.append("=" * width)
        lines.append(restaurant_name.center(width))
        if restaurant_address:
            lines.append(restaurant_address.center(width))
        if restaurant_phone:
            lines.append(f"Tel: {restaurant_phone}".center(width))
        lines.append("=" * width)
        
        # Receipt info
        lines.append(f"Receipt: {sale_data.get('receipt_no', 'N/A')}")
        timestamp = sale_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))
        lines.append(f"Date: {timestamp}")
        cashier = sale_data.get('cashier', 'Staff')
        lines.append(f"Cashier: {cashier}")
        lines.append("-" * width)
        
        # Items
        items: List[Dict] = sale_data.get("items", [])
        for item in items:
            name = item.get("product_name", "Item")
            qty = item.get("qty", 1)
            price = item.get("price_at_sale", 0)
            total = qty * price
            
            lines.append(name)
            detail = f"  {qty} x {currency} {price:,.2f} = {currency} {total:,.2f}"
            lines.append(detail)
        
        lines.append("-" * width)
        
        # Totals
        subtotal = sale_data.get("subtotal", 0)
        tax = sale_data.get("tax", 0)
        discount = sale_data.get("discount", 0)
        total = sale_data.get("total", 0)
        
        lines.append(f"{'Subtotal:':<20} {currency} {subtotal:>10,.2f}")
        if tax > 0:
            lines.append(f"{'Tax:':<20} {currency} {tax:>10,.2f}")
        if discount > 0:
            lines.append(f"{'Discount:':<20}-{currency} {discount:>10,.2f}")
        
        lines.append("-" * width)
        lines.append(f"{'TOTAL:':<20} {currency} {total:>10,.2f}")
        lines.append("-" * width)
        
        lines.append(f"Payment: {sale_data.get('payment_type', 'Cash')}")
        lines.append("=" * width)
        
        lines.append("")
        lines.append(footer.center(width))
        lines.append("")
        
        return "\n".join(lines)
    
    def show_receipt_preview(self, sale_data: Dict[str, Any], settings: Dict[str, str]) -> tuple[bool, str]:
        """Show receipt in notepad for preview."""
        try:
            receipt_text = self.format_receipt_text(sale_data, settings)
            
            temp_dir = tempfile.gettempdir()
            receipt_path = os.path.join(temp_dir, f"receipt_preview_{sale_data.get('receipt_no', 'temp')}.txt")
            
            with open(receipt_path, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            os.startfile(receipt_path)
            return True, receipt_path
        except Exception as e:
            return False, str(e)


# Global printer instance
printer = PrinterService()
