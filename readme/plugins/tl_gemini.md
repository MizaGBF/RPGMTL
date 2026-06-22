# RPGMTL  
  
# TL Gemini Plugin Manual  
  
## Quick Overview  
  
The Google Gemini plugin interfaces with the Gemini API using the `google-genai` Python module. This module must be installed for the plugin to function.  
  
Due to its processing nature, this plugin is best suited for **Batch Translation** (e.g., "Translate this File" or "Batch Translate"). Note that performance may vary, particularly when using the free API tier.  
  
## Configuration  
  
* **API Key**: Generate a key at the [Google AI Studio](https://aistudio.google.com/apikey).  
* **Recommended Model**: `gemini-3.1-flash-lite` (or the latest stable Flash model).  
* **Rate Limits**: Consult the [AI Studio Usage Dashboard](https://aistudio.google.com/usage) for details on current limits and model availability.  
  
Consult the changelog here: https://ai.google.dev/gemini-api/docs/changelog to learn about discontinued or newer models.  
  
Check the models and your   rate limits here: https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit  
  
## Safety Filters and Content  
  
Safety filters are disabled by default within the plugin, with the exception of the `PROHIBITED_CONTENT` filter enforced by Google. This filter can be sensitive to violent or adult-oriented content.  
  
**Workaround for Blocked Content**:  
If translations are frequently blocked, reduce the batch token count in the project settings. This forces RPGMTL to split files into smaller batches. While specific sensitive sections may still be blocked, the rest of the file can often be processed successfully. Content that remains blocked must be translated manually.  