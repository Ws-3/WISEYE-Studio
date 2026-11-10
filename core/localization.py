"""Presentation translations. Wire values, paths and user input stay untouched."""
import json
import re
from functools import lru_cache
from pathlib import Path

LANGUAGES = (('zh_CN', '简体中文'), ('en_US', 'English'))
_language = 'zh_CN'


def language():
    return _language


def set_language(value):
    global _language
    if value not in dict(LANGUAGES):
        raise ValueError('Unsupported language')
    _language = value


@lru_cache(maxsize=1)
def catalog():
    from core.runtime_paths import RESOURCE_ROOT
    return json.loads((RESOURCE_ROOT / 'configs/locales/en_US.json').read_text(encoding='utf-8'))


def tr(text, locale=None):
    if not isinstance(text, str) or (locale or _language) == 'zh_CN':
        return text
    translations = catalog()
    if text in translations:
        return translations[text]
    # Split UI sentences around dynamic numbers/IDs while preserving whitespace,
    # punctuation, units, URLs and values. Unknown diagnostics retain their source.
    return re.sub(r'[\u3400-\u9fff]+', lambda m: translations.get(m[0], m[0]), text)
