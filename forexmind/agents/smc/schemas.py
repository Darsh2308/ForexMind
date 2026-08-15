from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FairValueGap(BaseModel):
    """A 3-candle imbalance (FVG)."""

    direction: Literal["bullish", "bearish"]
    top: float
    bottom: float
    candle_index: int  # Index of the 3rd candle that confirmed the gap
    timestamp: str
    mitigated: bool = False


class MarketStructureShift(BaseModel):
    """Break of Structure (BOS) or Change of Character (CHOCH)."""

    type: Literal["BOS", "CHOCH"]
    direction: Literal["bullish", "bearish"]
    level: float
    candle_index: int
    timestamp: str


class OrderBlock(BaseModel):
    """An institutional order block."""

    direction: Literal["bullish", "bearish"]
    top: float
    bottom: float
    candle_index: int
    timestamp: str
    mitigated: bool = False


class LiquidityPool(BaseModel):
    """A concentration of stop losses (e.g. Equal Highs, Equal Lows, Major Swings)."""

    type: Literal["EQH", "EQL", "swing_high", "swing_low"]
    price: float
    touches: int
    candle_indices: list[int]
    swept: bool = False


class LiquiditySweep(BaseModel):
    """A wick extending beyond a liquidity pool followed by a rejection."""

    direction: Literal["bullish", "bearish"]  # Bullish sweep takes out EQL/swing_low
    pool_type: Literal["EQH", "EQL", "swing_high", "swing_low"]
    sweep_price: float
    candle_index: int
    timestamp: str


class DealingRange(BaseModel):
    """The current active impulsive leg for measuring Premium/Discount and OTE."""

    swing_high: float
    swing_low: float
    equilibrium: float
    ote_high: float
    ote_low: float
    current_zone: Literal["premium", "discount", "equilibrium"]


class SMCResult(BaseModel):
    """The SMC/ICT analysis for a single timeframe."""

    fvgs: list[FairValueGap] = Field(default_factory=list)
    structure_shifts: list[MarketStructureShift] = Field(default_factory=list)
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    liquidity_pools: list[LiquidityPool] = Field(default_factory=list)
    liquidity_sweeps: list[LiquiditySweep] = Field(default_factory=list)
    dealing_range: DealingRange | None = None


class SMCSnapshot(BaseModel):
    """A multi-timeframe snapshot of SMC concepts."""

    as_of: str | None = None
    timeframes: dict[str, SMCResult] = Field(default_factory=dict)
