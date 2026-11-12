import os
from langchain_openai import OpenAIEmbeddings
from src.app_logging.logger import logger

def create_embeddings() -> OpenAIEmbeddings:
    """Create the OpenAI embeddings model.

    Uses the same timeout and retry settings as the chat model. Without an
    explicit timeout the OpenAI SDK waits up to 600 seconds, so a single hung
    embedding call could block a chat request for minutes. The SDK retries
    rate limits, 5xx responses and connection errors with exponential backoff.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error("OpenAI API key is not configured")
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

    logger.info("Initializing embedding model", model="text-embedding-3-small", timeout_seconds=timeout, max_retries=max_retries)

    return OpenAIEmbeddings(model="text-embedding-3-small", request_timeout=timeout, max_retries=max_retries)
