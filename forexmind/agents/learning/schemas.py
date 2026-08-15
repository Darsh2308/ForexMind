from pydantic import BaseModel

class LearningSnapshot(BaseModel):
    """Statistical memory of similar setups to feed into Reasoning Agent confidence."""
    segment_key: str
    win_rate_30d: float | None = None
    win_rate_90d: float | None = None
    win_rate_lifetime: float | None = None
    confidence_modifier: float = 0.0
    total_trades_analyzed: int = 0
