from __future__ import annotations
from . import TranslatorPlugin, TranslatorBatchFormat
try:
    from google import genai
    from pydantic import BaseModel
except:
    raise Exception("Failed to import google-genai.\nMake sure it's installed using: pip install -U google-genai")
from typing import Any
import json

TL_PROMPT : str = """You are the World's best Video Game Translator.
Your task is to take a JSON object formatted in such manner:
```json
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
```
Example:
```json
{
    "file":"Game Script.json",
    "number":35,
    "strings":[
        {
            "id":"2-1",
            "parent":"Group 2: Message Jack",
            "source":"昨日はすごく楽しかった！",
            "translation":"It was so much fun yesterday!"
        },
        {
            "id":"2-2",
            "parent":"Group 2: Message John",
            "source":"昨日何をしましたか？"
        },
        {
            "id":"2-3",
            "parent":"Group 2: Message Jack",
            "source":"私は映画を見ました。"
        }
    ]
}
```
You must translate them from $SOURCE$ to $TARGET$.
The strings are in order of occurence.
An existing translation may or may not be provided.
Don't re-translate unless it's incorrect.
Preserve placeholders (e.g. {playerName}, %VAR%, <tag>), punctuation, new line (e.g. \n), and code syntax.

Produce JSON matching this specification:
```json
[
    {"id":"STRING_ID", "translation":"TRANSLATED_STRING"}
]
```
Example:
```json
[
    {"id":"2-2", "translation":"What did you do yesterday?"},
    {"id":"2-3", "translation":"I saw a movie."}
]
```
Do NOT include any other text or formatting outside of the JSON object.
Provide only the JSON object. No explanations, no 'Here is your translation:' or anything similar.
$EXTRA$

$KNOWLEDGE$

The user input:
$INPUT$

Your output:
"""

KB_PROMPT : str = """You are the World's best Video Game Translator.
Your task it to update the knowledge base for the $SOURCE$ to $TARGET$ translation you're currently working on.
The user will provide a batch of strings for matted in such manner:
```json
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
```
Example:
```json
{
    "file":"Game Script.json",
    "number":35,
    "strings":[
        {
            "id":"2-1",
            "parent":"Group 2: Message Jack",
            "source":"昨日はすごく楽しかった！",
            "translation":"It was so much fun yesterday!"
        },
        {
            "id":"2-2",
            "parent":"Group 2: Message John",
            "source":"昨日何をしましたか？"
        },
        {
            "id":"2-3",
            "parent":"Group 2: Message Jack",
            "source":"私は映画を見ました。"
        }
    ]
}
```

Your goal is to provide a JSON list of names, for characters, items, places, etc... along their translation and additional notes which might help with the translation.
Notes must NOT be a lenghty description.
Notes must, for example, includes the gender of the character, if it is or has a nickname, etc... Anything which will help your future translations.
An example of the output JSON is the following:
```json
[
    {"original":"ジョン", "translation":"John", "note":"Adult man. Age 24. Work at the local cinema."},
    {"original":"ジャック", "translation":"Jack", "note":"Adult man. Age 19. Enjoy movies."}
]
```
Only provide new entries or update ones if there is a need to update the notes.
Preserve placeholders (e.g. {playerName}, %VAR%, <tag>), punctuation, new line (e.g. \n), and code syntax.
Do NOT include any other text or formatting outside of the JSON object.
Provide only the JSON object. No explanations, no 'Here is the output:' or anything similar.
$EXTRA$

The existing knowledge base is the following:
```json
$KNOWLEDGE$
```

The user input:
$INPUT$

Your output:
"""

class GModel(BaseModel):
    id: str
    translation: str

class GKbModel(BaseModel):
    original: str
    translation: str
    note: str

class TLGemini(TranslatorPlugin):
    def __init__(self : TLGemini) -> None:
        super().__init__()
        self.name : str = "TL Gemini"
        self.description : str = " v0.7\nWrapper around the google-genai module to TL_PROMPT Gemini. (EXPERIMENTAL)"
        self.instance = None
        self.key_in_use = None

    def get_format(self : TranslatorPlugin) -> TranslatorBatchFormat:
        return TranslatorBatchFormat.AI

    def get_token_budget_threshold(self : TranslatorPlugin) -> int:
        return 20000

    def get_setting_infos(self : TLGemini) -> dict[str, list]:
        return {
            "gemini_api_key": ["Set the Google Studio <a href=\"https://aistudio.google.com/apikey\">API Key</a> (Don't share your settings/config.json!)", "password", "", None],
            "gemini_model": ["Set the Gemini <a href=\"https://aistudio.google.com/changelog\">Model String</a> (<a href=\"https://ai.google.dev/gemini-api/docs/rate-limits\">Rate Limits</a>)", "str", "gemini-2.5-flash", None],
            "gemini_src_language": ["Set the Source Language", "str", "Japanese", None],
            "gemini_target_language": ["Set the Target Language", "str", "English", None],
            "gemini_extra_context": ["Set extra informations or commands for the AI", "text", "", None],
            "gemini_use_knowledge_base": ["Gemini will build a knowledge base (Require extra requests and tokens)", "bool", False, None]
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

    def parse_model_output(self : TLGemini, text : str, input_batch : dict[str, Any]) -> dict[str, str]:
        id_set : set[str] = set()
        for string in input_batch["strings"]:
            id_set.add(string["id"])
        output : list[dict[str, str]] = json.loads(text)
        parsed : dict[str, str] = {}
        for el in output:
            if el.get("id", None) is not None and el.get("translation", None) is not None and el["id"] in id_set:
                parsed[el["id"]] = el["translation"]
        return parsed

    async def ask_gemini(self : TLGemini, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        self._init_translator(settings)
        extra_context : str = ""
        if settings["gemini_extra_context"].strip() != "":
            extra_context = "\nThe User specified the following:\n{}".format(settings["gemini_extra_context"])
        knowledge_base : str = self.knowledge_to_text(settings.get("gemini_knowledge_base", []))
        if knowledge_base != "":
            knowledge_base = "The following is a partial glossary of names encountered in the game.\nStrictly follow the notes mentioned inside:\n" + knowledge_base
        response = self.instance.models.generate_content(
            model=settings["gemini_model"],
            contents=TL_PROMPT.replace("$TARGET$", settings["gemini_target_language"]).replace("$SOURCE$", settings["gemini_src_language"]).replace("$EXTRA$", extra_context).replace("$KNOWLEDGE$", knowledge_base).replace("$INPUT$", json.dumps(batch, ensure_ascii=False, indent=4), 1),
            config={
                "response_mime_type": "application/json",
                "response_schema": list[GModel]
            }
        )
        return self.parse_model_output(response.text, batch)

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

    async def update_knowledge(self : TLGemini, name : str, batch : dict[str, Any], settings : dict[str, Any] = {}) -> None:
        try:
            if not settings.get("gemini_use_knowledge_base", False):
                return
            self._init_translator(settings)
            extra_context : str = ""
            if settings["gemini_extra_context"].strip() != "":
                extra_context = "\nThe User specified the following for the whole translation project:\n{}".format(settings["gemini_extra_context"])
            if "gemini_knowledge_base" not in self.owner.projects[name]['settings']:
                self.owner.projects[name]['settings']["gemini_knowledge_base"] = []
            response = self.instance.models.generate_content(
                model=settings["gemini_model"],
                contents=KB_PROMPT.replace("$TARGET$", settings["gemini_target_language"]).replace("$SOURCE$", settings["gemini_src_language"]).replace("$EXTRA$", extra_context).replace("$KNOWLEDGE$", json.dumps(self.owner.projects[name]['settings']["gemini_knowledge_base"], ensure_ascii=False, indent=4), 1).replace("$INPUT$", json.dumps(batch, ensure_ascii=False, indent=4), 1),
                config={
                    "response_mime_type": "application/json",
                    "response_schema": list[GKbModel]
                }
            )
            output = json.loads(response.text)
            ref = {entry["original"] : entry for entry in self.owner.projects[name]['settings']["gemini_knowledge_base"]}
            updated : int = 0
            added : int = 0
            for entry in output:
                if "original" in entry and "translation" in entry and "note" in entry:
                    if entry["original"] in ref:
                        ref[entry["original"]]["note"] = entry["note"]
                        updated += 1
                    else:
                        self.owner.projects[name]['settings']["gemini_knowledge_base"].append({"original":entry["original"], "translation":entry["translation"], "note":entry["note"]})
                        added += 1
                    self.owner.modified[name] = True
            self.owner.log.info("[TL Gemini] Knowledge base for project {} got {} addition(s), {} updates".format(name, added, updated))
        except Exception as e:
            self.owner.log.error("[TL Gemini] Error in 'update_knowledge':\n" + self.owner.trbk(e))

    def knowledge_to_text(self : TLGemini, base : list[dict]) -> str:
        result : list[str] = []
        for entry in base:
            if entry["note"].strip() != "":
                result.append("- {} ({}): {}".format(entry["original"], entry["translation"], entry["note"]))
            else:
                result.append("- {} ({})".format(entry["original"], entry["translation"]))
        return "\n".join(result).strip()