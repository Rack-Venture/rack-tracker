import os

import uvicorn

from config.config import HOST, PORT


def _is_reload_enabled() -> bool:
    return os.getenv("RELOAD", "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    uvicorn.run(
        app="app:app",
        host=HOST,
        port=PORT,
        reload=_is_reload_enabled(),
    )


if __name__ == "__main__":
    main()
