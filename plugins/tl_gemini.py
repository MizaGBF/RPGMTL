from __future__ import annotations
from . import TranslatorPlugin, TranslatorBatchFormat
try:
    from google.genai import Client
    from pydantic import BaseModel
except:
    raise Exception("Failed to import google-genai.\nMake sure it's installed using: pip install -U google-genai")
from typing import Any
import asyncio
import json

PROMPT : str = """You are the World's best Video Game Translator.
Your task is to translate the strings from $SOURCE$ to $TARGET$, provided in a JSON object of this specification:
{"file":"FILE","number":BATCH_NUMBER,"strings":[{"id":"STRING_ID","parent":"GROUP OF WHICH THIS STRING IS PART OF","source":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"},{"id":"STRING_ID","parent":"GROUP OF WHICH THIS STRING IS PART OF","source":"ORIGINAL_STRING"}]
}

The strings are in order of occurence.
An existing translation may or may not be provided.
If, and only if, a translation is provided in the input, do NOT re-translate unless it's incorrect.
Preserve placeholders (e.g. {playerName}, %VAR%, <tag>), punctuation, new line (e.g. \n and \\n), and code syntax.
In regard to new lines, make sure to preserve the \n or \\n in the syntax they're written (i.e. the number of backslash used).

In the input, you must also identify important proper nouns (characters, places or key items) that are not already in the provided knowledge base below.
Notes should be concise and help with future translations (e.g., gender, role) and NOT be lengthy descriptions.
For example, they can includes a character gender, pronuns, specific terms relevant for the translation, and so on.
Do NOT add general/common words or expressions, objects or onomatopoeia. Add ONLY unique, named entities, to not bloat the knowledge base.

Produce a single JSON object matching this specification:
{"new_knowledge": [{"original": "TERM", "translation": "TRANSLATED_TERM", "note": "A helpful note."}],"translations": [{"id": "STRING_ID", "translation": "TRANSLATED_STRING"}]}

Example:
Valid input:
{"file":"Game Script.json","number":35,"strings":[{"id":"2-1","parent":"Group 2: Message Jack","source":"昨日はすごく楽しかった！","translation":"It was so much fun yesterday!"},{"id":"2-2","parent":"Group 2: Message John","source":"昨日何をしましたか？"},{"id":"2-3","parent":"Group 2: Message Jack","source":"私は映画を見ました。"}]
}

Valid output:
{"new_knowledge": [{"original": "ジョン", "translation": "John", "note": "Adult man. Nickname \"Johny\"."}],"translations": [{"id": "2-2", "translation": "What did you do yesterday?"},{"id": "2-3", "translation": "I saw a movie."}]
}

Do NOT include any other text or formatting OUTSIDE of the JSON object.
Provide only the JSON object. No explanations, no 'Here is your translation:' or anything similar.
$KNOWLEDGE$

$EXTRA$

The user input:
$INPUT$

Your output:
"""

class GmTranslation(BaseModel):
    id: str
    translation: str

class GmKnowledge(BaseModel):
    original: str
    translation: str
    note: str

class GmResponse(BaseModel):
    new_knowledge: list[GmKnowledge]
    translations: list[GmTranslation]

class TLGemini(TranslatorPlugin):
    def __init__(self : TLGemini) -> None:
        super().__init__()
        self.name : str = "TL Gemini"
        self.description : str = " v1.0\nWrapper around the google-genai module to prompt Gemini to generate translations."
        self.related_tool_plugins : list[str] = [self.name]
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
            "gemini_temperature": ["Set the Model Temperature (Higher is more creative but less predictable)", "num", 0, None],
            "gemini_extra_context": ["Set extra informations or commands for the AI", "text", "", None]
        }

    def _init_translator(self : TLGemini, settings : dict[str, Any]) -> None:
        try:
            if self.key_in_use is not None and settings["gemini_api_key"] == self.key_in_use:
                return
            if self.instance is None:
                current = Client(api_key=settings["gemini_api_key"])
                self.instance = current
                self.key_in_use = settings["gemini_api_key"]
        except Exception as e:
             self.owner.log.error("[TL Gemini] Error in '_init_translator':\n" + self.owner.trbk(e))

    def update_knowledge_base(
        self : TLGemini,
        name : str,
        input_strings : list[dict[str, str]],
        new_knowledge : list[dict[str, str]]
    ) -> None:
        base_ref = self.owner.projects[name]["ai_knowledge_base"]
        # update last seen
        for entry in base_ref:
            found = False
            for string in input_strings:
                if entry["original"] in string["source"]:
                    entry["occurence"] += 1
                    entry["last_seen"] += 0
                    found = True
                    self.owner.modified[name] = True
                    break
            if not found:
                entry["last_seen"] += 1
                self.owner.modified[name] = True
        # table of original : pointer to entries
        ref = {entry["original"] : entry for entry in self.owner.projects[name]["ai_knowledge_base"]}
        updated : int = 0
        added : int = 0
        deleted : int = 0
        for entry in new_knowledge:
            if "original" in entry and "translation" in entry and "note" in entry:
                if entry["original"] in ref:
                    ref[entry["original"]]["note"] = entry["note"]
                    if ref[entry["original"]]["last_seen"] != 0: # if not found in above loop
                        ref[entry["original"]]["last_seen"] = 0
                        ref[entry["original"]]["occurence"] += 1
                    updated += 1
                    self.owner.modified[name] = True
                else:
                    # Checking if the entry added by the AI is a substring of an existing one
                    # For example: AI tris to add John, when we have John Doe in our list
                    # Note: Current solution isn't perfect, but it's to help with the bloat
                    # Note²: Maybe add a setting toggle?
                    found : bool = False
                    for k in ref:
                        if entry["original"] in k:
                            found = True
                            if ref[k]["last_seen"] != 0: # if not found in above loop
                                ref[k]["last_seen"] = 0
                                ref[k]["occurence"] += 1
                            break
                    if not found:
                        base_ref.append({"original":entry["original"], "translation":entry["translation"], "note":entry["note"], "last_seen":0, "occurence":1})
                        added += 1
                        self.owner.modified[name] = True
        # cleanup
        i = 0
        while i < len(base_ref):
            if base_ref[i]["last_seen"] > 10: # if not seen in last 10 translations
                base_ref[i]["occurence"] -= 1
                self.owner.modified[name] = True
            if base_ref[i]["occurence"] <= 0: # if occurence at 0, delete from base
                base_ref.pop(i)
                deleted += 1
            else:
                i += 1
        # result
        if updated + added + deleted != 0:
            self.owner.log.info("[TL Gemini] Knowledge base of project {}: {} update(s), {} addition(s), {} deletion(s)".format(name, updated, added, deleted))

    def parse_model_output(self : TLGemini, text : str, name : str, input_batch : dict[str, Any]) -> dict[str, str]:
        # build set of string id from batch for validation
        id_set : set[str] = set()
        for string in input_batch["strings"]:
            id_set.add(string["id"])
        # load data
        err = 0
        cur = len(text)
        while err < 3:
            try:
                output : dict = json.loads(text)
                break
            except:
                err += 1
                cur = text.rfind("},", 0, cur)
                if cur == -1:
                    raise Exception("[TL Gemini] Text isn't valid JSON")
                text = text[:cur+1] + "]}"
        # generate dict of edited strings for RPGMTL
        parsed : dict[str, str] = {}
        if "translations" in output:
            for string in output["translations"]:
                if string.get("id", None) is not None and string.get("translation", None) is not None and string["id"] in id_set:
                    parsed[string["id"]] = string["translation"]
        # updated knowledge base
        if "new_knowledge" in output:
            self.update_knowledge_base(name, input_batch["strings"], output["new_knowledge"])
        return parsed

    async def ask_gemini(self : TLGemini, name : str, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        self._init_translator(settings)
        extra_context : str = ""
        if settings["gemini_extra_context"].strip() != "":
            extra_context = "\nThe User specified the following:\n{}".format(settings["gemini_extra_context"])
        knowledge_base : str = self.knowledge_to_text(self.owner.projects[name]["ai_knowledge_base"])
        if knowledge_base != "":
            knowledge_base = "The knowledge base that you must strictly refer to for your translations is the following:\n" + knowledge_base
        else:
            knowledge_base = "The knowledge base is currently empty."
        response = self.instance.models.generate_content(
            model=settings["gemini_model"],
            contents=PROMPT.replace("$TARGET$", settings["gemini_target_language"], 1).replace("$SOURCE$", settings["gemini_src_language"], 1).replace("$EXTRA$", extra_context, 1).replace("$KNOWLEDGE$", knowledge_base, 1).replace("$INPUT$", json.dumps(batch, ensure_ascii=False, separators=(',',':')), 1),
            config={
                "response_mime_type":"application/json",
                "response_schema":GmResponse,
                "temperature":settings["gemini_temperature"],
            }
        )
        return self.parse_model_output(response.text, name, batch)

    async def translate(self : TLGemini, name : str, string : str, settings : dict[str, Any] = {}) -> str|None:
        retry : int = 0
        while retry < 3:
            try:
                data = await self.ask_gemini(
                    name,
                    {
                        "file":"string.json","number":0,"strings":[
                            {
                                "id":"0-0",
                                "parent":"Group 0",
                                "source":string
                            }
                        ]
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
                se : str = str(e)
                if "JSONDecodeError" in se or "500 INTERNAL" in se or "503 " in se:
                    await asyncio.sleep(10)
                    retry += 1
                elif "429 RESOURCE_EXHAUSTED" in se:
                    raise Exception("Resource exhausted")
                else:
                    return None

    async def translate_batch(self : TLGemini, name : str, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        retry : int = 0
        while retry < 3:
            try:
                return await self.ask_gemini(name, batch, settings)
            except Exception as e:
                self.owner.log.error("[TL Gemini] Error in 'translate_batch':\n" + self.owner.trbk(e))
                se : str = str(e)
                if "JSONDecodeError" in se or "500 INTERNAL" in se or "503 " in se:
                    await asyncio.sleep(10)
                    retry += 1
                elif "429 RESOURCE_EXHAUSTED" in se:
                    raise Exception("Resource exhausted")
                else:
                    return {}

    def knowledge_to_text(self : TLGemini, base : list[dict]) -> str:
        result : list[str] = []
        for entry in base:
            if entry["note"].strip() != "":
                result.append("- {} ({}): {}".format(entry["original"], entry["translation"], entry["note"]))
            else:
                result.append("- {} ({})".format(entry["original"], entry["translation"]))
        return "\n".join(result).strip()