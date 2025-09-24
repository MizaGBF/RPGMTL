from __future__ import annotations
from . import TranslatorPlugin
try:
    from deep_translator import GoogleTranslator
except:
    raise Exception("Failed to import deep-translator.\nMake sure it's installed using: pip install -U deep-translator")
from typing import Any

class TLGoogle(TranslatorPlugin):
    def __init__(self : TLGoogle) -> None:
        super().__init__()
        self.name : str = "TL Google"
        self.description : str = " v1.2\nWrapper around the deep-translator module\nGoogle Translator is used"
        self.related_tool_plugins : list[str] = [self.name]
        self.instance = None
        self.past_setting = None

    def get_setting_infos(self : TLGoogle) -> dict[str, list]:
        supported_languages : list[str] = GoogleTranslator().get_supported_languages()
        return {
            "tl_google_src_language": ["Select the Source Language", "str", "auto", ["auto"] + supported_languages],
            "tl_google_target_language": ["Select the Target Language", "str", "english", supported_languages]
        }

    def _init_translator(self : TLGoogle, settings : dict[str, Any]) -> None:
        current = (settings["tl_google_src_language"], settings["tl_google_target_language"])
        if current != self.past_setting or self.instance is None:
            self.instance = GoogleTranslator(source=current[0], target=current[1])
            self.past_setting = current

    async def translate(self : TLGoogle, name : str, string : str, settings : dict[str, Any] = {}) -> str|None:
        try:
            self._init_translator(settings)
            return self.instance.translate(string)
        except Exception as e:
            self.owner.log.error("[TL Google] Error in 'translate':\n" + self.owner.trbk(e))
            return None

    async def translate_batch(self : TLGoogle, name : str, strings : list[str], settings : dict[str, Any] = {}) -> list[str|None]:
        try:
            self._init_translator(settings)
            return self.instance.translate_batch(strings)
        except Exception as e:
            self.owner.log.error("[TL Google] Error in 'translate_batch':\n" + self.owner.trbk(e))
            return []