from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.db import check_db

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> JSONResponse:
    try:
        journal_mode = await check_db()
    except Exception:
        return JSONResponse({"status": "error", "db": "error"}, status_code=503)
    return JSONResponse({"status": "ok", "db": "ok", "journal_mode": journal_mode})
