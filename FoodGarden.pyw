import sys
import traceback


def _hide_console_window() -> None:
    try:
        if not sys.platform.startswith("win"):
            return
        import ctypes  # type: ignore

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def _show_startup_error(message: str) -> None:
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "Food Garden - Startup Error", message)
        app.quit()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        _hide_console_window()
        from main import main

        main()
    except Exception as e:
        _show_startup_error(f"{e}\n\n{traceback.format_exc()}")
        sys.exit(1)
