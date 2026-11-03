"""V4 semantic palette shared by both desktop applications."""
TOKENS = dict(background='#111418', surface='#191e25', raised='#222a34',
              border='#303946', text='#e9eef5', muted='#a2adbd', accent='#5797ff',
              primary='#5797ff', success='#63c9a7', warning='#e6b76c', danger='#ec8390')
STYLE = r'''
QWidget { background: %(background)s; color: %(text)s; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QLabel { background: transparent; }
QLabel#muted, QLabel#hint, QLabel#streamMeta { color: %(muted)s; }
QLabel#title { font-size: 18px; font-weight: 600; }
QLabel#value, QLabel#tileTitle { font-size: 14px; font-weight: 600; }
QLabel#badge { color: %(accent)s; padding: 3px 8px; }
QWidget#panel, QFrame#card, QFrame#viewTile, QFrame#arrangeCard { background: %(surface)s; border: 1px solid %(border)s; border-radius: 6px; }
QWidget#panel QLabel, QFrame#card QLabel, QFrame#viewTile QLabel, QFrame#arrangeCard QLabel { background: transparent; }
QPushButton, QToolButton { background: %(raised)s; border: 1px solid %(border)s; border-radius: 5px; padding: 5px 9px; min-height: 21px; }
QPushButton:hover, QToolButton:hover { background: #2b3643; border-color: #53647b; }
QPushButton:pressed, QToolButton:pressed { background: #263e5b; }
QPushButton:focus, QToolButton:focus { border-color: %(accent)s; }
QPushButton:disabled, QToolButton:disabled { color: #7e8997; background: #1b2028; border-color: #303946; }
QPushButton#primary { background: %(primary)s; color: #101b2b; border-color: %(primary)s; font-weight: 600; }
QPushButton#primary:hover { background: #79acff; }
QPushButton#primary:disabled { background: #293b55; color: #9ba9bd; border-color: #394b63; }
QPushButton#ghost, QPushButton#iconButton { background: transparent; border-color: transparent; }
QPushButton#danger { background: #40252d; color: #ffb1bc; border-color: #7b424e; }
QPushButton:checked, QToolButton:checked { color: #c5ddff; background: #223b60; border-color: #4874ad; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #13181e; border: 1px solid %(border)s; border-radius: 5px; padding: 5px 7px; min-height: 21px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: %(accent)s; }
QDoubleSpinBox[dirty="true"], QComboBox[dirty="true"] { border-color: %(warning)s; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { color: #7e8997; }
QComboBox QAbstractItemView { background: %(surface)s; selection-background-color: #263c56; }
QPlainTextEdit, QTableWidget, QTreeWidget, QListWidget { background: %(surface)s; border: 0; alternate-background-color: #1e252e; selection-background-color: #263c56; }
QPlainTextEdit { padding: 8px; color: %(muted)s; }
QTreeWidget::item { padding: 7px 2px; }
QTreeWidget::item:selected { background: #263c56; }
QTableWidget::item { padding: 6px; border: 0; }
QTableWidget::item:selected { background: #263c56; color: %(text)s; }
QHeaderView::section { background: #171d24; color: %(muted)s; padding: 9px; border: 0; }
QTabWidget::pane { border: 0; }
QTabBar::tab { color: %(muted)s; background: transparent; padding: 7px 11px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(text)s; border-bottom-color: %(accent)s; }
QTabBar::tab:hover { background: %(raised)s; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; }
QScrollBar::handle:vertical { background: #4c5868; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSplitter::handle { background: #232b35; width: 5px; height: 5px; }
QSplitter::handle:hover { background: #4874ad; }
QStatusBar { background: #15191f; color: %(muted)s; border-top: 1px solid %(border)s; font-size: 12px; }
QMenu { background: %(surface)s; border: 1px solid %(border)s; padding: 4px; }
QMenu::item { padding: 7px 18px; }
QMenu::item:selected { background: #263c56; }
QToolTip { background: %(raised)s; color: %(text)s; border: 1px solid %(border)s; padding: 6px; }
QGroupBox { border: 1px solid %(border)s; border-radius: 6px; margin-top: 12px; padding-top: 14px; }
QGroupBox::title { color: %(muted)s; subcontrol-origin: margin; left: 9px; }
QWidget#appRoot { background: %(background)s; }
QLabel#brandMark { background: %(accent)s; color: #142036; border-radius: 7px; font-size: 23px; font-weight: 600; }
QLabel#brand { font-family: "Segoe UI"; font-size: 20px; font-weight: 600; letter-spacing: 2px; }
QLabel#brandSub { color: %(muted)s; font-size: 10px; letter-spacing: 1px; }
QLabel#section { color: %(muted)s; font-size: 12px; font-weight: 600; padding-top: 4px; padding-bottom: 2px; }
QLabel#telemetry { background: #171e26; color: #bdcddd; border: 1px solid %(border)s; border-radius: 5px; padding: 6px; font-size: 12px; }
QLabel#streamMeta { font-size: 12px; padding: 2px 0; }
QLabel#channel { color: #a8caff; padding: 2px 3px; font-size: 11px; font-weight: 600; }
QWidget#controlBody, QWidget#sensorPage, QWidget#sensorFooter, QWidget#sensorShell { background: %(surface)s; }
QPushButton#direction { background: #202a38; min-height: 25px; }
QPushButton#direction:pressed { background: %(accent)s; color: #101b2b; }
QFrame#arrangeFooter { background: #192433; border: 1px solid #354c68; border-radius: 6px; }
QDockWidget { font-weight: 600; }
QDockWidget::title { background: #202a36; padding: 9px; }
QWidget#navigation { background: #15191f; border-right: 1px solid %(border)s; }
QToolButton#navButton { border: 0; background: transparent; color: %(muted)s; padding: 8px 2px; }
QToolButton#navButton:checked { background: #22344c; color: #c5ddff; }
QFrame#sessionBar { background: #1a232d; border-bottom: 1px solid %(border)s; }
QLabel#ownershipBar { background: #191e25; border: 1px solid %(border)s; border-radius: 4px; padding: 7px 10px; color: #bdcddd; font-size: 12px; }
QFrame#machineSummary { background: transparent; border-top: 1px solid %(border)s; }
QLabel#warningText { color: %(warning)s; }
QToolButton#foldHeader { text-align: left; background: transparent; border: 0; border-top: 1px solid %(border)s; padding: 7px 2px; }
QPushButton#imageTool { padding: 2px 6px; min-height: 19px; background: transparent; border-color: transparent; font-size: 12px; }
QPushButton#imageTool:hover { background: #263c56; }
''' % TOKENS
