"""
AuraPOS Professional - Printer Service (Windows)
Uses Windows built-in printing functionality
"""
import os
import subprocess
import tempfile
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from contextlib import contextmanager
import textwrap
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
RECEIPT_WIDTH = 42
PRINT_TIMEOUT = 30
FEED_LINES = 3

# Column widths for receipt items
COL_QTY = 2
COL_ITEM = 19
COL_PRICE = 8
COL_TOTAL = 10


@dataclass(frozen=True)
class PrintResult:
    """Immutable result of a print operation."""
    success: bool
    message: str


class PrinterService:
    """Handles printing via Windows."""

    def __init__(self, auto_cleanup: bool = True):
        """
        Initialize printer service.
        
        Args:
            auto_cleanup: If True, temp files are cleaned up on exit
        """
        self._last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._temp_files: List[Path] = []
        self._auto_cleanup = auto_cleanup
        
        if auto_cleanup:
            atexit.register(self._cleanup_temp_files)

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message (thread-safe)."""
        with self._lock:
            return self._last_error

    def _set_error(self, error: str) -> None:
        """Set the last error message (thread-safe)."""
        with self._lock:
            self._last_error = error

    def _cleanup_temp_files(self) -> None:
        """Remove all temporary files created by this service."""
        for file_path in self._temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError as e:
                logger.debug(f"Could not delete temp file {file_path}: {e}")
        self._temp_files.clear()

    @contextmanager
    def _create_temp_file(self, prefix: str, content: str):
        """
        Create a temporary file with content.
        
        Yields:
            Path to the temporary file
        """
        temp_dir = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = temp_dir / f"{prefix}_{timestamp}.txt"
        
        try:
            file_path.write_text(content, encoding='utf-8')
            self._temp_files.append(file_path)
            yield file_path
        except IOError as e:
            raise RuntimeError(f"Failed to create temp file: {e}") from e

    def print_receipt(
        self, 
        sale_data: Dict[str, Any], 
        settings: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Print a sales receipt asynchronously to prevent UI freeze.
        
        Args:
            sale_data: Dictionary containing sale information
            settings: Dictionary containing printer/restaurant settings
            
        Returns:
            Tuple of (success, message)
        """
        try:
            thread = threading.Thread(
                target=self._run_print_job,
                args=(sale_data, settings),
                name="PrinterWorker",
                daemon=True
            )
            thread.start()
            return True, "Printing started in background..."
        except Exception as e:
            error_msg = f"Failed to start print job: {e}"
            self._set_error(error_msg)
            logger.error(error_msg)
            return False, error_msg

    def _run_print_job(
        self, 
        sale_data: Dict[str, Any], 
        settings: Dict[str, str]
    ) -> None:
        """Background worker for printing."""
        try:
            receipt_text = self.format_receipt_text(sale_data, settings)
            receipt_no = sale_data.get('receipt_no', 'temp')
            
            with self._create_temp_file(f"receipt_{receipt_no}", receipt_text) as path:
                result = self._print_file(path)
                if not result.success:
                    logger.warning(f"Background print failed: {result.message}")
                    self._set_error(result.message)
        except Exception as e:
            error_msg = f"Background print error: {e}"
            logger.error(error_msg)
            self._set_error(error_msg)

    def _try_powershell_print(self, file_path: Path) -> Optional[PrintResult]:
        """Attempt to print using PowerShell."""
        try:
            # Use list form to avoid shell injection
            result = subprocess.run(
                [
                    'powershell', '-NoProfile', '-Command',
                    f'Get-Content -LiteralPath "{file_path}" | Out-Printer'
                ],
                capture_output=True,
                text=True,
                timeout=PRINT_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return PrintResult(True, "Sent to default printer")
        except subprocess.TimeoutExpired:
            logger.warning("PowerShell print timed out")
        except FileNotFoundError:
            logger.debug("PowerShell not available")
        except Exception as e:
            logger.debug(f"PowerShell print failed: {e}")
        return None

    def _try_notepad_print(self, file_path: Path) -> Optional[PrintResult]:
        """Attempt to print using Notepad."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            subprocess.Popen(
                ['notepad.exe', '/p', str(file_path)],
                startupinfo=startupinfo
            )
            return PrintResult(True, "Print dialog opened")
        except FileNotFoundError:
            logger.debug("Notepad not available")
        except Exception as e:
            logger.debug(f"Notepad print failed: {e}")
        return None

    def _try_open_file(self, file_path: Path) -> PrintResult:
        """Attempt to open file for manual printing."""
        try:
            os.startfile(str(file_path))
            return PrintResult(True, "Opened receipt. Use File→Print to print.")
        except OSError as e:
            return PrintResult(False, f"Could not print: {e}")

    def _print_file(self, file_path: Path) -> PrintResult:
        """
        Print a file using available Windows methods.
        
        Tries methods in order of preference:
        1. PowerShell (silent, reliable)
        2. Notepad /p (silent)
        3. Open file (manual)
        """
        # Method 1: PowerShell
        if result := self._try_powershell_print(file_path):
            return result

        # Method 2: Notepad
        if result := self._try_notepad_print(file_path):
            return result

        # Method 3: Fallback - open file
        return self._try_open_file(file_path)

    def test_print(self) -> Tuple[bool, str]:
        """
        Print a test page to verify printer configuration.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            test_content = self._generate_test_page()
            
            with self._create_temp_file("aurapos_test_print", test_content) as path:
                result = self._print_file(path)
                return result.success, result.message
        except Exception as e:
            error_msg = f"Test print failed: {e}"
            self._set_error(error_msg)
            logger.error(error_msg)
            return False, error_msg

    def _generate_test_page(self) -> str:
        """Generate test page content."""
        divider = "=" * RECEIPT_WIDTH
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
{divider}
{"AURAPOS TEST PRINT":^{RECEIPT_WIDTH}}
{divider}
Date: {timestamp}

Printer is working correctly!

This is a test receipt to verify
that your printer is configured
properly.

{divider}
"""

    def format_receipt_text(
        self, 
        sale_data: Dict[str, Any], 
        settings: Dict[str, str]
    ) -> str:
        """
        Format receipt as text for printing.
        
        Args:
            sale_data: Sale transaction data
            settings: Restaurant and receipt settings
            
        Returns:
            Formatted receipt text
        """
        config = self._extract_settings(settings)
        lines: List[str] = []
        
        # Build receipt sections
        self._add_header(lines, config)
        self._add_meta_info(lines, sale_data)
        self._add_items(lines, sale_data, config['currency'])
        self._add_totals(lines, sale_data, config['currency'])
        self._add_footer(lines, sale_data, config['footer'])
        
        return "\n".join(lines)

    @staticmethod
    def _extract_settings(settings: Dict[str, str]) -> Dict[str, str]:
        """Extract and provide defaults for receipt settings."""
        return {
            'name': settings.get("restaurant_name", "Restaurant"),
            'address': settings.get("restaurant_address", ""),
            'phone': settings.get("restaurant_phone", ""),
            'currency': settings.get("currency_symbol", "Rs"),
            'footer': settings.get("receipt_footer", "Thank you!"),
        }

    @staticmethod
    def _center(text: str) -> str:
        """Center text within receipt width."""
        return text.center(RECEIPT_WIDTH).rstrip()

    @staticmethod
    def _divider(char: str = "-") -> str:
        """Create a divider line."""
        return char * RECEIPT_WIDTH

    def _add_header(self, lines: List[str], config: Dict[str, str]) -> None:
        """Add receipt header section."""
        decoration = "*" * (RECEIPT_WIDTH - 12)
        
        lines.append(self._center(decoration))
        lines.append(self._center(config['name'].upper()))
        
        if config['address']:
            lines.append(self._center(config['address']))
        if config['phone']:
            lines.append(self._center(f"Tel: {config['phone']}"))
            
        lines.append(self._center(decoration))
        lines.append("")

    def _add_meta_info(self, lines: List[str], sale_data: Dict[str, Any]) -> None:
        """Add receipt meta information."""
        receipt_no = sale_data.get('receipt_no', 'N/A')
        timestamp = sale_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))
        cashier = sale_data.get('cashier', 'Staff')
        
        lines.append(f"RCP NO : {receipt_no}")
        lines.append(f"DATE   : {timestamp}")
        lines.append(f"SERVER : {cashier}")
        lines.append(self._divider("="))

    def _add_items(
        self, 
        lines: List[str], 
        sale_data: Dict[str, Any], 
        currency: str
    ) -> None:
        """Add items section to receipt."""
        col_fmt = f"{{:<{COL_QTY}}} {{:<{COL_ITEM}}} {{:>{COL_PRICE}}} {{:>{COL_TOTAL}}}"
        
        lines.append(col_fmt.format("QT", "ITEM", "PRICE", "TOTAL"))
        lines.append(self._divider("-"))
        
        items: List[Dict] = sale_data.get("items", [])
        for item in items:
            self._add_item_line(lines, item, col_fmt)
            
        lines.append(self._divider("-"))

    def _add_item_line(
        self, 
        lines: List[str], 
        item: Dict[str, Any], 
        col_fmt: str
    ) -> None:
        """Add a single item line with word wrapping."""
        name = item.get("product_name", "Item")
        qty = item.get("qty", 1)
        price = item.get("price_at_sale", 0)
        total = qty * price
        
        wrapped_name = textwrap.wrap(name, width=COL_ITEM) or [name]
        
        # First line with all columns
        lines.append(col_fmt.format(
            str(qty), 
            wrapped_name[0], 
            f"{price:,.2f}", 
            f"{total:,.2f}"
        ))
        
        # Continuation lines (name only)
        for extra_line in wrapped_name[1:]:
            lines.append(col_fmt.format("", extra_line, "", ""))

    def _add_totals(
        self, 
        lines: List[str], 
        sale_data: Dict[str, Any], 
        currency: str
    ) -> None:
        """Add totals section to receipt."""
        subtotal = sale_data.get("subtotal", 0)
        tax = sale_data.get("tax", 0)
        discount = sale_data.get("discount", 0)
        total = sale_data.get("total", 0)
        
        def format_total_row(label: str, value: float, prefix: str = " ") -> str:
            return f"{label:<20} {prefix} {currency:>3} {value:>10,.2f}"
        
        lines.append(format_total_row("SUBTOTAL", subtotal))
        
        if tax > 0:
            lines.append(format_total_row("TAX", tax, "+"))
        if discount > 0:
            lines.append(format_total_row("DISCOUNT", discount, "-"))
            
        lines.append(self._divider("="))
        lines.append(f"{'TOTAL':<20}   {currency:>3} {total:>10,.2f}")
        lines.append(self._divider("="))

    def _add_footer(
        self, 
        lines: List[str], 
        sale_data: Dict[str, Any], 
        footer_text: str
    ) -> None:
        """Add footer section to receipt."""
        pay_type = sale_data.get('payment_type', 'Cash')
        
        lines.append(f"PAYMENT MODE: {pay_type.upper()}")
        lines.append("")
        lines.append(self._center(footer_text))
        lines.append(self._center("******"))
        
        # Feed lines for tear-off
        lines.extend([""] * FEED_LINES)

    def show_receipt_preview(
        self, 
        sale_data: Dict[str, Any], 
        settings: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Show receipt in notepad for preview.
        
        Args:
            sale_data: Sale transaction data
            settings: Restaurant and receipt settings
            
        Returns:
            Tuple of (success, file_path or error_message)
        """
        try:
            receipt_text = self.format_receipt_text(sale_data, settings)
            receipt_no = sale_data.get('receipt_no', 'temp')
            
            with self._create_temp_file(f"receipt_preview_{receipt_no}", receipt_text) as path:
                os.startfile(str(path))
                return True, str(path)
        except Exception as e:
            error_msg = f"Preview failed: {e}"
            logger.error(error_msg)
            return False, error_msg


# ─────────────────────────────────────────────────────────────────────────────
# Global printer instance
# ─────────────────────────────────────────────────────────────────────────────
printer = PrinterService()