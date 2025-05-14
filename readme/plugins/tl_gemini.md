# RPGMTL  
  
# TL Gemini Plugin Manual  
  
## Quick Overview  
  
The TL Gemini Plugin is a Translator Plugin.  
It's a wrapper around the `google-genai` module.  
The later Python module must be installed for the Plugin to load.  
  
The plugin is currently in an experimental state, so the requirement isn't installed by default via `python -m pip install -r requirements.txt`.  
It's also quite slow if you're on the free tier. This plugin is best suited for Batch Translation (using the `Translate this File` button).  
  
You can generate an API key at https://aistudio.google.com/apikey  
Recommended models are:  
- `gemini-2.5-pro-exp-03-25`  
- `gemini-2.5-flash-preview-04-17`  
  
Check rate limits here: https://ai.google.dev/gemini-api/docs/rate-limits  