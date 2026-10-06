import os
from langchain_openai import ChatOpenAI
from src.logging.logger import logger

def create_chat_model() -> ChatOpenAI:
    """Create the OpenAI chat model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key is not configured")
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

    logger.info("Initializing chat model", model=model_name, timeout_seconds=timeout, max_retries=max_retries)

    return ChatOpenAI(model=model_name, temperature=0, timeout=timeout, max_retries=max_retries)