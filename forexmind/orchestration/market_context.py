"""The blackboard: a single shared-state object every agent reads from and
writes a section of. The Reasoning Agent (Phase 12) is the only consumer of
the *whole* object; every other agent only touches its own section plus
whatever upstream sections it depends on.

`market_data` has a fixed shape now that Phase 1 (Market Data Agent) exists.
`technical_analysis` was locked in Phase 2 (Technical Analysis Agent).
`price_action` and `candlestick` were locked in Phase 3.
The remaining `agent_key` fields stay open dicts - their shape gets fixed the
same way as each agent is built (Phases 4-11). Locking a shape before its
agent exists would mean guessing at fields nothing produces yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from forexmind.agents.candlestick.schemas import CandlestickSnapshot
from forexmind.agents.market_data.schemas import MarketDataSnapshot
from forexmind.agents.price_action.schemas import PriceActionSnapshot
from forexmind.agents.smc.schemas import SMCSnapshot
from forexmind.agents.support_resistance.schemas import SupportResistanceSnapshot
from forexmind.agents.technical_analysis.schemas import TechnicalAnalysisSnapshot

from forexmind.agents.elliott_wave.schemas import ElliottWaveSnapshot
from forexmind.agents.wyckoff.schemas import WyckoffSnapshot
from forexmind.agents.news.schemas import NewsSnapshot
from forexmind.agents.historical.schemas import HistoricalSimilaritySnapshot
from forexmind.agents.risk_analysis.schemas import RiskAnalysisSnapshot
from forexmind.agents.learning.schemas import LearningSnapshot
from forexmind.agents.reasoning.schemas import ReasoningSnapshot


class MarketContext(BaseModel):
    generated_at: datetime
    symbol: str = "EUR/USD"
    timeframes: list[str] = Field(default_factory=list)

    market_data: MarketDataSnapshot | None = None
    technical_analysis: TechnicalAnalysisSnapshot | None = None
    price_action: PriceActionSnapshot | None = None
    candlestick: CandlestickSnapshot | None = None
    support_resistance: SupportResistanceSnapshot | None = None
    smc: SMCSnapshot | None = None
    elliott_wave: ElliottWaveSnapshot | None = None
    wyckoff: WyckoffSnapshot | None = None
    news: NewsSnapshot | None = None
    historical_similarity: HistoricalSimilaritySnapshot | None = None
    risk_analysis: RiskAnalysisSnapshot | None = None
    learning_metrics: LearningSnapshot | None = None

    conflicts: list[str] = Field(default_factory=list)
    reasoning_output: ReasoningSnapshot | None = None

    def populated_sections(self) -> list[str]:
        sections = [
            "market_data",
            "technical_analysis",
            "price_action",
            "candlestick",
            "support_resistance",
            "smc",
            "elliott_wave",
            "wyckoff",
            "news",
            "historical_similarity",
            "risk_analysis",
            "reasoning_output",
        ]
        return [name for name in sections if getattr(self, name) is not None]
