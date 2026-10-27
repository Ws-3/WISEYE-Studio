"""Small reusable controls; changes never cause hidden network requests."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QComboBox, QScrollArea


class NumberInput(QDoubleSpinBox):
    def __init__(self, low, high, unit='', decimals=2, step=1., parent=None):
        super().__init__(parent)
        self.setRange(low, high)
        self.setDecimals(decimals)
        self.setSingleStep(step)
        self.setKeyboardTracking(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if unit:
            self.setSuffix(' ' + unit)
        self.setToolTip(f'允许范围：{low:g}–{high:g} {unit}'.rstrip())

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class ChoiceInput(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


def scroll(widget):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area
