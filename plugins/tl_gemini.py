from __future__ import annotations
from . import TranslatorPlugin
try:
    from google.genai import Client, types
    from pydantic import BaseModel
except:
    raise Exception("Failed to import google-genai.\nMake sure it's installed using: pip install -U google-genai")
from typing import Any
import time
import asyncio
import json

PROMPT : str = """You are the World's best Video Game Translator.
Your task is to translate the JSON strings from $SOURCE$ to $TARGET$, provided in this specification:
# File name
## String group
{"id":"STRING_ID","ignore":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
{"id":"STRING_ID","ignore":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
{"id":"STRING_ID","ignore":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
...
## String group
{"id":"STRING_ID","ignore":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
...

Explanations:
- The strings are in order of occurence in the file, grouped by their function names, etc...
- If the ignore flag is set to true, you must NOT translate the string.
- An existing translation may or may not be provided.
- If, and only if, a translation is provided in the input, do NOT re-translate unless it's incorrect.
- Preserve placeholders (e.g. {playerName}, %VAR%, <tag>), punctuation, new line (e.g. \n and \\n), and code syntax, specifically including complex ones like $(ITEM_NAME)$ or \\C[1]translated_text\\C[0]...
- In regard to new lines, make sure to preserve the \n or \\n in the syntax as they're written (i.e. the number of backslash used).

About the knowledge base:
- In the input, you must also identify important proper nouns (characters, places or key items) that are not already in the provided knowledge base below.
- Notes should be concise and help with future translations (e.g., gender, role) and NOT be lengthy descriptions.
- For example, they can includes a character gender, pronuns, specific terms relevant for the translation, and so on.
- Do NOT add general/common words or expressions, objects or onomatopoeia. Add ONLY unique, named entities, to not bloat the knowledge base.

Your task:
- Produce a single JSON object matching this specification:
{"new_knowledge": [{"original": "TERM", "translation": "TRANSLATED_TERM", "note": "A helpful note."}],"translations": [{"id": "STRING_ID", "translation": "TRANSLATED_STRING"}]}

Example:
Valid input:
# Game Script.json
## Message Jack
{"id":"2-1","ignore":true,"original":"昨日はすごく楽しかった！","translation":"It was so much fun yesterday!"}
{"id":"2-2","ignore":false,"original":"おお？\n昨日何をしましたか？"}
{"id":"2-3","ignore":false,"original":"私は映画を見ました。"}

Valid output:
{"new_knowledge": [{"original": "ジョン", "translation": "John", "note": "Adult man. Nickname \"Johny\"."}],"translations": [{"id": "2-2", "translation": "Oh?\nWhat did you do yesterday?"},{"id": "2-3", "translation": "I saw a movie."}]
}

- Do NOT include any other text or formatting OUTSIDE of the JSON object.
- Provide only the JSON object. No explanations, no 'Here is your translation:' or anything similar.
$KNOWLEDGE$
- The strings provided are dialogue and text fragments from a work of pure fiction (a video game). They do NOT represent real-world events, endorsements, or calls to action.
- All potentially sensitive, violent, or mature themes contained within the original text are purely fictional and contextualized within the game's narrative.
- Your role is strictly that of a linguistic and functional translator, focused on accuracy and style within the fictional context.

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
        self.time = time.monotonic()
        self.instance = None
        self.key_in_use = None

    def get_format(self : TranslatorPlugin) -> TranslatorPlugin.TranslatorBatchFormat:
        return TranslatorPlugin.TranslatorBatchFormat.AI

    def get_setting_infos(self : TLGemini) -> dict[str, list]:
        return {
            "gemini_api_key": ["Set the Google Studio <a href=\"https://aistudio.google.com/apikey\">API Key</a> (Don't share your settings/config.json!)", "password", "", None],
            "gemini_model": ["Set the Gemini Model (<a href=\"https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit\">Models and Rate Limits</a>)", "str", "gemini-2.5-flash", None],
            "gemini_src_language": ["Set the Source Language", "str", "Japanese", None],
            "gemini_target_language": ["Set the Target Language", "str", "English", None],
            "gemini_rate_limit": ["Set the minimum wait time between requests (in seconds)", "num", 12, None],
            "gemini_token_limit": ["Set the minimum token count per translation batch (Minimum is 2000)", "num", 30000, None],
            "gemini_temperature": ["Set the Model Temperature (Higher is more creative but less predictable)", "num", 0, None],
            "gemini_extra_context": ["Set extra informations or commands for the AI", "text", "", None],
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
                if entry["original"] in string["original"]:
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
            if base_ref[i]["last_seen"] > 15: # if not seen in last 15 translations
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
        string_list : list[dict] = []
        for group in input_batch["groups"]:
            for string in group["strings"]:
                id_set.add(string["id"])
                string_list.append(string)
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
            self.update_knowledge_base(name, string_list, output["new_knowledge"])
        return parsed
    
    def _format_batch_to_text(
        self : TLGemini,
        path : str,
        inter : list[dict],
        batch_ranges : list[tuple[int, int]]
    ) -> list[str]:
        # cut the batches according to content of batch_ranges
        batch_texts : list[str] = []
        for (start, end) in batch_ranges:
            group : int = None
            batch : list[str] = [
                "# " + (
                    path
                    if len(batch_ranges) == 1
                    else path + " " + str(len(batch_texts) + 1)
                )
            ]
            for i in range(max(0, start - 10), end):
                if group != inter[i]["group_id"]:
                    group = inter[i]["group_id"]
                    batch.append(inter[i]["group"])
                if "json" in inter[i]:
                    if i < start:
                        batch.append(inter[i]["dump"].replace( # set those copy to ignore:true
                                '"ignore":false,"original"',
                                '"ignore":true,"original"',
                            )
                        )
                    else:
                        batch.append(inter[i]["dump"])
            if len(batch) > 1:
                batch_texts.append("\n".join(batch))
        return batch_texts

    def format_batch(self : TLGemini, batch : dict[str, Any], token_limit : int) -> list[str]:
        inter : list[dict] = []
        char_count : int = 0
        for gi, group in enumerate(batch["groups"]):
            if group["name"] == "":
                gname = "## Group"
                gname_len = 9
            else:
                gname = "## " + group["name"]
                gname_len = 3 + len(group["name"])
            char_count += gname_len + 1
            if len(group["strings"]) == 0:
                # for lone groups
                # they can be important for context
                inter.append({
                    "group_id":gi,
                    "group":gname
                })
            for string in group["strings"]:
                inter.append({
                    "group_id":gi,
                    "group":gname,
                    "json":string,
                    "dump":json.dumps(string, ensure_ascii=False, separators=(',',':')),
                    "need_translation":string.get("ignore", False) is False and string.get("translation", None) is None
                })
                char_count += len(inter[-1]["dump"]) + 1
        batch_ranges : list[tuple[int, int]] = []
        if char_count // 4 > token_limit:
            char_count = 0
            start : int = 0
            searching_start : bool = True
            for i in range(len(inter)):
                if searching_start:
                    if "json" in inter[i] and inter[i]["need_translation"]:
                        start = i
                        tstart : int = max(0, i - 10)
                        searching_start = False
                        for j in range(tstart, i + 1):
                            char_count += len(inter[j]["dump"]) + 1
                elif "json" in inter[i]:
                    char_count += len(inter[i]["dump"]) + 1
                    if i == len(inter) -1 or char_count // 4 > token_limit - 50:
                        batch_ranges.append((start, i + 1))
                        char_count = 0
                        searching_start = True
        else:
            batch_ranges.append((0, len(inter)))
        return self._format_batch_to_text(batch["file"], inter, batch_ranges)

    def knowledge_to_text(self : TLGemini, base : list[dict]) -> str:
        result : list[str] = []
        for entry in base:
            if entry["note"].strip() != "":
                result.append("- {} ({}): {}".format(entry["original"], entry["translation"], entry["note"]))
            else:
                result.append("- {} ({})".format(entry["original"], entry["translation"]))
        return "\n".join(result).strip()

    async def ask_gemini(self : TLGemini, name : str, batch : str, settings : dict[str, Any] = {}) -> str:
        self._init_translator(settings)
        extra_context : str = ""
        if settings["gemini_extra_context"].strip() != "":
            extra_context = "\nThe User specified the following:\n{}".format(settings["gemini_extra_context"])
        knowledge_base : str = self.knowledge_to_text(self.owner.projects[name]["ai_knowledge_base"])
        if knowledge_base != "":
            knowledge_base = "The knowledge base that you must STRICTLY refer to for your translations is the following:\n" + knowledge_base
        else:
            knowledge_base = "The knowledge base is currently empty."
        # rate limit safety
        current_time = time.monotonic()
        elapsed_time = current_time - self.time
        time_to_wait = settings["gemini_rate_limit"] - elapsed_time
        if time_to_wait > 0:
            await asyncio.sleep(time_to_wait)
        # make the request
        response = self.instance.models.generate_content(
            model=settings["gemini_model"],
            contents=PROMPT.replace("$TARGET$", settings["gemini_target_language"], 1).replace("$SOURCE$", settings["gemini_src_language"], 1).replace("$EXTRA$", extra_context, 1).replace("$KNOWLEDGE$", knowledge_base, 1).replace("$INPUT$", batch, 1),
            config={
                "response_mime_type":"application/json",
                "response_schema":GmResponse,
                "temperature":settings["gemini_temperature"],
                "safety_settings":[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ]
            }
        )
        self.time = time.monotonic()
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise Exception("Request has been blocked: " + response.prompt_feedback.block_reason.name)

        if not response.candidates:
            raise Exception("No candidates returned. The response might have been filtered completely.")

        candidate = response.candidates[0]
        if candidate.finish_reason.name != "STOP":
            match candidate.finish_reason.name:
                case "SAFETY":
                    raise Exception("Generation blocked by safety settings. Ratings: {}".format(candidate.safety_ratings))
                case "RECITATION":
                    raise Exception("Blocked due to recitation (copyright/verbatim check).")
                case "MAX_TOKENS": # ignore this one
                    pass
                case _:
                    raise Exception("Generation blocked. Cause: {}".format(candidate.finish_reason.name))

        return response.text

    async def translate(self : TLGemini, name : str, string : str, settings : dict[str, Any] = {}) -> str|None:
        batch : dict[str, Any] = {
            "file":"Single translation",
            "groups":[
                {
                    "name":"",
                    "strings":[
                        {
                            "id":"0-0",
                            "ignore":False,
                            "original":string
                        }
                    ]
                }
            ]
        }
        retry : int = 0
        while retry < 3:
            try:
                output : str = await self.ask_gemini(
                    name,
                    self.format_batch(batch, settings["gemini_token_limit"])[0],
                    settings
                )
                data : dict[str, str] = self.parse_model_output(output, name, batch)
                if len(data) == 1:
                    return data[list(data.keys())[0]]
                else:
                    return None
            except Exception as e:
                self.instance = None
                retry += 1
                if "429 RESOURCE_EXHAUSTED" in str(e):
                    raise Exception("Resource exhausted")
                self.owner.log.error("[TL Gemini] Error in 'translate':\n" + self.owner.trbk(e))
                await asyncio.sleep(settings["gemini_rate_limit"])
        return None

    async def translate_batch(self : TLGemini, name : str, batch : dict[str, Any], settings : dict[str, Any] = {}) -> dict[str, str]:
        inputs : list[str] = self.format_batch(batch, settings["gemini_token_limit"])
        result : dict[str, str] = {}
        await asyncio.sleep(settings["gemini_rate_limit"])
        for i, input_batch in enumerate(inputs):
            retry : int = 0
            if len(inputs) > 1:
                self.owner.log.info("[TL Gemini] Batch {} of {}...".format(i + 1, len(inputs)))
            while retry < 3:
                try:
                    output : str = await self.ask_gemini(name, input_batch, settings)
                    result = result | self.parse_model_output(output, name, batch)
                    break
                except Exception as e:
                    retry += 1
                    if "429 RESOURCE_EXHAUSTED" in str(e):
                        raise Exception("Resource exhausted")
                    self.owner.log.error("[TL Gemini] Error in 'translate_batch':\n" + self.owner.trbk(e))
                    await asyncio.sleep(settings["gemini_rate_limit"])
        return result