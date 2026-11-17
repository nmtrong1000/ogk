from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse


def register(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    async def dashboard(path: str):
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file = (root / path).resolve()
        if file.is_relative_to(root) and file.is_file():
            return FileResponse(file)
        return FileResponse(index)
