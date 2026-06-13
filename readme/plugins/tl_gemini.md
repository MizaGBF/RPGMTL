# RPGMTL  
  
# TL Gemini Plugin Manual  
  
## Quick Overview  
  
The TL Gemini Plugin is a Translator Plugin.  
It's a wrapper around the `google-genai` module.  
The later Python module must be installed for the Plugin to load.  
  
Do note that the plugin can be slow, especially on the free tier.  
This plugin is best suited for Batch Translation (using the `Translate this File` or `Batch Translate` buttons).  
  
You can generate an API key at https://aistudio.google.com/apikey  
Recommended model is `gemini-3.1-flash-lite` **at the time of this writing**.  
  
You can also use experimental preview models when available.  
Consult the changelog here: https://ai.google.dev/gemini-api/docs/changelog  
It's untested with the Gemma model family (the context window in particular might cause issues).
  
Check the models and rate limits here: https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit  
  
## Note on safety  
  
Safety filters are turned off except the `PROHIBITED_CONTENT` filter enforced by Google.  
It's, sadly, very sensitive and is easily triggered if you're translating H-games or some violent games.  
The only workaround is to reduce the translation batch token count in the project setting, to the point where RPGMTL will break the file in multiple batch.  
This way, while the sensitive batch might still be blocked, other parts of the file should still be translated.  
You'll then have to translate the sensitive content by yourself.  