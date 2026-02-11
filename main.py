from api.asgi import app
from logging import getLogger
import uvicorn

from hephaestus.logging import init_logger

logger = getLogger(__name__)

init_logger()
if __name__ == "__main__":
    logger.info("Starting Hermes")
    uvicorn.run(app, host="0.0.0.0", port=8000)