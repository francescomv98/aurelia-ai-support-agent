import os
from langchain_openai import OpenAIEmbeddings
from src.app_logging.logger import logger

def create_embeddings() -> OpenAIEmbeddings:
    """Create the OpenAI embeddings model."""

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error("OpenAI API key is not configured")
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    logger.info("Initializing embedding model", model="text-embedding-3-small")

    return OpenAIEmbeddings(model="text-embedding-3-small")