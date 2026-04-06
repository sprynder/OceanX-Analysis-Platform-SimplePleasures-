# backend-ml/app/main.py
from fastapi import FastAPI
from app.api.process_video import router as process_router
from app.api.cluster_rois import router as cluster_router
from app.api.search_rois import router as search_router
from app.api.global_view import router as global_router

app = FastAPI(title="OceanX ML Service")

app.include_router(process_router)
app.include_router(cluster_router)
app.include_router(search_router)
app.include_router(global_router)
