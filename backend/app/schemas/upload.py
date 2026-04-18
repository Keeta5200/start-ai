from pydantic import BaseModel


class UploadResponse(BaseModel):
    analysis_id: str
    status: str
