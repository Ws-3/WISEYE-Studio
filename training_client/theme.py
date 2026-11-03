"""Reuse the simulator theme, with a bundled copy for standalone deployment."""
try:
    from apps.desktop_app.ui.theme import TOKENS, STYLE
except ModuleNotFoundError:
    from ._theme import TOKENS, STYLE
