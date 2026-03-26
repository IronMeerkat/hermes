from api.asgi import app
from logging import getLogger
import uvicorn

logger = getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting Hermes")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)