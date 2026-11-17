from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Lỗi trả về client dạng {"detail": code, ...extra}."""

    def __init__(self, status: int, code: str, headers: dict[str, str] | None = None, **extra) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.headers = headers
        self.extra = extra


async def _handle(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse({"detail": exc.code, **exc.extra}, status_code=exc.status, headers=exc.headers)


def register(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle)
