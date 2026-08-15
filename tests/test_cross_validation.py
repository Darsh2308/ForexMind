from datetime import datetime

from forexmind.orchestration.cross_validation import cross_validate
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.technical_analysis.schemas import TechnicalAnalysisSnapshot, IndicatorSet
from forexmind.agents.price_action.schemas import PriceActionSnapshot, PriceActionResult, TrendState
from forexmind.agents.elliott_wave.schemas import ElliottWaveSnapshot, ElliottWaveResult, Wave, WaveCount
from forexmind.agents.wyckoff.schemas import WyckoffSnapshot, WyckoffResult, WyckoffPhase


def test_trend_mismatch():
    context = MarketContext(
        generated_at=datetime.now(),
        timeframes=["1h"],
        technical_analysis=TechnicalAnalysisSnapshot(
            as_of="2026-08-08",
            timeframes={"1h": IndicatorSet(trend="bullish")}
        ),
        price_action=PriceActionSnapshot(
            as_of="2026-08-08",
            timeframes={"1h": PriceActionResult(trend=TrendState(direction="bearish"))}
        )
    )
    
    conflicts = cross_validate(context)
    assert len(conflicts) == 1
    assert "Trend Mismatch: Technical Analysis is Bullish, but Price Action is Bearish" in conflicts[0]


def test_advisory_mismatch():
    context = MarketContext(
        generated_at=datetime.now(),
        timeframes=["4h"],
        elliott_wave=ElliottWaveSnapshot(
            as_of="2026-08-08",
            timeframes={"4h": ElliottWaveResult(
                current_count=WaveCount(
                    waves=[Wave(label="3", start_index=0, end_index=10, start_price=1.0, end_price=1.1)]
                )
            )}
        ),
        wyckoff=WyckoffSnapshot(
            as_of="2026-08-08",
            timeframes={"4h": WyckoffResult(
                current_phase=WyckoffPhase(phase="distribution")
            )}
        )
    )
    
    conflicts = cross_validate(context)
    assert len(conflicts) == 1
    assert "Advisory Mismatch: Elliott Wave is Bullish, but Wyckoff Phase is distribution" in conflicts[0]


def test_no_conflicts():
    context = MarketContext(
        generated_at=datetime.now(),
        timeframes=["15min"],
        technical_analysis=TechnicalAnalysisSnapshot(
            as_of="2026-08-08",
            timeframes={"15min": IndicatorSet(trend="bullish")}
        ),
        price_action=PriceActionSnapshot(
            as_of="2026-08-08",
            timeframes={"15min": PriceActionResult(trend=TrendState(direction="bullish"))}
        )
    )
    
    conflicts = cross_validate(context)
    assert len(conflicts) == 0
