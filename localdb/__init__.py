"""Chinese translations for the BlendRaw addon.

The translation tables are registered as two independent Blender translation
contexts (``zh_CN`` and ``zh_HANS``) because Blender 4.0+ uses ``zh_HANS`` for
Simplified Chinese while older builds use ``zh_CN``.
"""

import bpy

from . import zh_CN

__all__ = ["register", "unregister"]


class TranslationHelper:
    def __init__(self, name: str, data: dict, lang: str = "zh_CN"):
        self.name = name
        self.translations_dict = {}
        for src, dst in data.items():
            for context in ("Operator", "*"):
                self.translations_dict.setdefault(lang, {})[(context, src)] = dst

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except ValueError:
            # Already registered (e.g. addon reloaded without a full restart).
            pass

    def unregister(self):
        try:
            bpy.app.translations.unregister(self.name)
        except ValueError:
            pass


_translators = (
    TranslationHelper("BRaw_zh_CN", zh_CN.data),
    TranslationHelper("BRaw_zh_HANS", zh_CN.data, lang="zh_HANS"),
)


def register():
    for translator in _translators:
        translator.register()


def unregister():
    for translator in _translators:
        translator.unregister()
