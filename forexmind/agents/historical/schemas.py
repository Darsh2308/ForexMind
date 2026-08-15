from pydantic import BaseModel, Field

class SimilarSetup(BaseModel):
    recommendation_id: int
    similarity_score: float
    historical_outcome: str
    created_at: str

class HistoricalSimilaritySnapshot(BaseModel):
    as_of: str
    top_similar: list[SimilarSetup] = Field(default_factory=list)
