from typing import Any, Optional
from uuid import UUID

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalysisScores(BaseModel):
    start_posture: float
    push_direction: float
    first_step_landing: float
    ground_contact: float
    forward_com: float
    arm_leg_coordination: float


class AnalysisResultPayload(BaseModel):
    final_score: float
    scores: AnalysisScores
    score_details: dict[str, Any] = Field(default_factory=dict)
    primary_diagnosis: Optional[str] = None
    feedback: dict[str, Any] = Field(default_factory=dict)
    debug_metrics: dict[str, Any] = Field(default_factory=dict)
    deduction_reasons: dict[str, list[str]] = Field(default_factory=dict)


class AnalysisListItem(BaseModel):
    id: UUID
    status: str
    score: float
    video_filename: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisDetailResponse(AnalysisListItem):
    step_count: int
    result_payload: Optional[AnalysisResultPayload] = None
