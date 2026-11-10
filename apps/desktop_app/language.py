"""Live, reversible translation of the existing Qt presentation layer.

No windows are rebuilt and no application commands are emitted when switching.
Editable text and user-provided names are deliberately excluded.
"""
import weakref
from PySide6.QtCore import QObject, QTimer, Signal, QSettings, QSignalBlocker, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QAbstractButton,
    QGroupBox, QDockWidget, QComboBox, QTabBar, QLineEdit, QAbstractSpinBox,
    QListWidget, QTreeWidget, QTableWidget, QStatusBar)
from core.localization import LANGUAGES, tr, set_language, language

_active_manager = None
_setters_installed = False


def _install_setters():
    """Translate rapidly updated telemetry when it is written, without polling lag."""
    global _setters_installed
    if _setters_installed:return
    _setters_installed=True
    for cls, method, key in [(QLabel,'setText','text'),(QAbstractButton,'setText','text'),
            (QAction,'setText','text'),(QGroupBox,'setTitle','title'),
            (QWidget,'setWindowTitle','windowTitle'),(QWidget,'setToolTip','toolTip'),
            (QWidget,'setStatusTip','statusTip'),(QWidget,'setWhatsThis','whatsThis'),
            (QWidget,'setAccessibleName','accessibleName'),(QLineEdit,'setPlaceholderText','placeholder')]:
        original=getattr(cls,method)
        def write(obj,text,_original=original,_key=key):
            control=_active_manager
            if control is None or control.translating or obj.property('noTranslate'):
                return _original(obj,text)
            sources=getattr(obj,'_wiseye_sources',None)
            if sources is None:sources={};obj._wiseye_sources=sources
            previous=sources.get(_key)
            source=previous[0] if previous and text==previous[1] else text
            rendered=tr(source)
            sources[_key]=(source,rendered)
            return _original(obj,rendered)
        setattr(cls,method,write)


class LanguageManager(QObject):
    changed = Signal(str)

    def __init__(self, app):
        global _active_manager
        super().__init__(app)
        self.translating=False
        _active_manager=self
        _install_setters()
        self.settings = QSettings('WISEYE', 'Language')
        code = self.settings.value('language', 'zh_CN')
        set_language(code if code in dict(LANGUAGES) else 'zh_CN')
        self.roots = weakref.WeakSet()
        self.cache = {}
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def select(self, code):
        set_language(code)
        self.settings.setValue('language', code)
        self.settings.sync()
        self.refresh()
        self.changed.emit(code)

    def register(self, root):
        self.roots.add(root)
        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        self.settings.sync()
        code = self.settings.value('language', 'zh_CN')
        if code in dict(LANGUAGES) and code != language():
            set_language(code)
            self.changed.emit(code)
        seen = set()

        def apply(obj, key, get, put):
            identity = (id(obj), key)
            seen.add(identity)
            current = get()
            if not isinstance(current, str) or not current:
                return
            previous = self.cache.get(identity)
            written=getattr(obj,'_wiseye_sources',{}).get(key)
            source = written[0] if written and current==written[1] else previous[0] if previous and current == previous[1] else current
            rendered = tr(source)
            self.cache[identity] = (source, rendered)
            if rendered != current:
                self.translating=True
                try:put(rendered)
                finally:self.translating=False

        roots = list(QApplication.topLevelWidgets())
        for root in roots:
            # Only touch registered application windows and their transient UI.
            ancestor = root
            while ancestor.parentWidget() is not None:
                ancestor = ancestor.parentWidget()
            if ancestor not in self.roots and root not in self.roots:
                continue
            for obj in [root, *root.findChildren(QWidget), *root.findChildren(QAction)]:
                if obj.property('noTranslate'):
                    continue
                blocker = QSignalBlocker(obj)
                for key in ('toolTip', 'statusTip', 'whatsThis', 'accessibleName'):
                    if hasattr(obj, key):
                        apply(obj, key, getattr(obj, key), getattr(obj, 'set'+key[0].upper()+key[1:]))
                if isinstance(obj, (QLabel, QAbstractButton, QAction)):
                    apply(obj, 'text', obj.text, obj.setText)
                if isinstance(obj,QStatusBar):
                    apply(obj,'message',obj.currentMessage,obj.showMessage)
                if isinstance(obj, QGroupBox):
                    apply(obj, 'title', obj.title, obj.setTitle)
                if obj is root or isinstance(obj, QDockWidget):
                    apply(obj, 'windowTitle', obj.windowTitle, obj.setWindowTitle)
                if isinstance(obj, QLineEdit) and not isinstance(obj.parentWidget(), QAbstractSpinBox):
                    apply(obj, 'placeholder', obj.placeholderText, obj.setPlaceholderText)
                if isinstance(obj, (QComboBox, QTabBar)):
                    for i in range(obj.count()):
                        get = obj.itemText if isinstance(obj, QComboBox) else obj.tabText
                        put = obj.setItemText if isinstance(obj, QComboBox) else obj.setTabText
                        apply(obj, ('item', i), lambda i=i:get(i), lambda value,i=i:put(i,value))
                if isinstance(obj, QListWidget):
                    for i in range(obj.count()):
                        item = obj.item(i)
                        apply(item, 'text', item.text, item.setText)
                if isinstance(obj, QTableWidget):
                    for i in range(obj.columnCount()):
                        item = obj.horizontalHeaderItem(i)
                        if item:apply(item, 'header', item.text, item.setText)
                if isinstance(obj,QTreeWidget):
                    pending=[obj.topLevelItem(i) for i in range(obj.topLevelItemCount())]
                    while pending:
                        item=pending.pop()
                        for column in range(obj.columnCount()):
                            apply(item,('tree',column),lambda c=column:item.text(c),lambda value,c=column:item.setText(c,value))
                        pending.extend(item.child(i) for i in range(item.childCount()))
                # Numeric fields, device names, table contents, logs, raw protocol
                # diagnostics and trees containing user names are never rewritten.
                del blocker
            root.update()
        self.cache = {k:v for k,v in self.cache.items() if k in seen}


def manager():
    app = QApplication.instance()
    if not hasattr(app, '_wiseye_language'):
        app._wiseye_language = LanguageManager(app)
    return app._wiseye_language


def language_selector(parent=None):
    box = QComboBox(parent)
    box.setObjectName('languageSelector')
    box.setProperty('noTranslate', True)
    for code, name in LANGUAGES:
        box.addItem(name, code)
    box.setCurrentIndex(box.findData(language()))
    control = manager()
    box.activated.connect(lambda _: control.select(box.currentData()))
    def sync(code):
        blocker = QSignalBlocker(box)
        box.setCurrentIndex(box.findData(code))
        del blocker
    control.changed.connect(sync)
    return box
