from pydantic import BaseModel

class ProcessVideoRequest(BaseModel):
    video_id: str
    video_path: str