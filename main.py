from fastapi import FastAPI
from src.api.routes.auth import router as auth_router
from src.api.routes.chat import router as chat_router
from src.logging.logger import configure_logging, logger

configure_logging()

app = FastAPI(
    title="Aurelia AI Support Agent",
    description="Enterprise AI support agent for Aurelia Industrial Systems.",
    version="0.1.0"
)

app.include_router(auth_router)
app.include_router(chat_router)

logger.info("Aurelia AI Support Agent starting")