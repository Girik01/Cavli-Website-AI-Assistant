from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app import config

ROOT = Path(__file__).resolve().parent.parent


def get_embeddings():
    return OpenAIEmbeddings(model=config.EMBED_MODEL)


def qdrant_kwargs():
    kw = {"collection_name": config.COLLECTION}
    if config.QDRANT_URL:
        kw["url"] = config.QDRANT_URL
        if config.QDRANT_API_KEY:
            kw["api_key"] = config.QDRANT_API_KEY
    else:
        kw["path"] = str(ROOT / "qdrant_data")
    return kw


def chat_llm(**kw):
    """The chat model from config. gpt-5.x models are deterministic enough with reasoning off and reject `temperature`."""
    return ChatOpenAI(model=config.CHAT_MODEL, reasoning_effort=config.CHAT_REASONING, timeout=kw.pop("timeout", 30),
                      max_retries=kw.pop("max_retries", 1), **kw)
