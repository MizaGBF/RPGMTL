from __future__ import annotations
from . import TranslatorPlugin
try:
    import translators
except:
    raise Exception("Failed to import translators.\nMake sure it's installed using: pip install -U translators")
import asyncio
import time
from typing import Any

class TLStandard(TranslatorPlugin):
    SERVICES : list[str] = ["google", "yandex", "bing", "baidu", "alibaba", "tencent", "youdao", "sogou", "deepl", "caiyun", "argos"]
    LANGUAGE_TABLE : dict[str, dict[str, str]] = {
        "english": {"google": "en", "yandex": "en", "bing": "en", "baidu": "en", "alibaba": "en", "tencent": "en", "youdao": "en", "sogou": "en", "deepl": "en", "caiyun": "en", "argos": "en"},
        "chinese": {"google": "zh", "yandex": "zh", "bing": "zh", "baidu": "zh", "alibaba": "zh", "tencent": "zh", "youdao": "zh", "sogou": "zh", "deepl": "zh", "caiyun": "zh", "argos": "zh"},
        "arabic": {"google": "ar", "yandex": "ar", "bing": "ar", "baidu": "ara", "alibaba": "ar", "tencent": "ar", "youdao": "ar", "sogou": "ar", "argos": "ar"},
        "russian": {"google": "ru", "yandex": "ru", "bing": "ru", "baidu": "ru", "alibaba": "ru", "tencent": "ru", "youdao": "ru", "sogou": "ru", "deepl": "ru", "caiyun": "ru", "argos": "ru"},
        "french": {"google": "fr", "yandex": "fr", "bing": "fr", "baidu": "fra", "alibaba": "fr", "tencent": "fr", "youdao": "fr", "sogou": "fr", "deepl": "fr", "caiyun": "fr", "argos": "fr"},
        "german": {"google": "de", "yandex": "de", "bing": "de", "baidu": "de", "tencent": "de", "youdao": "de", "sogou": "de", "deepl": "de", "argos": "de"},
        "spanish": {"google": "es", "yandex": "es", "bing": "es", "baidu": "spa", "alibaba": "es", "tencent": "es", "youdao": "es", "sogou": "es", "deepl": "es", "caiyun": "es", "argos": "es"},
        "portuguese": {"google": "pt", "yandex": "pt", "bing": "pt", "baidu": "pt", "alibaba": "pt", "tencent": "pt", "youdao": "pt", "sogou": "pt", "deepl": "pt", "argos": "pt"},
        "italian": {"google": "it", "yandex": "it", "bing": "it", "baidu": "it", "alibaba": "it", "tencent": "it", "youdao": "it", "sogou": "it", "deepl": "it", "argos": "it"},
        "japanese": {"google": "ja", "yandex": "ja", "bing": "ja", "baidu": "jp", "tencent": "ja", "youdao": "ja", "sogou": "ja", "deepl": "ja", "caiyun": "ja", "argos": "ja"},
        "korean": {"google": "ko", "yandex": "ko", "bing": "ko", "baidu": "kor", "tencent": "ko", "youdao": "ko", "sogou": "ko", "argos": "ko"},
        "greek": {"google": "el", "yandex": "el", "bing": "el", "baidu": "el", "sogou": "el", "deepl": "el"},
        "dutch": {"google": "nl", "yandex": "nl", "bing": "nl", "baidu": "nl", "youdao": "nl", "sogou": "nl", "deepl": "nl"},
        "hindi": {"google": "hi", "yandex": "hi", "bing": "hi", "tencent": "hi", "sogou": "hi", "argos": "hi"},
        "turkish": {"google": "tr", "yandex": "tr", "bing": "tr", "alibaba": "tr", "tencent": "tr", "sogou": "tr", "argos": "tr"},
        "malay": {"google": "ms", "yandex": "ms", "bing": "ms", "tencent": "ms", "sogou": "ms"},
        "thai": {"google": "th", "yandex": "th", "bing": "th", "baidu": "th", "alibaba": "th", "tencent": "th", "sogou": "th"},
        "vietnamese": {"google": "vi", "yandex": "vi", "bing": "vi", "baidu": "vie", "alibaba": "vi", "tencent": "vi", "youdao": "vi", "sogou": "vi", "argos": "vi"},
        "indonesian": {"google": "id", "yandex": "id", "bing": "id", "alibaba": "id", "tencent": "id", "youdao": "id", "sogou": "id", "argos": "id"},
        "hebrew": {"google": "iw", "yandex": "he", "bing": "he", "sogou": "he"},
        "polish": {"google": "pl", "yandex": "pl", "bing": "pl", "baidu": "pl", "sogou": "pl", "deepl": "pl", "argos": "pl"},
        "mongolian": {"google": "mn", "yandex": "mn"},
        "czech": {"google": "cs", "yandex": "cs", "bing": "cs", "baidu": "cs", "sogou": "cs", "deepl": "cs"},
        "hungarian": {"google": "hu", "yandex": "hu", "bing": "hu", "baidu": "hu", "sogou": "hu", "deepl": "hu"},
        "estonian": {"google": "et", "yandex": "et", "bing": "et", "baidu": "est", "sogou": "et", "deepl": "et"},
        "bulgarian": {"google": "bg", "yandex": "bg", "bing": "bg", "baidu": "bul", "sogou": "bg", "deepl": "bg"},
        "danish": {"google": "da", "yandex": "da", "bing": "da", "baidu": "dan", "sogou": "da", "deepl": "da"},
        "finnish": {"google": "fi", "yandex": "fi", "bing": "fi", "baidu": "fin", "sogou": "fi", "deepl": "fi"},
        "romanian": {"google": "ro", "yandex": "ro", "bing": "ro", "baidu": "rom", "sogou": "ro", "deepl": "ro"},
        "swedish": {"google": "sv", "yandex": "sv", "bing": "sv", "baidu": "swe", "sogou": "sv", "deepl": "sv"},
        "slovenian": {"google": "sl", "yandex": "sl", "bing": "sl", "baidu": "slo", "sogou": "sl", "deepl": "sl"},
        "persian/farsi": {"google": "fa", "yandex": "fa", "bing": "fa", "sogou": "fa"},
        "bosnian": {"google": "bs", "yandex": "bs", "bing": "bsLatn", "sogou": "bsLatn"},
        "serbian": {"google": "sr", "yandex": "sr", "bing": "srLatn", "sogou": "srLatn"},
        "fijian": {"bing": "fj", "sogou": "fj"},
        "filipino": {"google": "tl", "yandex": "tl", "bing": "fil", "sogou": "fil"},
        "haitiancreole": {"google": "ht", "yandex": "ht", "bing": "ht", "sogou": "ht"},
        "catalan": {"google": "ca", "yandex": "ca", "bing": "ca", "sogou": "ca"},
        "croatian": {"google": "hr", "yandex": "hr", "bing": "hr", "sogou": "hr"},
        "latvian": {"google": "lv", "yandex": "lv", "bing": "lv", "sogou": "lv", "deepl": "lv"},
        "lithuanian": {"google": "lt", "yandex": "lt", "bing": "lt", "sogou": "lt", "deepl": "lt"},
        "urdu": {"google": "ur", "yandex": "ur", "bing": "ur", "sogou": "ur"},
        "ukrainian": {"google": "uk", "yandex": "uk", "bing": "uk", "sogou": "uk"},
        "welsh": {"google": "cy", "yandex": "cy", "bing": "cy", "sogou": "cy"},
        "tahiti": {"bing": "ty", "sogou": "ty"},
        "tongan": {"bing": "to", "sogou": "to"},
        "swahili": {"google": "sw", "yandex": "sw", "bing": "sw", "sogou": "sw"},
        "samoan": {"google": "sm", "bing": "sm", "sogou": "sm"},
        "slovak": {"google": "sk", "yandex": "sk", "bing": "sk", "sogou": "sk", "deepl": "sk"},
        "afrikaans": {"google": "af", "yandex": "af", "bing": "af", "sogou": "af"},
        "norwegian": {"google": "no", "yandex": "no", "bing": "no", "sogou": "no"},
        "bengali": {"google": "bn", "yandex": "bn", "bing": "bnBD", "sogou": "bn"},
        "malagasy": {"google": "mg", "yandex": "mg", "bing": "mg", "sogou": "mg"},
        "maltese": {"google": "mt", "yandex": "mt", "bing": "mt", "sogou": "mt"},
        "queretarootomi": {"bing": "otq", "sogou": "otq"},
        "klingon/tlhinganhol": {"bing": "tlh", "sogou": "tlh"},
        "gujarati": {"google": "gu", "yandex": "gu", "bing": "gu"},
        "tamil": {"google": "ta", "yandex": "ta", "bing": "ta"},
        "telugu": {"google": "te", "yandex": "te", "bing": "te"},
        "punjabi": {"google": "pa", "yandex": "pa", "bing": "pa"},
        "amharic": {"google": "am", "yandex": "am"},
        "azerbaijani": {"google": "az", "yandex": "az"},
        "bashkir": {"yandex": "ba"},
        "belarusian": {"google": "be", "yandex": "be"},
        "cebuano": {"google": "ceb", "yandex": "ceb"},
        "chuvash": {"yandex": "cv"},
        "esperanto": {"google": "eo", "yandex": "eo"},
        "basque": {"google": "eu", "yandex": "eu"},
        "irish": {"google": "ga", "yandex": "ga", "bing": "ga"},
    }
    
    def __init__(self : TLStandard) -> None:
        super().__init__()
        self.name : str = "TL Standard"
        self.description : str = " v1.0\nWrapper around many translation services."
        self.related_tool_plugins : list[str] = [self.name]
        self.last_tl : dict[str, float] = {}

    def get_setting_infos(self : TLStandard) -> dict[str, list]:
        supported_languages : list[str] = list(self.LANGUAGE_TABLE.keys())
        return {
            "tl_standard_service": ["Select the provider (Google is recommended)", "str", "google", self.SERVICES],
            "tl_standard_src_language": ["Select the Source Language", "str", "auto", ["auto"] + supported_languages],
            "tl_standard_target_language": ["Select the Target Language", "str", "english", supported_languages],
            "tl_standard_rate_limit": ["Input the rate limit (in seconds) between requests (recommended 1 ~ 2)", "num", 1, None],
        }

    def _init_translator(self : TLStandard, settings : dict[str, Any]) -> None:
        translators.preaccelerate_and_speedtest()

    async def translate_text(self : TLStandard, string : str, rate_limit : float|int, service : str, src_l : str, dst_l : str) -> str:
        now : float = time.time()
        last_tl : int|float = self.last_tl.get(service, 0)
        if rate_limit > 0 and now - last_tl < rate_limit:
            await asyncio.sleep(rate_limit - (now - last_tl))
        self.last_tl[service] = time.time()
        return await translators.translate_text(
            string,
            translator=service,
            from_language=src_l,
            to_language=dst_l,
            http_client='aiohttp',
            if_use_async=True,
            if_close_session=False
        )

    def process_settings(self : TLStandard, settings : dict[str, Any] = {}) -> tuple[str, str, str]:
        service : str = settings.get("tl_standard_service", self.SERVICES[0])
        # check source
        src : str = settings.get("tl_standard_src_language", "auto")
        if src != "auto":
            if src not in self.LANGUAGE_TABLE:
                raise Exception(f"Unknown language {src}")
            if service not in self.LANGUAGE_TABLE[src]:
                raise Exception(f"Service {service} doesn't support language {src}")
            src = self.LANGUAGE_TABLE[src][service]
        # check target
        dst : str = settings.get("tl_standard_target_language", "en")
        if dst not in self.LANGUAGE_TABLE:
            raise Exception(f"Unknown language {dst}")
        if service not in self.LANGUAGE_TABLE[dst]:
            raise Exception(f"Service {service} doesn't support language {dst}")
        dst = self.LANGUAGE_TABLE[dst][service]
        return service, src, dst

    async def translate(self : TLStandard, name : str, string : str, settings : dict[str, Any] = {}) -> str|None:
        service, src, dst = self.process_settings(settings)
        try:
            return await self.translate_text(
                string,
                settings["tl_standard_rate_limit"],
                service, src, dst
            )
        except Exception as e:
            self.owner.log.error(f"[TL Standard] Error in 'translate':\n{self.owner.trace(e)}")
            return None

    async def translate_batch(
        self : TLStandard,
        name : str,
        strings : list[str],
        settings : dict[str, Any] = {}
    ) -> tuple[list[str|None], bool]:
        rate_limit : float|int = settings["tl_standard_rate_limit"]
        service, src, dst = self.process_settings(settings)
        result : list[str] = []
        for s in strings:
            try:
                if not self.owner.running:
                    raise Exception()
                result.append(await self.translate_text(s, rate_limit, service, src, dst))
            except:
                result.append(None)
        return result, True