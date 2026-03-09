import logging
import uvicorn
from src.core.config import get_config

logger = logging.getLogger(__name__)


def run() -> None:
    """
    Entrypoint of the application.
    """

    config = get_config()
    logger.info(
        f"Starting application on {config.server.host} with port :{config.server.port}, reload={config.server.reload}"
    )

    uvicorn.run(
        "src.app:get_app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        # log_level=config.settings.log_level.value.lower(),
        factory=True,
        forwarded_allow_ips="*",
        proxy_headers=True,
        log_config="logging.json",
    )


if __name__ == "__main__":
    run()
