# Firmly connections

Configure live research with a model access key and a web research key.

| Firmly label | Current integration | Custom configuration |
| --- | --- | --- |
| Web research key | Tavily search and extraction | `FIRMLY_SEARCH_KEY` |
| Model access key | OpenRouter model gateway | `FIRMLY_MODEL_KEY` |
| Research model | OpenRouter's free router by default | `FIRMLY_MODEL` |
| Installation model | Optional direct OpenAI API | `FIRMLY_DIRECT_MODEL_KEY` |
| Briefing connection | Optional Google Gemini API | `FIRMLY_BRIEFING_KEY` |
| Report storage | Optional MongoDB | `FIRMLY_STORAGE_URI` |

Automatic selection uses `openrouter/free`. Service endpoints and model identifiers
are defined in `firmly_engine/connections.py` and `ui/src/lib/connections.ts`.

Create the web key at https://app.tavily.com/ and the model key at
https://openrouter.ai/settings/keys. These are the destinations behind the settings
page's “Get a key” links. Free tiers have usage limits; external billing settings
remain with those services.

Use the environment variable names in `.env.example` for local and deployed installations.
