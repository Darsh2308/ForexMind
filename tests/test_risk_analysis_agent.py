from datetime import datetime, timezone
import pytest

from forexmind.agents.risk_analysis.risk_analysis_agent import RiskAnalysisAgent
from forexmind.agents.market_data.schemas import MarketDataSnapshot, SessionState, Candle
from forexmind.agents.technical_analysis.schemas import TechnicalAnalysisSnapshot, IndicatorSet
from forexmind.agents.smc.schemas import SMCSnapshot, SMCResult, OrderBlock
from forexmind.agents.support_resistance.schemas import SupportResistanceSnapshot, SupportResistanceResult, PriceLevel
from forexmind.orchestration.market_context import MarketContext

@pytest.fixture
def base_context():
    return MarketContext(
        generated_at=datetime.now(timezone.utc),
        symbol="EUR/USD",
        timeframes=["1h"],
        market_data=MarketDataSnapshot(
            as_of="2026-08-08T12:00:00+00:00",
            is_live=False,
            latest_price=1.1000,
            sessions=SessionState()
        ),
        technical_analysis=TechnicalAnalysisSnapshot(
            as_of="2026-08-08T12:00:00+00:00",
            timeframes={
                "1h": IndicatorSet(atr_14=0.0020) # 20 pips ATR
            }
        ),
        smc=SMCSnapshot(
            as_of="2026-08-08T12:00:00+00:00",
            timeframes={
                "1h": SMCResult(
                    order_blocks=[
                        OrderBlock(direction="bullish", top=1.0960, bottom=1.0950, candle_index=0, timestamp="2026", mitigated=False),
                        OrderBlock(direction="bearish", top=1.1060, bottom=1.1050, candle_index=0, timestamp="2026", mitigated=False)
                    ]
                )
            }
        ),
        support_resistance=SupportResistanceSnapshot(
            as_of="2026-08-08T12:00:00+00:00",
            timeframes={
                "1h": SupportResistanceResult(
                    support_levels=[
                        PriceLevel(price=1.0900, type="horizontal", strength="strong", touch_count=3)
                    ],
                    resistance_levels=[
                        PriceLevel(price=1.1100, type="horizontal", strength="strong", touch_count=3)
                    ]
                )
            }
        )
    )

def test_risk_analysis_valid_buy_setup(base_context):
    agent = RiskAnalysisAgent()
    # Adjust mock to make a valid BUY setup
    # Current = 1.1000
    # Bullish OB at 1.0955 (highest support < current) -> SL = 1.0955 - (0.5 * 0.0020) = 1.0945 (Distance: 55 pips)
    # Bearish OB at 1.1055 (lowest resistance > current) -> TP = 1.1055 - (0.5 * 0.0020 / 2) = 1.1050 (Distance: 50 pips)
    # R:R = 50 / 55 = 0.9 (Wait, that's < 1.0, so it will be invalid!)
    
    # Let's adjust TP up to make R:R > 1
    base_context.smc.timeframes["1h"].order_blocks[1] = OrderBlock(direction="bearish", top=1.1160, bottom=1.1150, candle_index=0, timestamp="2026", mitigated=False)
    base_context.support_resistance.timeframes["1h"].resistance_levels[0].price = 1.1200
    # Bearish OB is now 1.1155. TP = 1.1155 - 0.0005 = 1.1150 (Distance: 115 pips). R:R = 115 / 55 = ~2.1
    
    snapshot = agent.analyze(base_context)
    
    buy = snapshot.buy_setup
    assert buy is not None
    assert buy.direction == "BUY"
    assert buy.entry == 1.1000
    assert buy.stop_loss == 1.0945
    assert buy.take_profit == 1.1150
    assert buy.reward_to_risk > 2.0
    assert buy.invalidation_reason is None

def test_risk_analysis_invalid_rr(base_context):
    agent = RiskAnalysisAgent()
    # Base mock has TP at 1.1055, SL at 1.0955. 
    # SL distance = 55 pips, TP distance = 50 pips. R:R = 0.9.
    
    snapshot = agent.analyze(base_context)
    buy = snapshot.buy_setup
    assert buy is not None
    assert buy.invalidation_reason == "R:R < 1.0"

def test_risk_analysis_sl_too_tight(base_context):
    agent = RiskAnalysisAgent()
    # SL is too tight if distance < 0.5 * ATR (10 pips).
    # Current = 1.1000. Make a bullish OB at 1.0995 (5 pips away).
    base_context.smc.timeframes["1h"].order_blocks[0] = OrderBlock(direction="bullish", top=1.0995, bottom=1.0995, candle_index=0, timestamp="2026", mitigated=False)
    
    # SL will be 1.0995 - 0.0010 = 1.0985. Distance is 15 pips (1.1000 - 1.0985).
    # 0.5 ATR = 10 pips. So 15 pips is > 10 pips. Wait, let's make it tighter.
    # Bullish OB at 1.1005 (Wait, that's above current, so it won't be picked for BUY).
    # Bullish OB at 1.1000. SL = 1.1000 - 0.0010 = 1.0990. Distance = 10 pips.
    # Let's change ATR to 50 pips (0.0050).
    base_context.technical_analysis.timeframes["1h"].atr_14 = 0.0050
    # Bullish OB at 1.0995. SL = 1.0995 - 0.0025 = 1.0970. Distance = 30 pips.
    # Min SL = 0.5 * 50 = 25 pips. Still valid!
    # Let's just make the OB at 1.0998, ATR = 100 pips (0.0100).
    base_context.technical_analysis.timeframes["1h"].atr_14 = 0.0100
    base_context.smc.timeframes["1h"].order_blocks[0] = OrderBlock(direction="bullish", top=1.0998, bottom=1.0998, candle_index=0, timestamp="2026", mitigated=False)
    
    # SL = 1.0998 - 0.0050 = 1.0948. Distance = 52 pips.
    # Min SL = 0.5 * 100 = 50 pips. Valid.
    # Okay, let's just make min_atr_sl_mult higher to test it easily.
    agent.min_atr_sl_mult = 1.0
    # SL distance = 52 pips. Min SL = 1.0 * 100 = 100 pips.
    
    snapshot = agent.analyze(base_context)
    buy = snapshot.buy_setup
    assert buy.invalidation_reason == "SL too tight (< 1.0 ATR)"

def test_risk_analysis_sl_too_wide(base_context):
    agent = RiskAnalysisAgent()
    # Current = 1.1000
    # Make support very far away. 
    base_context.smc.timeframes["1h"].order_blocks = []
    base_context.support_resistance.timeframes["1h"].support_levels[0].price = 1.0000 # 1000 pips away
    # ATR = 20 pips (0.0020). Max SL = 3.0 * ATR = 60 pips.
    
    snapshot = agent.analyze(base_context)
    buy = snapshot.buy_setup
    assert buy.invalidation_reason == "SL too wide (> 3.0 ATR)"
