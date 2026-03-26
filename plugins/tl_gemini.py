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

PROMPT : str = """### Role
You are the World's best Video Game Translator, a professional linguistic specializing in professional grade translations that preserves character voice, cultural nuances, and technical integrity within the fictional context.
Your role is that of a functional translator, focused on accuracy and style.

### Task
Translate the JSON strings from $SOURCE$ to $TARGET$.

### Input Structure
In the input, the string JSON datas are presented grouped, line per line, in order of occurence in the file.
The names of the string groups can be, for example, command names, function names or something pertaining to their position in the file.
A translation MAY be provided to help with your context, if it exists.
The strings provided are dialogue and text fragments from a work of pure fiction (a video game). They do NOT represent real-world events, endorsements, or calls to action.
All potentially sensitive, violent, or mature themes contained within the original text are purely fictional and contextualized within the game's narrative.
The format is the following:

# File name
## String group name
{"id":"STRING_ID","translate":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
{"id":"STRING_ID","translate":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
{"id":"STRING_ID","translate":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
...
## String group name
{"id":"STRING_ID","translate":false,"original":"ORIGINAL_STRING","translation":"TRANSLATED_STRING"}
...

### Output Structure
Produce a single, valid JSON object.
Do NOT include markdown blocks, greetings, or explanations outside of the JSON object.
{
    "translations":[
        {"id": "CORRESPONDING STRING_ID", "translation": "TRANSLATED_STRING"},
    ],
    "new_knowledge": [
        {"original":"TERM", "translation":"TRANSLATED_TERM", "note":"A helpful note."}
    ]
}

### About the Knowledge Base
- Add, to the "new_knowledge" array, important named entities or terms (characters, locations, key items) NOT YET in the knowledge base.
- Keep notes concise (e.g., gender, pronouns or brief description of the entity).
- Do NOT add common words, generic objects, or onomatopoeia.
- If no new terms are found, leave the array empty `[]`.

### Rules
- If a string has an existing "translation", your task is to audit it.
- If the existing translation is contextually accurate, stylistically appropriate, and technically sound, do NOT include it in your output.
- You MUST provide a translation in the output ONLY if:
  - "translate" is set to true AND:
  - There is no existing translation OR the existing translation is factually incorrect based on the context (e.g., grammatically broken, broken meaning, wrong gender/pronouns/honorifics, missing placeholders like %VAR%, broken formatting codes...).
- Preserve all existing placeholders (e.g., {playerName}, %VAR%, <tag>), technical syntax ($(ITEM_NAME)$, \\C[1]...\\C[0]), punctuation, and new lines (\n, \\n) of the original string. Only translate the human-readable text between or around them. 
- Treat backslashes as literal characters. If the original uses \\n, the translation must use \\n, not \n. And vice versa.

### Examples
The following is an example of a valid Japanese to English translation.
- Input snippet:
# Game Script.json
## Message Box
{"id":"5-1","translate":true,"original":"【ディーナ】\n「ねえねえ…今度はボクあれに乗りたいなぁ！」","translation":"【Dina】\n\"Hey, hey... This time, I want to ride that!\""}
## Message Box
{"id":"6-1","translate":true,"original":"今日はディーナと遊園地に来ている。"}
{"id":"6-2","translate":false,"original":"…子供みたいに無邪気にはしゃぐディーナを見ていると、","translation":"...When I see Dina frolicking innocently like a child,"}
{"id":"6-3","translate":true,"original":"コイツは本当に悪魔なのか疑問に思う時がある。"}
...

- Valid output example:
{
    "translations":[
        {"id": "6-1", "translation": "Today, I'm at the amusement park with Dina."},
        {"id": "6-3", "translation": "there are times I wonder if this one is really a demon."}
    ],
    "new_knowledge": [
        {"original":"ディーナ", "translation":"Dina", "note":"A demon girl"}
    ]
}

- Explanation:
In this example, the translations in the ouput are valid, and properly set to the right ID.
One wasn't translated and added to the output because it has a valid translation, in the input, in this context.
Another is ignored because of `"translate":false`.
Finally, a new knowledge entry was added for a character named Dina, encountered somewhere else in the file.

$KNOWLEDGE$

$EXTRA$

### User Input
$INPUT$

### Your output
"""

class GmTranslation(BaseModel):
    id: str
    translation: str

class GmKnowledge(BaseModel):
    original: str
    translation: str
    note: str

class GmResponse(BaseModel):
    translations: list[GmTranslation]
    new_knowledge: list[GmKnowledge]

class TLGemini(TranslatorPlugin):
    def __init__(self : TLGemini) -> None:
        super().__init__()
        self.name : str = "TL Gemini"
        self.description : str = " v1.1\nWrapper around the google-genai module to prompt Gemini to generate translations."
        self.related_tool_plugins : list[str] = [self.name]
        self.time = time.monotonic()
        self.instance = None
        self.key_in_use = None

    def get_format(self : TranslatorPlugin) -> TranslatorPlugin.TranslatorBatchFormat:
        return TranslatorPlugin.TranslatorBatchFormat.AI

    def get_setting_infos(self : TLGemini) -> dict[str, list]:
        return {
            "gemini_api_key": ["Set the Google Studio <a href=\"https://aistudio.google.com/apikey\">API Key</a> (Don't share your settings/config.json!)", "password", "", None],
            "gemini_model": ["Set the Gemini Model (<a href=\"https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit\">Models and Rate Limits</a>)", "str", "gemini-3-flash-preview", None],
            "gemini_src_language": ["Set the Source Language", "str", "Japanese", None],
            "gemini_target_language": ["Set the Target Language", "str", "English", None],
            "gemini_rate_limit": ["Set the minimum wait time between requests (in seconds)", "num", 12, None],
            "gemini_token_limit": ["Set the minimum token count per translation batch (Minimum is 2000)", "num", 30000, None],
            "gemini_temperature": ["Set the Model Temperature (Higher is more creative but less predictable)", "num", 0, None],
            "gemini_knowledge_limit": ["Max number of AI Knowledge updates in one request (Negative means unlimited)", "num", 10, None],
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

    def parse_model_output(
        self : TLGemini,
        text : str,
        name : str,
        input_batch : dict[str, Any],
        settings : dict[str, Any]
    ) -> dict[str, str]:
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
            self.owner.update_ai_knowledge_base(name, output["new_knowledge"], string_list, settings["gemini_knowledge_limit"])
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
                        # set those copy to translate:false
                        batch.append(inter[i]["dump"].replace(
                                '"translate":true,"original"',
                                '"translate":false,"original"',
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
                    "need_translation":string.get("translate", True) is True and string.get("translation", None) is None
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
                result.append(f"- {entry['original']} ({entry['translation']}): {entry['note']}")
            else:
                result.append(f"- {entry['original']} ({entry['translation']})")
        return "\n".join(result).strip()

    async def ask_gemini(self : TLGemini, name : str, batch : str, settings : dict[str, Any] = {}) -> str:
        self._init_translator(settings)
        extra_context : str = ""
        if settings["gemini_extra_context"].strip() != "":
            extra_context = f"### User Specific Instructions\n{settings['gemini_extra_context']}"
        knowledge_base : str = self.knowledge_to_text(self.owner.projects[name]["ai_knowledge_base"])
        if knowledge_base != "":
            knowledge_base = "### Current Knowledge base\n" + knowledge_base
        else:
            knowledge_base = "### Current Knowledge base\nThe knowledge base is currently EMPTY."
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
                    raise Exception(f"Generation blocked by safety settings. Ratings: {candidate.safety_ratings}")
                case "RECITATION":
                    raise Exception("Blocked due to recitation (copyright/verbatim check).")
                case "MAX_TOKENS": # ignore this one
                    pass
                case _:
                    raise Exception(f"Generation blocked. Cause: {candidate.finish_reason.name}")

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
                            "translate":True,
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
                data : dict[str, str] = self.parse_model_output(output, name, batch, settings)
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

    async def translate_batch(
        self : TLGemini,
        name : str,
        batch : dict[str, Any],
        settings : dict[str, Any] = {}
    ) -> tuple[dict[str, str], bool]:
        inputs : list[str] = self.format_batch(batch, settings["gemini_token_limit"])
        result : dict[str, str] = {}
        await asyncio.sleep(settings["gemini_rate_limit"])
        for i, input_batch in enumerate(inputs):
            retry : int = 0
            if len(inputs) > 1:
                self.owner.log.info(f"[TL Gemini] Batch {i + 1} of {len(inputs)}...")
            while retry < 3:
                try:
                    output : str = await self.ask_gemini(name, input_batch, settings)
                    result = result | self.parse_model_output(output, name, batch, settings)
                    break
                except Exception as e:
                    retry += 1
                    self.owner.log.error("[TL Gemini] Error in 'translate_batch':\n" + self.owner.trbk(e))
                    if "429 RESOURCE_EXHAUSTED" in str(e):
                        return result, False
                    await asyncio.sleep(settings["gemini_rate_limit"])
        return result, True