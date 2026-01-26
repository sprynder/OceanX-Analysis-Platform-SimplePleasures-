# backend-ml/app/main.py
from fastapi import FastAPI
from app.api.process_video import router as process_router

app = FastAPI(title="OceanX ML Service")

app.include_router(process_router)
