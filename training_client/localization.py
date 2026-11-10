"""Share integrated translation; keep a copied training_client folder runnable."""
try:
    from core.localization import tr
except ModuleNotFoundError:
    def tr(text):return text

class _Standalone:
    def register(self,root):pass

def manager():
    try:
        from apps.desktop_app.language import manager as shared
    except ModuleNotFoundError:return _Standalone()
    return shared()

def language_selector(parent):
    try:
        from apps.desktop_app.language import language_selector as shared
    except ModuleNotFoundError:
        from PySide6.QtWidgets import QLabel
        return QLabel('中文',parent)
    return shared(parent)
