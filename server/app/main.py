from fastapi import FastAPI
from app.config import settings

app = FastAPI(title=settings.app_name)

@app.get("/")
def read_root():
    return {
        "app_name": settings.app_name,
        "debug": settings.app_debug
    }