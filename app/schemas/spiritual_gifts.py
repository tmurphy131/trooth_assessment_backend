from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class SpiritualGiftsSubmission(BaseModel):
    template_key: str = Field(..., description="Must be 'spiritual_gifts_v1' for this version")
    answers: Dict[str, int]

class GiftScore(BaseModel):
    gift: str
    score: int

class SpiritualGiftsResult(BaseModel):
    id: str
    apprentice_id: str
    template_key: str
    version: int
    created_at: datetime
    top_gifts_truncated: List[GiftScore]
    top_gifts_expanded: List[GiftScore]
    all_scores: List[GiftScore]
    rank_meta: Dict[str, Optional[int]]

class SpiritualGiftsLatestResponse(BaseModel):
    overall: Optional[int] = Field(None, description="Placeholder if future aggregate needed")
    top_gifts_truncated: List[GiftScore]
    completed_at: datetime
    version: str
