from datetime import datetime, timezone

from forexmind.agents.market_data.schemas import MarketDataSnapshot, SessionState
from forexmind.agents.technical_analysis.schemas import TechnicalAnalysisSnapshot
from forexmind.orchestration.market_context import MarketContext


def test_default_context_has_no_populated_sections():
    ctx = MarketContext(generated_at=datetime.now(timezone.utc))
    assert ctx.symbol == "EUR/USD"
    assert ctx.populated_sections() == []


def test_populated_sections_reflects_filled_fields():
    market_data = MarketDataSnapshot(
        as_of=datetime.now(timezone.utc).isoformat(),
        is_live=True,
        latest_price=1.0959,
        sessions=SessionState(),
    )
    ta_snapshot = TechnicalAnalysisSnapshot(
        as_of=datetime.now(timezone.utc).isoformat(),
    )
    ctx = MarketContext(
        generated_at=datetime.now(timezone.utc),
        market_data=market_data,
        technical_analysis=ta_snapshot,
    )
    assert ctx.populated_sections() == ["market_data", "technical_analysis"]
    assert ctx.market_data.latest_price == 1.0959


def test_conflicts_default_to_empty_list():
    ctx = MarketContext(generated_at=datetime.now(timezone.utc))
    assert ctx.conflicts == []

    ctx.conflicts.append("Price action bullish breakout vs SMC premium-zone rejection")
    assert len(ctx.conflicts) == 1
