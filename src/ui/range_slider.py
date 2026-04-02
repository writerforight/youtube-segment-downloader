from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget


class DualRangeSlider(QWidget):
    values_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(46)
        self.setMouseTracking(True)
        self._minimum = 0
        self._maximum = 100
        self._left_value = 0
        self._right_value = 100
        self._active_handle: str | None = None
        self._handle_radius = 9
        self._track_height = 6

    def minimum(self) -> int:
        return self._minimum

    def maximum(self) -> int:
        return self._maximum

    def left_value(self) -> int:
        return self._left_value

    def right_value(self) -> int:
        return self._right_value

    def set_range(self, minimum: int, maximum: int) -> None:
        self._minimum = minimum
        self._maximum = max(minimum, maximum)
        self._left_value = max(self._minimum, min(self._left_value, self._maximum))
        self._right_value = max(self._left_value, min(self._right_value, self._maximum))
        self.update()
        self.values_changed.emit(self._left_value, self._right_value)

    def set_values(self, left: int, right: int) -> None:
        left = max(self._minimum, min(left, self._maximum))
        right = max(left, min(right, self._maximum))
        changed = left != self._left_value or right != self._right_value
        self._left_value = left
        self._right_value = right
        self.update()
        if changed:
            self.values_changed.emit(left, right)

    def _track_rect(self) -> QRect:
        margin = self._handle_radius + 6
        y = self.height() // 2 - self._track_height // 2
        return QRect(margin, y, self.width() - 2 * margin, self._track_height)

    def _value_to_pos(self, value: int) -> int:
        track = self._track_rect()
        if self._maximum == self._minimum:
            return track.left()
        ratio = (value - self._minimum) / (self._maximum - self._minimum)
        return int(track.left() + ratio * track.width())

    def _pos_to_value(self, x: int) -> int:
        track = self._track_rect()
        x = max(track.left(), min(x, track.right()))
        if track.width() <= 0 or self._maximum == self._minimum:
            return self._minimum
        ratio = (x - track.left()) / track.width()
        return int(round(self._minimum + ratio * (self._maximum - self._minimum)))

    def _left_handle_rect(self) -> QRect:
        x = self._value_to_pos(self._left_value)
        y = self.height() // 2
        r = self._handle_radius
        return QRect(x - r, y - r, 2 * r, 2 * r)

    def _right_handle_rect(self) -> QRect:
        x = self._value_to_pos(self._right_value)
        y = self.height() // 2
        r = self._handle_radius
        return QRect(x - r, y - r, 2 * r, 2 * r)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        track = self._track_rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2a2f3a"))
        painter.drawRoundedRect(track, 3, 3)

        left_x = self._value_to_pos(self._left_value)
        right_x = self._value_to_pos(self._right_value)
        selected = QRect(left_x, track.top(), max(1, right_x - left_x), track.height())
        painter.setBrush(QColor("#4f8cff"))
        painter.drawRoundedRect(selected, 3, 3)

        for handle_rect in (self._left_handle_rect(), self._right_handle_rect()):
            painter.setBrush(QColor("#f5f7fb"))
            painter.setPen(QPen(QColor("#8ea6d9"), 1))
            painter.drawEllipse(handle_rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()
        if self._left_handle_rect().contains(pos):
            self._active_handle = "left"
        elif self._right_handle_rect().contains(pos):
            self._active_handle = "right"
        else:
            left_dist = abs(pos.x() - self._value_to_pos(self._left_value))
            right_dist = abs(pos.x() - self._value_to_pos(self._right_value))
            self._active_handle = "left" if left_dist <= right_dist else "right"
            self._move_active_handle(pos)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._active_handle is not None:
            self._move_active_handle(event.position().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._active_handle = None
        self.update()

    def _move_active_handle(self, pos: QPoint) -> None:
        value = self._pos_to_value(pos.x())
        if self._active_handle == "left":
            self.set_values(value, self._right_value)
        elif self._active_handle == "right":
            self.set_values(self._left_value, value)
