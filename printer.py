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

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants — 80 mm thermal roll ≈ 42 printable chars @ 12 cpi (Font A)
# ─────────────────────────────────────────────────────────────────────────────
PRINT_TIMEOUT = 30
# Blank lines before cut for tear-off clearance.
# Keep this small to avoid large top/bottom white space between receipts.
FEED_LINES = 2



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
    DOUBLE_ON    = b'\x1b\x47\x01'       # double-strike (not supported on all printers)
    DOUBLE_OFF   = b'\x1b\x47\x00'
    ULINE_ON     = b'\x1b\x2d\x01'
    ULINE_OFF    = b'\x1b\x2d\x00'
    INVERSE_ON   = b'\x1d\x42\x01'       # white-on-black
    INVERSE_OFF  = b'\x1d\x42\x00'

    # ── alignment ──
    ALIGN_LEFT   = b'\x1b\x61\x00'
    ALIGN_CENTER = b'\x1b\x61\x01'
    ALIGN_RIGHT  = b'\x1b\x61\x02'

    # ── font / spacing ──
    FONT_A       = b'\x1b\x4d\x00'       # 12×24 (Font A)
    FONT_B       = b'\x1b\x4d\x01'       # 9×17  (Font B)
    LINE_SPACING_DEFAULT = b'\x1b\x32'   # ESC 2
    SMOOTH_ON   = b'\x1d\x62\x01'        # GS b 1 (character smoothing; ignored if unsupported)
    SMOOTH_OFF  = b'\x1d\x62\x00'

    # ── 2D / QR ──
    GS_K         = b'\x1d\x28\x6b'

    # ── character size  \x1d\x21 <(w-1)<<4 | (h-1)> ──
    SIZE_NORMAL  = b'\x1d\x21\x00'       # 1×1
    SIZE_DH      = b'\x1d\x21\x01'       # 1×2
    SIZE_DW      = b'\x1d\x21\x10'       # 2×1
    SIZE_2X      = b'\x1d\x21\x11'       # 2×2

    LF           = b'\x0a'
    CHARSET_437  = b'\x1b\x74\x00'
    SET_LEFT_MARGIN = b'\x1d\x4c'       # GS L nL nH
    SET_PRINT_WIDTH = b'\x1d\x57'       # GS W nL nH (in dots)

    def __init__(
        self,
        encoding: str = 'cp437',
        *,
        left_margin_dots: int = 0,
        print_width_dots: int | None = None,
        smoothing: bool = True,
    ):
        self._buf = bytearray()
        self._enc = encoding
        self._buf.extend(self.INIT)
        if encoding == 'cp437':
            self._buf.extend(self.CHARSET_437)
        if smoothing:
            self._buf.extend(self.SMOOTH_ON)
        # Ensure we use the full thermal printable area (prevents "centered" output).
        try:
            lm = max(0, min(65535, int(left_margin_dots)))
            self._buf.extend(self.SET_LEFT_MARGIN + bytes([lm & 0xFF, (lm >> 8) & 0xFF]))
        except Exception:
            pass
        if print_width_dots is not None:
            try:
                pw = max(0, min(65535, int(print_width_dots)))
                self._buf.extend(self.SET_PRINT_WIDTH + bytes([pw & 0xFF, (pw >> 8) & 0xFF]))
            except Exception:
                pass

    # ── alignment ──
    def center(self):   self._buf.extend(self.ALIGN_CENTER); return self
    def left(self):     self._buf.extend(self.ALIGN_LEFT);   return self
    def right(self):    self._buf.extend(self.ALIGN_RIGHT);  return self

    def font_a(self):   self._buf.extend(self.FONT_A); return self
    def font_b(self):   self._buf.extend(self.FONT_B); return self
    def line_spacing_default(self): self._buf.extend(self.LINE_SPACING_DEFAULT); return self
    def smoothing(self, on: bool = True): self._buf.extend(self.SMOOTH_ON if on else self.SMOOTH_OFF); return self

    # ── style ──
    def bold(self, on=True):
        self._buf.extend(self.BOLD_ON if on else self.BOLD_OFF); return self

    def double_strike(self, on=True):
        self._buf.extend(self.DOUBLE_ON if on else self.DOUBLE_OFF); return self

    def underline(self, on=True):
        self._buf.extend(self.ULINE_ON if on else self.ULINE_OFF); return self

    def inverse(self, on=True):
        self._buf.extend(self.INVERSE_ON if on else self.INVERSE_OFF); return self

    def qrcode(
        self,
        data: str,
        *,
        module_size: int = 6,
        ecc: str = "M",
    ):
        """
        Print a QR code (ESC/POS model 2).
        - module_size: 1..16 (typical 4..8)
        - ecc: L, M, Q, H
        """
        try:
            payload = (data or "").encode(self._enc, errors="replace")
            if not payload:
                return self

            size = max(1, min(16, int(module_size)))
            ecc_map = {"L": 48, "M": 49, "Q": 50, "H": 51}
            ecc_n = ecc_map.get(str(ecc).upper().strip(), 49)

            # Select model 2
            self._buf.extend(self.GS_K + b'\x04\x00' + b'\x31\x41\x32\x00')
            # Set module size
            self._buf.extend(self.GS_K + b'\x03\x00' + b'\x31\x43' + bytes([size]))
            # Set error correction
            self._buf.extend(self.GS_K + b'\x03\x00' + b'\x31\x45' + bytes([ecc_n]))
            # Store data
            n = len(payload) + 3
            pL = n & 0xFF
            pH = (n >> 8) & 0xFF
            self._buf.extend(self.GS_K + bytes([pL, pH]) + b'\x31\x50\x30' + payload)
            # Print
            self._buf.extend(self.GS_K + b'\x03\x00' + b'\x31\x51\x30')
            self._buf.extend(self.LF)
        except Exception:
            pass
        return self

    def size(self, w: int = 1, h: int = 1):
        """Character magnification  1-8 × 1-8."""
        wb = max(0, min(7, w - 1))
        hb = max(0, min(7, h - 1))
        self._buf.extend(bytes([0x1d, 0x21, (wb << 4) | hb]))
        return self

    def normal(self):
        """Reset size / bold / underline / inverse."""
        self._buf.extend(self.SIZE_NORMAL + self.BOLD_OFF
                         + self.DOUBLE_OFF
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
            # ITEM | PRICE | xQTY | TOTAL
            # Total width 32 = 12 + 1 + 7 + 1 + 3 + 1 + 7
            return {"W": 32, "COL_ITEM": 12, "COL_PRICE": 7, "COL_XQTY": 3, "COL_TOTAL": 7}
        # 80mm printers are commonly 576 dots/line. With Font A (~12 dots/char) that's ~48 columns.
        # ITEM | PRICE | xQTY | TOTAL
        # Total width 48 = 21 + 1 + 9 + 1 + 5 + 1 + 10
        return {"W": 48, "COL_ITEM": 21, "COL_PRICE": 9, "COL_XQTY": 5, "COL_TOTAL": 10}

    @staticmethod
    def _extract_settings(settings: Dict[str, str]) -> Dict[str, str]:
        return {
            'name':     settings.get("restaurant_name",   "Restaurant"),
            'address':  settings.get("restaurant_address", ""),
            'phone':    settings.get("restaurant_phone",   ""),
            'currency': settings.get("currency_symbol",    "Rs"),
            'footer':   settings.get("receipt_footer",     "Thank you for visiting!"),
            'paper_size': settings.get("receipt_paper_size", "80mm"),
            'qr_text': settings.get("receipt_qr_text", ""),
            'qr_caption': settings.get("receipt_qr_caption", "Scan for menu / offers"),
            'high_contrast': settings.get("receipt_high_contrast", False),
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
        b = ESCPOSBuilder(left_margin_dots=0, print_width_dots=576, smoothing=True).font_a().line_spacing_default()
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
        COL_ITEM, COL_PRICE, COL_XQTY, COL_TOTAL = (
            layout["COL_ITEM"],
            layout["COL_PRICE"],
            layout["COL_XQTY"],
            layout["COL_TOTAL"],
        )
        cur = cfg['currency']
        pw = 384 if "58" in str(cfg.get("paper_size", "")) else 576
        b = ESCPOSBuilder(left_margin_dots=0, print_width_dots=pw, smoothing=True).font_a().line_spacing_default()

        # ── HEADER ──────────────────────────────────────────────────────
        b.center()
        # Brand / "logo" — centered, bold, double-height
        name = cfg['name'].upper()
        b.inverse(True).size(2, 2).bold().double_strike(True).line(f" {name} ").inverse(False).normal()
        b.feed(1)

        # ── META (TOP) ──────────────────────────────────────────────────
        rno = sale_data.get('receipt_no', 'N/A')
        cash = sale_data.get('cashier', 'Staff')

        sale_dt = self._parse_sale_datetime(sale_data.get('timestamp'))
        ts_meta = sale_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Merge receipt/order into one short code (last chunk of receipt no)
        short_code = str(rno).split("-")[-1].strip() or str(rno)
        bill_lbl = f"BILL #{short_code}"
        date_lbl = ts_meta
        gap = max(W - len(bill_lbl) - len(date_lbl), 1)

        b.font_b().left()
        b.line(f"{bill_lbl}{' ' * gap}{date_lbl}"[:W])
        phone = str(cfg.get('phone') or '').strip()
        cashier_lbl = f"Cashier: {cash}"
        if phone:
            tel_lbl = f"Tel: {phone}"
            gap2 = max(W - len(cashier_lbl) - len(tel_lbl), 1)
            line2 = f"{cashier_lbl}{' ' * gap2}{tel_lbl}"
            if len(line2) <= W:
                b.line(line2[:W])
            else:
                # Fallback: append tel if it still fits, otherwise just cashier.
                compact = f"{cashier_lbl}  {tel_lbl}"
                b.line((compact if len(compact) <= W else cashier_lbl)[:W])
        else:
            b.line(cashier_lbl[:W])
        b.font_a().left().hr('=', W)

        # ── COLUMN HEADER ──────────────────────────────────────────────
        hdr = (
            f"{'ITEM':<{COL_ITEM}} "
            f"{'PRICE':>{COL_PRICE}} "
            f"{'xQTY':>{COL_XQTY}} "
            f"{'TOTAL':>{COL_TOTAL}}"
        )
        b.inverse(True).bold().line(hdr.ljust(W)[:W]).bold(False).inverse(False)
        b.hr('-', W)

        # ── ITEMS ──────────────────────────────────────────────────────
        high_contrast = str(cfg.get("high_contrast", False)).lower() in ("1", "true", "yes", "on")
        if high_contrast:
            b.double_strike(True)
        items = sale_data.get("items", [])
        for item in items:
            self._escpos_item(b, item, layout)
        if high_contrast:
            b.double_strike(False)
        b.hr('-', W)

        # ── TOTALS ─────────────────────────────────────────────────────
        subtotal = sale_data.get("subtotal", 0)
        tax      = sale_data.get("tax", 0)
        discount = sale_data.get("discount", 0)
        total    = sale_data.get("total", 0)

        def _row(label, val, prefix=''):
            sign = str(prefix or "")
            if sign and not sign.endswith(" "):
                sign += " "
            amt = f"{sign}{cur} {val:,.2f}"
            sp   = max(W - len(label) - len(amt), 1)
            return f"{label}{' ' * sp}{amt}"[:W]

        if high_contrast:
            b.double_strike(True)
        b.line(_row("Subtotal", subtotal))
        if tax > 0:
            b.line(_row("Tax", tax, '+'))
        if discount > 0:
            b.line(_row("Discount", discount, '-'))
        if high_contrast:
            b.double_strike(False)

        b.hr('=', W)
        # Grand total — double-height + bold
        b.inverse(True).size(1, 2).bold().double_strike(True)
        b.line(_row("TOTAL", total))
        b.inverse(False).normal()
        b.hr('=', W)

        # ── PAYMENT ────────────────────────────────────────────────────
        pay = sale_data.get('payment_type', 'Cash').upper()
        if high_contrast:
            b.double_strike(True)
        b.right().bold().line(f"PAID BY: {pay}").bold(False).left()
        if high_contrast:
            b.double_strike(False)

        tendered = sale_data.get('amount_tendered', 0)
        change   = sale_data.get('change', 0)
        if pay == 'CASH' and tendered > 0:
            b.line(_row("Tendered", tendered))
            b.bold().line(_row("Change", change)).bold(False)

        # ── FOOTER ─────────────────────────────────────────────────────
        # Footer: always 2 lines (cleaner). Line 1 = bold stamp, line 2 = softer address.
        b.center()
        thanks_lines = (cfg.get('footer') or "Thanks for shopping!").strip().splitlines()
        thanks_msg = (thanks_lines[0] if thanks_lines else "Thanks for shopping!").strip() or "Thanks for shopping!"
        stamp = f" {thanks_msg} "
        if len(stamp) > W:
            stamp = stamp[:W]
        b.inverse(True).bold().double_strike(True).line(stamp).double_strike(False).bold(False).inverse(False)

        address = str(cfg.get('address') or '').strip()
        if address:
            b.font_b().line(address).font_a()
        b.font_a().left()

        # Optional QR (disabled unless configured)
        if cfg.get('qr_text'):
            b.feed(1)
            caption = str(cfg.get('qr_caption') or '').strip()
            if caption:
                b.line(caption)
            b.qrcode(str(cfg['qr_text']), module_size=6, ecc="M")
        b.normal().center()
        b.left()

        # ── CUT ────────────────────────────────────────────────────────
        b.cut()
        return b.build()

    @staticmethod
    def _fmt_money_fixed(val: float, width: int) -> str:
        """
        Format a number to fit a fixed-width column (right-aligned).
        Falls back to less verbose formats if the amount is too long.
        """
        try:
            s = f"{float(val):,.2f}"
        except Exception:
            s = str(val)
        if len(s) > width:
            # remove commas
            s = s.replace(",", "")
        if len(s) > width:
            # drop decimals
            try:
                s = f"{float(val):.0f}"
            except Exception:
                s = s[:width]
        if len(s) > width:
            s = s[-width:]
        return s.rjust(width)

    @staticmethod
    def _fmt_price_x_qty(price: float, qty: int, width: int) -> str:
        """
        Format "price xqty" to a fixed-width column, right-aligned.
        Example: "650.00 x2"
        """
        try:
            q = int(qty or 0)
        except Exception:
            q = 0
        try:
            p = float(price or 0)
        except Exception:
            p = 0.0

        # Prefer 2 decimals
        base = f"{p:,.2f} x{max(1, q)}" if q else f"{p:,.2f}"
        if len(base) > width:
            base = base.replace(",", "")
        if len(base) > width:
            # Drop decimals if still too long
            base = f"{p:.0f} x{max(1, q)}" if q else f"{p:.0f}"
        if len(base) > width:
            base = base[-width:]
        return base.rjust(width)

    @staticmethod
    def _fmt_xqty_fixed(qty: int, width: int) -> str:
        try:
            q = int(qty or 0)
        except Exception:
            q = 0
        s = f"x{max(1, q)}" if q else "x1"
        if len(s) > width:
            s = s[-width:]
        return s.rjust(width)

    @staticmethod
    def _parse_sale_datetime(ts_raw: Any) -> datetime:
        """
        Parse the sale timestamp from DB/app. Falls back to local now().
        DB may store 'YYYY-MM-DD HH:MM:SS' (SQLite) or ISO strings.
        """
        if not ts_raw:
            return datetime.now()
        try:
            s = str(ts_raw).strip()
            # Trim if string has extra fractional seconds or timezone suffix.
            s = s.replace("T", " ")
            if s.endswith("Z"):
                s = s[:-1]
            s = s.split(".")[0]
            # Try common sqlite formats.
            try:
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            try:
                return datetime.strptime(s, "%Y-%m-%d %H:%M")
            except ValueError:
                pass
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.now()

    @staticmethod
    def _escpos_item(b: ESCPOSBuilder, item: Dict[str, Any], layout: Dict[str, int]):
        W, COL_ITEM = layout["W"], layout["COL_ITEM"]
        COL_PRICE, COL_XQTY, COL_TOTAL = layout["COL_PRICE"], layout["COL_XQTY"], layout["COL_TOTAL"]
        """Append one item (with word-wrap) to the ESC/POS builder."""
        name  = str(item.get("product_name", "Item"))
        qty   = item.get("qty", 1)
        price = float(item.get("price_at_sale", 0))
        total = qty * price

        parts   = textwrap.wrap(name, width=COL_ITEM) or [name[:COL_ITEM]]
        # Fixed-width numeric columns so PRICE/TOTAL align perfectly.
        p_str = PrinterService._fmt_money_fixed(price, COL_PRICE)
        q_str = PrinterService._fmt_xqty_fixed(int(qty or 0), COL_XQTY)
        t_str = PrinterService._fmt_money_fixed(total, COL_TOTAL)
        first = (f"{parts[0]:<{COL_ITEM}} {p_str} {q_str} {t_str}")
        b.line(first[:W])
        for extra in parts[1:]:
            b.line(f"{extra}"[:W])

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
        COL_ITEM, COL_PRICE, COL_XQTY, COL_TOTAL = (
            layout["COL_ITEM"],
            layout["COL_PRICE"],
            layout["COL_XQTY"],
            layout["COL_TOTAL"],
        )
        cur = cfg['currency']
        ln: List[str] = []

        div_eq   = '=' * W
        div_dash = '-' * W
        ctr = lambda s: s.center(W).rstrip()

        # ── header ──
        ln.append(div_eq)
        ln.append(ctr(f"** {cfg['name'].upper()} **"))
        ln.append(div_eq)
        rno = sale_data.get('receipt_no', 'N/A')
        sale_dt = self._parse_sale_datetime(sale_data.get('timestamp'))
        ts = sale_dt.strftime('%Y-%m-%d %H:%M:%S')
        cas = sale_data.get('cashier', 'Staff')

        short_code = str(rno).split("-")[-1].strip() or str(rno)
        bill_lbl = f"BILL #{short_code}"
        gap = max(W - len(bill_lbl) - len(ts), 1)
        ln.append(f"{bill_lbl}{' ' * gap}{ts}"[:W])
        ln.append(f"Cashier: {cas}"[:W])
        ln.append(div_dash)

        # ── column header ──
        hdr = (
            f"{'ITEM':<{COL_ITEM}} "
            f"{'PRICE':>{COL_PRICE}} "
            f"{'xQTY':>{COL_XQTY}} "
            f"{'TOTAL':>{COL_TOTAL}}"
        )
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
            sign = str(prefix or "")
            if sign and not sign.endswith(" "):
                sign += " "
            amt = f"{sign}{cur} {val:,.2f}"
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
        ln.append(f"{('PAID BY: ' + pay).rjust(W)}"[:W])

        tendered = sale_data.get('amount_tendered', 0)
        change   = sale_data.get('change', 0)
        if pay == 'CASH' and tendered > 0:
            ln.append(_row("Tendered", tendered))
            ln.append(_row("Change", change))

        # ── footer ──
        address = str(cfg.get('address') or '').strip()
        thanks_lines = (cfg.get('footer') or "Thanks for shopping!").strip().splitlines()
        thanks_msg = (thanks_lines[0] if thanks_lines else "Thanks for shopping!").strip() or "Thanks for shopping!"

        # Always 2 lines: thanks then address (more readable)
        ln.append(div_dash)
        ln.append(ctr(thanks_msg))
        if address:
            ln.append(ctr(address))
        if cfg.get('qr_text'):
            ln.append('')
            caption = str(cfg.get('qr_caption') or '').strip()
            if caption:
                ln.append(ctr(caption))
            ln.append(ctr(str(cfg['qr_text'])))
        ln.append(div_dash)

        # feed
        ln.extend([''] * FEED_LINES)
        return '\n'.join(ln)

    @staticmethod
    def _text_item(ln: List[str], item: Dict[str, Any], layout: Dict[str, int]):
        W, COL_ITEM = layout["W"], layout["COL_ITEM"]
        COL_PRICE, COL_XQTY, COL_TOTAL = layout["COL_PRICE"], layout["COL_XQTY"], layout["COL_TOTAL"]
        name  = str(item.get("product_name", "Item"))
        qty   = item.get("qty", 1)
        price = float(item.get("price_at_sale", 0))
        total = qty * price

        parts = textwrap.wrap(name, width=COL_ITEM) or [name[:COL_ITEM]]
        p_str = PrinterService._fmt_money_fixed(price, COL_PRICE)
        q_str = PrinterService._fmt_xqty_fixed(int(qty or 0), COL_XQTY)
        t_s = PrinterService._fmt_money_fixed(total, COL_TOTAL)
        first = (f"{parts[0]:<{COL_ITEM}} {p_str} {q_str} {t_s}")
        ln.append(first[:W])
        for extra in parts[1:]:
            ln.append(f"{extra}"[:W])

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
