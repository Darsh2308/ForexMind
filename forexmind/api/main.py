"""FastAPI app skeleton. The real '/recommendation' endpoint is built in
Phase 15 once every agent exists; for now this only proves the stack is wired."""

from __future__ import annotations

from fastapi import FastAPI

from forexmind.logging_config import setup_logging

setup_logging()

app = FastAPI(title="ForexMind AI", version="0.0.1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
