from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_shadow(
    widget: QWidget,
    *,
    blur_radius: int = 28,
    x_offset: int = 0,
    y_offset: int = 10,
    color: QColor | None = None,
) -> None:
    """
    Apply a subtle drop shadow to a widget.

    Note: This is purely visual and can be skipped for very large/complex UIs
    if performance becomes a concern.
    """
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(x_offset, y_offset)
    shadow.setColor(color or QColor(0, 0, 0, 110))
    widget.setGraphicsEffect(shadow)

