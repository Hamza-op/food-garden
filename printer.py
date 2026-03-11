"""
AuraPOS Professional - Printer Service (Windows)
ESC/POS thermal-printer support with plain-text fallback
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

try:
    import win32print
    WIN32_PRINT_AVAILABLE = True
except ImportError:
    WIN32_PRINT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants — 80 mm thermal roll ≈ 42 printable chars @ 12 cpi (Font A)
# ─────────────────────────────────────────────────────────────────────────────
PRINT_TIMEOUT = 30
FEED_LINES    = 5          # blank lines before cut for tear-off clearance



# ─────────────────────────────────────────────────────────────────────────────
# ESC/POS Command Builder
# ─────────────────────────────────────────────────────────────────────────────
class ESCPOSBuilder:
    """
    Fluent builder for ESC/POS binary command sequences.

    Usage:
        data = (ESCPOSBuilder()
                .center().size(2,2).bold().line("MY SHOP")
                .normal().line("123 Main St")
                .cut()
                .build())
    """

    # ── printer control ──
    INIT         = b'\x1b\x40'
    PARTIAL_CUT  = b'\x1d\x56\x42\x03'   # feed + partial cut
    FULL_CUT     = b'\x1d\x56\x00'
    OPEN_DRAWER  = b'\x1b\x70\x00\x19\x19'  # kick pin 2

    # ── text style ──
    BOLD_ON      = b'\x1b\x45\x01'
    BOLD_OFF     = b'\x1b\x45\x00'
    ULINE_ON     = b'\x1b\x2d\x01'
    ULINE_OFF    = b'\x1b\x2d\x00'
    INVERSE_ON   = b'\x1d\x42\x01'       # white-on-black
    INVERSE_OFF  = b'\x1d\x42\x00'

    # ── alignment ──
    ALIGN_LEFT   = b'\x1b\x61\x00'
    ALIGN_CENTER = b'\x1b\x61\x01'
    ALIGN_RIGHT  = b'\x1b\x61\x02'

    # ── character size  \x1d\x21 <(w-1)<<4 | (h-1)> ──
    SIZE_NORMAL  = b'\x1d\x21\x00'       # 1×1
    SIZE_DH      = b'\x1d\x21\x01'       # 1×2
    SIZE_DW      = b'\x1d\x21\x10'       # 2×1
    SIZE_2X      = b'\x1d\x21\x11'       # 2×2

    LF           = b'\x0a'
    CHARSET_437  = b'\x1b\x74\x00'

    def __init__(self, encoding: str = 'cp437'):
        self._buf = bytearray()
        self._enc = encoding
        self._buf.extend(self.INIT)
        if encoding == 'cp437':
            self._buf.extend(self.CHARSET_437)

    # ── alignment ──
    def center(self):   self._buf.extend(self.ALIGN_CENTER); return self
    def left(self):     self._buf.extend(self.ALIGN_LEFT);   return self
    def right(self):    self._buf.extend(self.ALIGN_RIGHT);  return self

    # ── style ──
    def bold(self, on=True):
        self._buf.extend(self.BOLD_ON if on else self.BOLD_OFF); return self

    def underline(self, on=True):
        self._buf.extend(self.ULINE_ON if on else self.ULINE_OFF); return self

    def inverse(self, on=True):
        self._buf.extend(self.INVERSE_ON if on else self.INVERSE_OFF); return self

    def size(self, w: int = 1, h: int = 1):
        """Character magnification  1-8 × 1-8."""
        wb = max(0, min(7, w - 1))
        hb = max(0, min(7, h - 1))
        self._buf.extend(bytes([0x1d, 0x21, (wb << 4) | hb]))
        return self

    def normal(self):
        """Reset size / bold / underline / inverse."""
        self._buf.extend(self.SIZE_NORMAL + self.BOLD_OFF
                         + self.ULINE_OFF + self.INVERSE_OFF)
        return self

    # ── content ──
    def text(self, s: str):
        self._buf.extend(s.encode(self._enc, errors='replace')); return self

    def line(self, s: str = ''):
        if s:
            self.text(s)
        self._buf.extend(self.LF)
        return self

    def feed(self, n: int = 1):
        self._buf.extend(self.LF * n); return self

    def hr(self, char: str = '-', width: int = 42):
        """Horizontal rule / divider."""
        return self.line(char * width)

    # ── printer actions ──
    def cut(self, partial: bool = True):
        self.feed(FEED_LINES)
        self._buf.extend(self.PARTIAL_CUT if partial else self.FULL_CUT)
        return self

    def kick_drawer(self):
        self._buf.extend(self.OPEN_DRAWER); return self

    def build(self) -> bytes:
        return bytes(self._buf)


# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PrintResult:
    success: bool
    message: str


# ─────────────────────────────────────────────────────────────────────────────
class PrinterService:
    """Receipt printing via ESC/POS (thermal) with Windows text fallback."""

    def __init__(self, auto_cleanup: bool = True):
        self._last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._temp_files: List[Path] = []
        self._auto_cleanup = auto_cleanup
        if auto_cleanup:
            atexit.register(self._cleanup_temp_files)

    # ── helpers ──────────────────────────────────────────────────────────
    @property
    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error

    def _set_error(self, msg: str) -> None:
        with self._lock:
            self._last_error = msg

    def _cleanup_temp_files(self) -> None:
        for fp in self._temp_files:
            try:
                fp.exists() and fp.unlink()
            except OSError:
                pass
        self._temp_files.clear()

    @contextmanager
    def _create_temp_file(self, prefix: str, content: str):
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(tempfile.gettempdir()) / f"{prefix}_{ts}.txt"
        try:
            path.write_text(content, encoding='utf-8')
            self._temp_files.append(path)
            yield path
        except IOError as e:
            raise RuntimeError(f"Failed to create temp file: {e}") from e


    @staticmethod
    def _get_layout(paper_size: str) -> Dict[str, int]:
        if "58" in paper_size:
            return {"W": 32, "COL_QTY": 3, "COL_ITEM": 12, "COL_PRICE": 6, "COL_TOTAL": 8}
        return {"W": 42, "COL_QTY": 3, "COL_ITEM": 18, "COL_PRICE": 8, "COL_TOTAL": 10}

    @staticmethod
    def _extract_settings(settings: Dict[str, str]) -> Dict[str, str]:
        return {
            'name':     settings.get("restaurant_name",   "Restaurant"),
            'address':  settings.get("restaurant_address", ""),
            'phone':    settings.get("restaurant_phone",   ""),
            'currency': settings.get("currency_symbol",    "Rs"),
            'footer':   settings.get("receipt_footer",     "Thank you for visiting!"),
            'paper_size': settings.get("receipt_paper_size", "80mm"),
        }

    # ── public API ───────────────────────────────────────────────────────

    def print_receipt(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> Tuple[bool, str]:
        """Fire-and-forget background print (non-blocking)."""
        try:
            t = threading.Thread(
                target=self._run_print_job,
                args=(sale_data, settings),
                name="PrinterWorker",
                daemon=True,
            )
            t.start()
            return True, "Printing started …"
        except Exception as e:
            msg = f"Failed to start print job: {e}"
            self._set_error(msg); logger.error(msg)
            return False, msg

    def test_print(self) -> Tuple[bool, str]:
        """Print a hardware test page."""
        try:
            if self._try_escpos_test():
                return True, "ESC/POS test page sent"
            content = self._generate_test_page({'receipt_paper_size': '80mm'})
            with self._create_temp_file("aurapos_test", content) as p:
                r = self._print_text_file(p)
                return r.success, r.message
        except Exception as e:
            msg = f"Test print failed: {e}"
            self._set_error(msg); logger.error(msg)
            return False, msg

    def show_receipt_preview(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> Tuple[bool, str]:
        """Open plain-text receipt in Notepad for preview."""
        try:
            text = self.format_receipt_text(sale_data, settings)
            rno  = sale_data.get('receipt_no', 'temp')
            with self._create_temp_file(f"preview_{rno}", text) as p:
                os.startfile(str(p))
                return True, str(p)
        except Exception as e:
            msg = f"Preview failed: {e}"
            logger.error(msg)
            return False, msg

    # ── background worker ────────────────────────────────────────────────

    def _run_print_job(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> None:
        try:
            # Best path: ESC/POS binary → win32 RAW spool
            if self._try_escpos_print(sale_data, settings):
                return
            # Fallback: plain-text file → PowerShell / Notepad
            text = self.format_receipt_text(sale_data, settings)
            rno  = sale_data.get('receipt_no', 'temp')
            with self._create_temp_file(f"receipt_{rno}", text) as p:
                r = self._print_text_file(p)
                if not r.success:
                    self._set_error(r.message)
        except Exception as e:
            msg = f"Print error: {e}"
            logger.error(msg); self._set_error(msg)

    # ═════════════════════════════════════════════════════════════════════
    # PATH 1 — ESC/POS binary via win32print (best thermal output)
    # ═════════════════════════════════════════════════════════════════════

    def _is_thermal_printer(self, name: str) -> bool:
        """Heuristic: skip virtual / PDF printers."""
        skip = ("pdf", "onenote", "xps", "fax", "microsoft print")
        return not any(k in name.lower() for k in skip)

    def _send_raw(self, data: bytes, doc_name: str = "AuraPOS Receipt") -> bool:
        """Send raw bytes to the default printer via win32print."""
        if not WIN32_PRINT_AVAILABLE:
            return False
        try:
            name = win32print.GetDefaultPrinter()
            if not self._is_thermal_printer(name):
                return False
            h = win32print.OpenPrinter(name)
            try:
                win32print.StartDocPrinter(h, 1, (doc_name, None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, data)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
                logger.info(f"RAW data sent → {name}")
                return True
            finally:
                win32print.ClosePrinter(h)
        except Exception as e:
            logger.debug(f"win32print RAW failed: {e}")
            return False

    def _try_escpos_print(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> bool:
        """Build + send an ESC/POS receipt.  Returns True on success."""
        try:
            data = self._build_escpos_receipt(sale_data, settings)
            return self._send_raw(data)
        except Exception as e:
            logger.debug(f"ESC/POS build failed: {e}")
            return False

    def _try_escpos_test(self) -> bool:
        """Send a short ESC/POS test page."""
        b = ESCPOSBuilder()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        (b.center().hr('=')
          .size(2, 2).bold().line("AURAPOS").normal()
          .center().line("Printer Test Page")
          .hr('=')
          .left().line(f"Date: {ts}")
          .feed(1)
          .center()
          .bold().line(">> Printer OK <<").bold(False)
          .line("Thermal printer is")
          .line("configured correctly.")
          .feed(1).hr('=')
          .cut())
        return self._send_raw(b.build(), "AuraPOS Test")

    # ─────────────────────────────────────────────────────────────────────
    #  ESC/POS receipt layout
    # ─────────────────────────────────────────────────────────────────────

    def _build_escpos_receipt(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> bytes:
        cfg = self._extract_settings(settings)
        layout = self._get_layout(cfg['paper_size'])
        W = layout['W']
        COL_QTY, COL_ITEM, COL_PRICE, COL_TOTAL = layout['COL_QTY'], layout['COL_ITEM'], layout['COL_PRICE'], layout['COL_TOTAL']
        cur = cfg['currency']
        b   = ESCPOSBuilder()

        # ── HEADER ──────────────────────────────────────────────────────
        b.center()
        b.size(2, 2).bold().line(cfg['name'].upper()).normal()
        b.center()
        if cfg['address']:
            b.line(cfg['address'])
        if cfg['phone']:
            b.line(f"Tel: {cfg['phone']}")
        b.left().hr('=', W)

        # ── META ────────────────────────────────────────────────────────
        rno  = sale_data.get('receipt_no', 'N/A')
        ts   = sale_data.get('timestamp',
                             datetime.now().strftime('%Y-%m-%d %H:%M'))
        cash = sale_data.get('cashier', 'Staff')

        lbl = f"Rcpt: #{rno}"
        gap = max(W - len(lbl) - len(ts), 1)
        b.bold().line(f"{lbl}{' ' * gap}{ts}"[:W]).bold(False)
        b.line(f"Cashier: {cash}"[:W])
        b.hr('-', W)

        # ── COLUMN HEADER ──────────────────────────────────────────────
        hdr = (f"{'QTY':<{COL_QTY}} {'ITEM':<{COL_ITEM}} "
               f"{'PRICE':>{COL_PRICE}} {'TOTAL':>{COL_TOTAL}}")
        b.bold().line(hdr[:W]).bold(False)
        b.hr('-', W)

        # ── ITEMS ──────────────────────────────────────────────────────
        items = sale_data.get("items", [])
        for item in items:
            self._escpos_item(b, item, layout)
        b.hr('-', W)

        # ── TOTALS ─────────────────────────────────────────────────────
        subtotal = sale_data.get("subtotal", 0)
        tax      = sale_data.get("tax", 0)
        discount = sale_data.get("discount", 0)
        total    = sale_data.get("total", 0)

        def _row(label, val, prefix=''):
            amt  = f"{prefix}{cur} {val:,.2f}"
            sp   = max(W - len(label) - len(amt), 1)
            return f"{label}{' ' * sp}{amt}"[:W]

        b.line(_row("Subtotal", subtotal))
        if tax > 0:
            b.line(_row("Tax", tax, '+'))
        if discount > 0:
            b.line(_row("Discount", discount, '-'))

        b.hr('=', W)
        # Grand total — double-height + bold
        b.size(1, 2).bold()
        b.line(_row("TOTAL", total))
        b.normal()
        b.hr('=', W)

        # ── PAYMENT ────────────────────────────────────────────────────
        pay = sale_data.get('payment_type', 'Cash').upper()
        b.bold().line(f"PAID BY: {pay}").bold(False)

        tendered = sale_data.get('amount_tendered', 0)
        change   = sale_data.get('change', 0)
        if pay == 'CASH' and tendered > 0:
            b.line(_row("Tendered", tendered))
            b.bold().line(_row("Change", change)).bold(False)

        b.hr('-', W)

        # ── FOOTER ─────────────────────────────────────────────────────
        b.center().feed(1)
        for fline in cfg['footer'].split('\\n'):
            fline = fline.strip()
            if fline:
                b.bold().line(fline).bold(False)
        b.feed(1)
        b.normal().center()
        b.line(f"Items: {len(items)}  |  "
               f"{datetime.now().strftime('%d/%m/%Y %H:%M')}")
        b.left()

        # ── CUT ────────────────────────────────────────────────────────
        b.cut()
        return b.build()

    @staticmethod
    def _escpos_item(b: ESCPOSBuilder, item: Dict[str, Any], layout: Dict[str, int]):
        W, COL_QTY, COL_ITEM = layout["W"], layout["COL_QTY"], layout["COL_ITEM"]
        COL_PRICE, COL_TOTAL = layout["COL_PRICE"], layout["COL_TOTAL"]
        """Append one item (with word-wrap) to the ESC/POS builder."""
        name  = str(item.get("product_name", "Item"))
        qty   = item.get("qty", 1)
        price = float(item.get("price_at_sale", 0))
        total = qty * price

        parts   = textwrap.wrap(name, width=COL_ITEM) or [name[:COL_ITEM]]
        p_str   = f"{price:,.0f}" if COL_PRICE < 8 else f"{price:,.2f}"
        t_str   = f"{total:,.0f}" if COL_TOTAL < 10 else f"{total:,.2f}"
        first   = (f"{str(qty)[:COL_QTY]:<{COL_QTY}} {parts[0]:<{COL_ITEM}} "
                    f"{p_str[:COL_PRICE]:>{COL_PRICE}} {t_str[:COL_TOTAL]:>{COL_TOTAL}}")
        b.line(first[:W])
        indent = ' ' * (COL_QTY + 1)
        for extra in parts[1:]:
            b.line(f"{indent}{extra}"[:W])

    # ═════════════════════════════════════════════════════════════════════
    # PATH 2 — Plain-text fallback  (PowerShell → Notepad → Open)
    # ═════════════════════════════════════════════════════════════════════

    def _print_text_file(self, file_path: Path) -> PrintResult:
        for fn in (self._try_powershell_print,
                   self._try_notepad_print,
                   self._try_open_file):
            if r := fn(file_path):
                return r
        return PrintResult(False, "No print method available")

    def _try_powershell_print(self, fp: Path) -> Optional[PrintResult]:
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 f'Get-Content -LiteralPath "{fp}" | Out-Printer'],
                capture_output=True, text=True,
                timeout=PRINT_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if r.returncode == 0:
                return PrintResult(True, "Sent via PowerShell")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"PowerShell: {e}")
        return None

    def _try_notepad_print(self, fp: Path) -> Optional[PrintResult]:
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            subprocess.Popen(['notepad.exe', '/p', str(fp)], startupinfo=si)
            return PrintResult(True, "Sent via Notepad")
        except (FileNotFoundError, OSError) as e:
            logger.debug(f"Notepad: {e}")
        return None

    def _try_open_file(self, fp: Path) -> PrintResult:
        try:
            os.startfile(str(fp))
            return PrintResult(True, "Opened — use File → Print")
        except OSError as e:
            return PrintResult(False, f"Cannot print: {e}")

    # ─────────────────────────────────────────────────────────────────────
    #  Plain-text receipt  (also used for preview)
    # ─────────────────────────────────────────────────────────────────────

    def format_receipt_text(
        self,
        sale_data: Dict[str, Any],
        settings: Dict[str, str],
    ) -> str:
        cfg = self._extract_settings(settings)
        layout = self._get_layout(cfg['paper_size'])
        W = layout['W']
        COL_QTY, COL_ITEM, COL_PRICE, COL_TOTAL = layout['COL_QTY'], layout['COL_ITEM'], layout['COL_PRICE'], layout['COL_TOTAL']
        cur = cfg['currency']
        ln: List[str] = []

        div_eq   = '=' * W
        div_dash = '-' * W
        ctr = lambda s: s.center(W).rstrip()

        # ── header ──
        ln.append(div_eq)
        ln.append(ctr(f"** {cfg['name'].upper()} **"))
        ln.append(div_eq)
        parts = []
        if cfg['address']:
            parts.append(cfg['address'])
        if cfg['phone']:
            parts.append(f"Tel: {cfg['phone']}")
        if parts:
            combo = ' | '.join(parts)
            if len(combo) <= W:
                ln.append(ctr(combo))
            else:
                for p in parts:
                    ln.append(ctr(p))
        ln.append(div_dash)

        # ── meta ──
        rno = sale_data.get('receipt_no', 'N/A')
        ts  = sale_data.get('timestamp',
                            datetime.now().strftime('%Y-%m-%d %H:%M'))
        cas = sale_data.get('cashier', 'Staff')

        lbl = f"Rcpt: #{rno}"
        gap = max(W - len(lbl) - len(ts), 1)
        ln.append(f"{lbl}{' ' * gap}{ts}"[:W])
        ln.append(f"Cashier: {cas}"[:W])
        ln.append(div_dash)

        # ── column header ──
        hdr = (f"{'QTY':<{COL_QTY}} {'ITEM':<{COL_ITEM}} "
               f"{'PRICE':>{COL_PRICE}} {'TOTAL':>{COL_TOTAL}}")
        ln.append(hdr[:W])
        ln.append(div_dash)

        # ── items ──
        items = sale_data.get("items", [])
        for item in items:
            self._text_item(ln, item, layout)
        ln.append(div_dash)

        # ── totals ──
        subtotal = sale_data.get("subtotal", 0)
        tax      = sale_data.get("tax", 0)
        discount = sale_data.get("discount", 0)
        total    = sale_data.get("total", 0)

        def _row(label, val, prefix=''):
            amt = f"{prefix}{cur} {val:,.2f}"
            sp  = max(W - len(label) - len(amt), 1)
            return f"{label}{' ' * sp}{amt}"[:W]

        ln.append(_row("Subtotal", subtotal))
        if tax > 0:
            ln.append(_row("Tax", tax, '+'))
        if discount > 0:
            ln.append(_row("Discount", discount, '-'))
        ln.append(div_eq)
        ln.append(_row("** TOTAL **", total))
        ln.append(div_eq)

        # ── payment ──
        pay = sale_data.get('payment_type', 'Cash').upper()
        ln.append(f"PAID BY: {pay}"[:W])

        tendered = sale_data.get('amount_tendered', 0)
        change   = sale_data.get('change', 0)
        if pay == 'CASH' and tendered > 0:
            ln.append(_row("Tendered", tendered))
            ln.append(_row("Change", change))

        ln.append(div_dash)

        # ── footer ──
        ln.append('')
        for fline in cfg['footer'].split('\\n'):
            fline = fline.strip()
            if fline:
                ln.append(ctr(f"* {fline} *"))
        ln.append('')
        ln.append(ctr(
            f"Items: {len(items)}  |  "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ))
        ln.append(div_dash)

        # feed
        ln.extend([''] * FEED_LINES)
        return '\n'.join(ln)

    @staticmethod
    def _text_item(ln: List[str], item: Dict[str, Any], layout: Dict[str, int]):
        W, COL_QTY, COL_ITEM = layout["W"], layout["COL_QTY"], layout["COL_ITEM"]
        COL_PRICE, COL_TOTAL = layout["COL_PRICE"], layout["COL_TOTAL"]
        name  = str(item.get("product_name", "Item"))
        qty   = item.get("qty", 1)
        price = float(item.get("price_at_sale", 0))
        total = qty * price

        parts = textwrap.wrap(name, width=COL_ITEM) or [name[:COL_ITEM]]
        p_s   = f"{price:,.0f}" if COL_PRICE < 8 else f"{price:,.2f}"
        t_s   = f"{total:,.0f}" if COL_TOTAL < 10 else f"{total:,.2f}"
        first = (f"{str(qty)[:COL_QTY]:<{COL_QTY}} {parts[0]:<{COL_ITEM}} "
                 f"{p_s[:COL_PRICE]:>{COL_PRICE}} {t_s[:COL_TOTAL]:>{COL_TOTAL}}")
        ln.append(first[:W])
        indent = ' ' * (COL_QTY + 1)
        for extra in parts[1:]:
            ln.append(f"{indent}{extra}"[:W])

    def _generate_test_page(self, settings: Dict[str, str]) -> str:
        W = self._get_layout(settings.get('receipt_paper_size', '80mm'))['W']
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        eq = '=' * W
        return '\n'.join([
            eq,
            "AURAPOS TEST PRINT".center(W),
            eq,
            f"Date: {ts}",
            '',
            "Printer is working correctly!".center(W),
            '',
            "This is a test receipt".center(W),
            "to verify your printer".center(W),
            "is configured properly.".center(W),
            '',
            eq,
        ])


# ─────────────────────────────────────────────────────────────────────────────
printer = PrinterService()