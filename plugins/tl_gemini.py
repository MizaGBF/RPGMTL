from __future__ import annotations
from . import TranslatorPlugin, TranslatorBatchFormat
try:
    from google import genai
except:
    raise Exception("Failed to import google-genai.\nMake sure it's installed using: pip install -U google-genai")
from typing import Any
import json
import re

PROMPT : str = """You are the World's best Video Game Translator.
Your task is to take a JSON object formatted in such manner:
{
    "file":"FILE",
    "number":BATCH_NUMBER,
    "strings":[
        {
            "id":"STRING_ID",
            "parent":"GROUP OF WHICH THIS STRING IS PART OF",
            "source":"ORIGINAL_STRING",
            "translation":"TRANSLATED_STRING"
        },
        {
            "id":"STRING_ID",
            "parent":"GROUP OF WHICH THIS STRING IS PART OF",
            "source":"ORIGINAL_STRING"
        }
    ]
}
The strings are in order of occurence.

To complete your task, you must absolutely do the following:
  1. The User requires that you translate from $SOURCE$ to $TARGET$.
  2. Don't translate strings with an existing translation.
  3. Preserve placeholders (e.g. {playerName}, %VAR%, <tag>), punctuation, and code syntax.
  4. Return a JSON object, containing the STRING_ID of the strings you translated, and the corresponding translation. It's not necessary to indent it.
  5. Do NOT include any comments, explanations, or extra fields. ONLY return the JSON object.
$EXTRA$
Simple Example for Japanese to English:  
Input:
{
    "file":"Game Script.json",
    "number":35,
    "strings":[
        {
            "id":"2-2",
            "parent":"Group 2: Text Box",
            "source":"昨日何をしましたか？"
        },
        {
            "id":"2-1",
            "parent":"Group 2: Text Box",
            "source":"私は昨日、映画を見ました。",
            "translation":"I watched a movie yesterday."
        }
    ]
}
Output:
{
    "2-2":"What did you do yesterday?"
}
    
The batch that you must translate is the following:
$INPUT$

Now waiting your output.
"""
JSON_SANITIZER = re.compile(r'(?P<key>"[^"]*"\s*:\s*)"(?P<content>.*?)"(?P<tail>(?=,|\}))', re.DOTALL)

class TLGemini(TranslatorPlugin):
    def __init__(self : TLGemini) -> None:
        super().__init__()
        self.name : str = "TL Gemini"
        self.description : str = " v0.4\nWrapper around the google-genai module to prompt Gemini. (EXPERIMENTAL)"
        self.instance = None
        self.key_in_use = None

    def get_format(self : TranslatorPlugin) -> TranslatorBatchFormat:
        return TranslatorBatchFormat.CONTEXT

    def get_setting_infos(self : TLGemini) -> dict[str, list]:
        return {
            "gemini_api_key": ["Set the Google Studio API Key", "str", "", None],
            "gemini_model": ["Set the Gemini Model String", "str", "gemini-2.5-pro-exp-03-25", None],
            "gemini_src_language": ["Set the Source Language", "str", "Japanese", None],
            "gemini_target_language": ["Set the Target Language", "str", "English", None],
            "gemini_extra_context": ["Set extra informations or commands for the AI", "str", "", None]
        }

    def _init_translator(self : TLGemini, settings : dict[str, Any]) -> None:
        try:
            if self.key_in_use is not None and settings["gemini_api_key"] == self.key_in_use:
                return
            if self.instance is None:
                current = genai.Client(api_key=settings["gemini_api_key"])
                self.instance = current
                self.key_in_use = settings["gemini_api_key"]
        except Exception as e:
             self.owner.log.error("[TL Gemini] Error in '_init_translator':\n" + self.owner.trbk(e))

    def _sanitize(self : TLGemini, text : str) -> str:
        def _repl(m):
            # re-escape the inner content properly
            escaped = json.dumps(m.group('content'), ensure_ascii=False)
            # json.dumps wraps it in quotes, so just drop the extra quotes
            return "{}{}{}".format(m.group('key'), escaped, m.group('tail'))
        # run the replacement globally
        return JSON_SANITIZER.sub(_repl, bad)

    def parse_model_output(self : TLGemini, text : str) -> dict[str, str]:
        start = text.find("{")
        if start == -1:
            raise Exception("[TL Gemini] Error in 'parse_model_output', failed to find the start of the JSON")
        end = text.rfind("}")
        if start == -1:
            raise Exception("[TL Gemini] Error in 'parse_model_output', failed to find the end of the JSON")
        return json.loads(text[start:end+1])

    async def ask_gemini(self : TLGemini, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        self._init_translator(settings)
        extra_context : str = ""
        if settings["gemini_extra_context"].strip() != "":
            extra_context = "  6. The User also specified the following: {}\n".format(settings["gemini_extra_context"])
        response = self.instance.models.generate_content(
            model=settings["gemini_model"], contents=PROMPT.replace("$TARGET$", settings["gemini_target_language"]).replace("$SOURCE$", settings["gemini_src_language"]).replace("$EXTRA$", extra_context).replace("$INPUT$", json.dumps(batch), 1)
        )
        return self.parse_model_output(response.text)

    async def translate(self : TLGemini, string : str, settings : dict[str, Any] = {}) -> str|None:
        try:
            data = await self.ask_gemini({
                    "file":"string.json","number":0,"strings":[{"id":"0-0","parent":"Group 0","source":string}]
                },
                settings
            )
            if len(data) == 1:
                return data[list(data.keys())[0]]
            else:
                return None
        except Exception as e:
            self.instance = None
            self.owner.log.error("[TL Gemini] Error in 'translate':\n" + self.owner.trbk(e))
            return None

    async def translate_batch(self : TLGemini, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        try:
            return await self.ask_gemini(batch, settings)
        except Exception as e:
            self.owner.log.error("[TL Gemini] Error in 'translate_batch':\n" + self.owner.trbk(e))
            return {}