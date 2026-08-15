import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any

from forexmind.agents.historical.schemas import HistoricalSimilaritySnapshot, SimilarSetup
from forexmind.orchestration.market_context import MarketContext
from forexmind.storage.db import fetch_historical_setups

class HistoricalSimilarityAgent:
    """Finds mathematically similar setups in the historical database."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _extract_features(self, context_dict: dict[str, Any]) -> list[float]:
        """
        Extracts a normalized mathematical feature vector [-1.0 to 1.0] from a MarketContext dictionary.
        Vector layout: [trend, rsi, smc, support_resistance]
        """
        features = [0.0, 0.0, 0.0, 0.0]

        # 1. Trend
        ta = context_dict.get("technical_analysis")
        if ta and isinstance(ta, dict):
            timeframes = ta.get("timeframes", {})
            if timeframes:
                first_tf = list(timeframes.values())[0]
                trend_val = first_tf.get("trend", "ranging")
                if trend_val == "bullish":
                    features[0] = 1.0
                elif trend_val == "bearish":
                    features[0] = -1.0

                rsi = first_tf.get("rsi_14")
                if rsi is not None:
                    if rsi > 70:
                        features[1] = -1.0 # Bearish signal
                    elif rsi < 30:
                        features[1] = 1.0  # Bullish signal

        # 3. SMC
        smc = context_dict.get("smc")
        if smc and isinstance(smc, dict):
            timeframes = smc.get("timeframes", {})
            if timeframes:
                first_tf = list(timeframes.values())[0]
                pois = first_tf.get("pois", [])
                for poi in pois:
                    poi_type = poi.get("type", "")
                    if "bullish" in poi_type.lower():
                        features[2] = 1.0
                        break
                    elif "bearish" in poi_type.lower():
                        features[2] = -1.0
                        break

        # 4. Support/Resistance
        sr = context_dict.get("support_resistance")
        if sr and isinstance(sr, dict):
            timeframes = sr.get("timeframes", {})
            if timeframes:
                first_tf = list(timeframes.values())[0]
                levels = first_tf.get("levels", [])
                # Look for extreme proximity
                for lvl in levels:
                    dist = lvl.get("distance_pips", 999)
                    if dist < 10:
                        if lvl.get("level_type") == "support":
                            features[3] = 1.0
                            break
                        elif lvl.get("level_type") == "resistance":
                            features[3] = -1.0
                            break

        return features

    def _euclidean_distance(self, v1: list[float], v2: list[float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _calculate_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Returns similarity from 0.0 (opposite) to 1.0 (identical)."""
        dist = self._euclidean_distance(v1, v2)
        # Max possible distance is sqrt(4 * 2^2) = 4.0
        max_dist = 4.0
        return max(0.0, 1.0 - (dist / max_dist))

    def analyze(self, current_context: MarketContext) -> HistoricalSimilaritySnapshot:
        """Compares the current context to historical snapshots and returns top matches."""
        current_features = self._extract_features(current_context.model_dump())
        
        # Fetch history
        rows = fetch_historical_setups(self.conn, limit=1000)
        
        scored_setups = []
        for row in rows:
            try:
                hist_context_dict = json.loads(row["market_context_json"])
                hist_features = self._extract_features(hist_context_dict)
                sim = self._calculate_similarity(current_features, hist_features)
                
                scored_setups.append(SimilarSetup(
                    recommendation_id=row["recommendation_id"],
                    similarity_score=round(sim, 4),
                    historical_outcome=row["status"],
                    created_at=row["created_at"]
                ))
            except Exception:
                continue

        # Sort by highest similarity
        scored_setups.sort(key=lambda x: x.similarity_score, reverse=True)
        top_n = scored_setups[:3]

        return HistoricalSimilaritySnapshot(
            as_of=datetime.now(timezone.utc).isoformat(),
            top_similar=top_n
        )
