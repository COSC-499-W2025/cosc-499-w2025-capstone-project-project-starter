from __future__ import annotations

from fastapi import Depends, FastAPI

from src.api.deps import get_store
from src.api.routers import api_router
from src.insights.storage import ProjectInsightsStore

app = FastAPI(title="Project Insights API")
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/runs")
def list_runs(store: ProjectInsightsStore = Depends(get_store)):
    return store.list_recent_zipfiles()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000)
