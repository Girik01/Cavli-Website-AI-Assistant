"""Single place for tunables. Only secrets/endpoints come from .env."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- secrets / endpoints (.env) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")        # read implicitly by langchain-openai
QDRANT_URL = os.getenv("QDRANT_URL") or None         # empty -> embedded local Qdrant in ./qdrant_data
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None

# --- tunables (code, not env) ---
COLLECTION = "cavli_modules"
CHAT_MODEL = "gpt-5.4-mini"
CHAT_REASONING = "none"   # gpt-5.x reasoning effort; "none" keeps first-token latency low (these models take no temperature)
EMBED_MODEL = "text-embedding-3-small"
CONTEXT_K = 12        # top k: chunks retrieved and passed to the LLM
OUT_OF_SCOPE_BELOW = 0.35  # best score below this = off-topic ("out of scope"); above it but unanswered = "not verified"
MIN_COSINE = 0.30     # a chunk must reach this cosine to count as evidence (eval: off-topic <= 0.27, on-topic unsupported >= 0.40, answerable >= 0.49)
RATE_LIMIT_PER_MIN = 20
MAX_QUESTION_CHARS = 500

# Websites allowed to call this API from a browser (CORS). Empty = same-origin only. To embed the widget on the Cavli site, add its origin, e.g. ["https://www.cavliwireless.com"].
ALLOWED_ORIGINS: list[str] = []
