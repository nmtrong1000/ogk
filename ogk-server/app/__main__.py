import ssl
import sys

import uvicorn

from app.core.config import ConfigError, get_settings
from app.main import create_app


def main() -> None:
    try:
        settings = get_settings()
    except ConfigError as exc:
        sys.exit(str(exc))

    config = uvicorn.Config(
        create_app(),
        host=settings.host,
        port=settings.port,
        ssl_certfile=str(settings.tls_cert),
        ssl_keyfile=str(settings.tls_key),
    )
    config.load()
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
