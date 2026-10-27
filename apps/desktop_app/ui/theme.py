"""Semantic colour tokens and a single desktop stylesheet."""
TOKENS = dict(background='#101216', surface='#191d24', raised='#242a34',
              border='#343d4b', text='#edf2fa', muted='#9ba9bd', accent='#69a7ff',
              primary='#326de6', success='#76d6a0', warning='#f3c66a', danger='#ff9292')

STYLE = '''
QWidget { background: %(background)s; color: %(text)s; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QLabel { background: transparent; }
QLabel#muted, QLabel#hint { color: %(muted)s; }
QLabel#title { font-size: 19px; font-weight: 600; }
QLabel#value { font-size: 15px; font-weight: 600; }
QLabel#badge { color: %(accent)s; padding: 4px 10px; }
QFrame#card, QWidget#panel, QFrame#viewTile { background: %(surface)s; border: 0; border-radius: 6px; }
QWidget#panel QLabel, QFrame#card QLabel, QFrame#viewTile QLabel { background: transparent; }
QPushButton, QToolButton { background: %(raised)s; border: 1px solid %(border)s;
    border-radius: 7px; padding: 6px 10px; min-height: 22px; }
QPushButton:hover, QToolButton:hover { background: #363c46; border-color: %(accent)s; }
QPushButton:pressed, QToolButton:pressed { background: #303e54; }
QPushButton:focus, QToolButton:focus { border: 1px solid %(accent)s; }
QPushButton:disabled, QToolButton:disabled { color: #949daa; background: #25292f; border-color: #383e48; }
QPushButton#primary { background: %(primary)s; border-color: %(primary)s; color: #ffffff; }
QPushButton#primary:hover { background: #306ed5; }
QPushButton#primary:disabled { background: #293c5e; color: #a3afc2; border-color: #3c4c64; }
QPushButton#ghost { background: transparent; border-color: transparent; }
QPushButton#danger { color: %(danger)s; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: %(raised)s;
    border: 1px solid %(border)s; border-radius: 5px; padding: 5px 7px; min-height: 22px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: %(accent)s; }
QDoubleSpinBox[dirty="true"], QComboBox[dirty="true"] { border-color: %(accent)s; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { color: #949daa; }
QComboBox QAbstractItemView { background: %(surface)s; selection-background-color: #30486d; }
QPlainTextEdit, QTableWidget, QTreeWidget { background: %(surface)s; border: 0; border-radius: 5px;
    alternate-background-color: #24282f; selection-background-color: #30486d; }
QPlainTextEdit { padding: 8px; color: %(muted)s; }
QTreeWidget::item { padding: 8px 2px; }
QTreeWidget::item:selected { background: #30486d; }
QHeaderView::section { background: %(surface)s; color: %(muted)s; padding: 8px; border: 0; }
QTabWidget::pane { border: 0; }
QTabBar::tab { color: %(muted)s; background: transparent; padding: 8px 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(text)s; border-bottom: 2px solid %(accent)s; }
QTabBar::tab:hover { background: %(raised)s; }
QTabBar::tab:disabled { color: #949daa; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #4e5663; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: %(background)s; width: 6px; height: 6px; }
QStatusBar { background: %(surface)s; color: %(muted)s; }
QMenu { background: %(surface)s; border: 1px solid %(border)s; padding: 5px; }
QMenu::item { padding: 7px 18px; }
QMenu::item:selected { background: #30486d; }
QToolTip { background: %(raised)s; color: %(text)s; border: 1px solid %(border)s; padding: 6px; }
QGroupBox { border: 1px solid %(border)s; border-radius: 6px; margin-top: 14px; padding-top: 16px; }
QGroupBox::title { color: %(muted)s; subcontrol-origin: margin; left: 10px; }
''' % TOKENS

STYLE += """
QWidget#appRoot { background: #101216; }
QLabel#brandMark { background: #326de6; color: white; border-radius: 10px; font-size: 24px; font-weight: 700; }
QLabel#brand { font-family: "Segoe UI"; font-size: 23px; font-weight: 700; letter-spacing: 2px; }
QLabel#brandSub { color: #7f90a8; font-size: 10px; letter-spacing: 2px; }
QLabel#section { color: #7796bd; font-size: 11px; font-weight: 600; padding-top: 8px; padding-bottom: 3px; }
QLabel#telemetry { background: #141922; color: #b9cde6; border: 1px solid #293343; border-radius: 7px; padding: 8px; font-size: 12px; }
QLabel#tileTitle { color: #e1e9f6; font-weight: 600; }
QLabel#streamMeta { color: #8092aa; font-family: "Segoe UI"; font-size: 11px; padding: 3px 0px; }
QLabel#channel { color: #8dbaff; background: #25374e; border-radius: 4px; padding: 3px 5px; font-size: 10px; font-weight: 700; }
QWidget#panel { background: #191d24; border: 1px solid #2a323e; border-radius: 10px; }
QFrame#viewTile { background: #191f29; border: 1px solid #303c4d; border-radius: 10px; }
QFrame#viewTile:hover { border-color: #557ba9; }
QWidget#controlBody { background: #191d24; }
QTabWidget#mainPages > QTabBar::tab { padding: 11px 22px; margin-right: 6px; border-radius: 7px; border-bottom: 0; color: #91a1b7; }
QTabWidget#mainPages > QTabBar::tab:selected { background: #233750; color: #a7ceff; }
QTabWidget#inspectors > QTabBar::tab { padding: 9px 12px; }
QPushButton#direction { background: #202a38; border: 1px solid #344458; min-height: 30px; color: #b8cdeb; }
QPushButton#direction:hover { background: #2c4261; border-color: #69a7ff; }
QPushButton#direction:pressed { background: #326de6; color: white; }
QPushButton#direction:disabled { color: #6e7b8d; background: #1d2430; border-color: #2b3442; }
QPushButton#iconButton { background: transparent; border: 0; padding: 3px; }
QPushButton#iconButton:hover { background: #2d4059; }
QWidget#sensorPage, QWidget#sensorFooter, QWidget#sensorShell { background: #191d24; }
QLabel#hint { font-size: 11px; color: #8190a5; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QStatusBar { border-top: 1px solid #28303c; font-size: 11px; }
QSplitter::handle:hover { background: #39577c; }
"""

STYLE += """
QFrame#arrangeCard { background: #191d24; border: 1px solid #303948; border-radius: 12px; }
QFrame#arrangeCard QWidget { background: transparent; }
QFrame#arrangeCard QLineEdit, QFrame#arrangeCard QComboBox, QFrame#arrangeCard QDoubleSpinBox { background: #232b37; }
QFrame#arrangeCard QPushButton { background: #283343; }
QFrame#arrangeCard QPushButton:hover { background: #344861; }
QFrame#arrangeCard QPushButton:disabled { background: #202630; color: #738197; }
QFrame#arrangeFooter { background: #1b2431; border: 1px solid #35465e; border-radius: 10px; }
"""

STYLE += """
QFrame#arrangeCard QPushButton#primary { background: #326de6; border-color: #326de6; color: white; }
QFrame#arrangeCard QPushButton#primary:disabled { background: #293c5e; color: #a3afc2; }
QFrame#arrangeCard QSpinBox { background: #232b37; }
"""
