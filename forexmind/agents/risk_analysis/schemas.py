from pydantic import BaseModel, Field

class TradeSetup(BaseModel):
    """Theoretical parameters for a potential trade setup."""
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    reward_to_risk: float
    invalidation_reason: str | None = None
    """Populated if the setup is structurally unsound (e.g. SL too tight, R:R < 1)."""

class RiskAnalysisSnapshot(BaseModel):
    """Top-level output of the Risk Analysis Agent."""
    as_of: str
    buy_setup: TradeSetup | None = None
    sell_setup: TradeSetup | None = None
    volatility_flag: str | None = None
    """Flagged if ATR suggests highly abnormal conditions (e.g., 'extreme_high' or 'extreme_low')."""
