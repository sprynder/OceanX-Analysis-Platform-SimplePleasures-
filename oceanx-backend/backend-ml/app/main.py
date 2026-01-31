# backend-ml/app/main.py
from fastapi import FastAPI
from app.api.process_video import router as process_router
from app.api.cluster_rois import router as cluster_router

app = FastAPI(title="OceanX ML Service")

app.include_router(process_router)
app.include_router(cluster_router)
