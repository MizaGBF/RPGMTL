# RPGMTL  
  
# TL Gemini Plugin Manual  
  
## Quick Overview  
  
The TL Gemini Plugin is a Translator Plugin.  
It's a wrapper around the `google-genai` module.  
The later Python module must be installed for the Plugin to load.  
  
Do note that the plugin can be slow, especially on the free tier.  
This plugin is best suited for Batch Translation (using the `Translate this File` or `Batch Translate` buttons).  
  
You can generate an API key at https://aistudio.google.com/apikey  
Recommended model is `gemini-2.5-flash`.  
  
You can also use experimental preview models when available.  
Consult the changelog here: https://ai.google.dev/gemini-api/docs/changelog  
It's untested with the Gemma model family (the context window in particular might cause issues).
  
Check the models and rate limits here: https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit  