"""
Trade post-mortem engine.

Uses the LLM to critique closed trades and produce a structured post-mortem report.
"""
import json
import logging
from typing import Dict, Any

from config.settings import get_settings
from reasoning.engine import DeepSeekEngine
from reasoning.schemas import PostMortemReport, AnalysisOutcome
from reasoning.memory import TradeMemory

logger = logging.getLogger(__name__)


class TradeCoroner:
    """
    LLM wrapper that critiques closed trades and produces a PostMortemReport.
    """

    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.engine = DeepSeekEngine(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            model=settings.deepseek_model,
        )
        self.memory = TradeMemory()

    def conduct_review(self, trade_data: Dict[str, Any]) -> PostMortemReport:
        """
        Analyze a closed trade and return a structured post-mortem.

        Args:
            trade_data: dictionary with keys like symbol, rationale, confidence, pnl, outcome, trade_id.

        Returns:
            PostMortemReport instance.
        """
        symbol = trade_data.get("symbol", "UNKNOWN")
        rationale = trade_data.get("rationale", "No rationale provided.")
        confidence = trade_data.get("confidence", 0.0)
        pnl = trade_data.get("pnl", 0.0)
        outcome = trade_data.get("outcome", "UNKNOWN")
        trade_id = trade_data.get("trade_id", "unknown")

        system_prompt = (
            "You are a Trading Performance Coach. "
            "You analyze closed trades to find logic gaps. Be harsh. "
            "If a trade lost, find the flaw in the original reasoning. "
            "If it won, verify if it won for the right reason or just luck."
        )

        user_prompt = (
            f"Original Trade: {symbol} BUY.\n"
            f"Original Thesis: {rationale}\n"
            f"Original Confidence: {confidence}\n"
            f"Actual Result: {pnl} ({outcome})\n\n"
            "Analyze the gap between thesis and reality.\n"
            "Respond in JSON with keys: trade_id, actual_outcome, outcome_category, "
            "root_cause, lesson_learned, adjusted_confidence."
        )

        raw_content = ""
        try:
            response = self.engine.client.chat.completions.create(
                model=self.engine.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content

            clean_json = self.engine._clean_json_response(raw_content)  # type: ignore
            data = json.loads(clean_json)
            if isinstance(data, list) and data:
                data = data[0]

            normalized = self._normalize_report_data(
                data,
                trade_id=trade_id,
                outcome=outcome,
                pnl=pnl,
                confidence=confidence,
            )

            report = PostMortemReport(**normalized)
            return report

        except Exception as e:
            logger.error("Post-mortem parsing failed: %s", e, exc_info=True)
            # Safe fallback
            return PostMortemReport(
                trade_id=trade_id,
                actual_outcome=outcome,
                outcome_category=AnalysisOutcome.MODEL_HALLUCINATION,
                root_cause="Parsing failure in post-mortem analysis.",
                lesson_learned="Review LLM output formatting.",
                adjusted_confidence=max(0.0, min(1.0, float(confidence) if confidence else 0.0)),
            )

    @staticmethod
    def _normalize_report_data(
        data: Dict[str, Any],
        trade_id: str,
        outcome: str,
        pnl: Any,
        confidence: Any,
    ) -> Dict[str, Any]:
        """
        Normalize raw LLM output into a shape that PostMortemReport can accept.
        """
        normalized: Dict[str, Any] = dict(data) if data else {}

        # Trade ID
        normalized["trade_id"] = normalized.get("trade_id", trade_id)

        # Actual outcome: ensure string and map from pnl if needed
        actual_outcome = normalized.get("actual_outcome", outcome)
        if not isinstance(actual_outcome, str):
            try:
                pnl_val = float(actual_outcome)
                if pnl_val > 0:
                    actual_outcome = "WIN"
                elif pnl_val < 0:
                    actual_outcome = "LOSS"
                else:
                    actual_outcome = "BREAKEVEN"
            except Exception:
                try:
                    pnl_val = float(pnl)
                    if pnl_val > 0:
                        actual_outcome = "WIN"
                    elif pnl_val < 0:
                        actual_outcome = "LOSS"
                    else:
                        actual_outcome = "BREAKEVEN"
                except Exception:
                    actual_outcome = "UNKNOWN"
        normalized["actual_outcome"] = str(actual_outcome)

        # Outcome category: normalize to enum; map common synonyms
        raw_category = normalized.get("outcome_category", "")
        if isinstance(raw_category, str):
            cat = raw_category.upper().replace(" ", "_")
            synonym_map = {
                "WIN_DUE_TO_LUCK": AnalysisOutcome.LUCK.value,
                "BREAKEVEN": AnalysisOutcome.VALIDATED_THESIS.value,
                "NEUTRAL": AnalysisOutcome.VALIDATED_THESIS.value,
                "AVOIDED_LOSS": AnalysisOutcome.VALIDATED_THESIS.value,
                "PROFIT": AnalysisOutcome.VALIDATED_THESIS.value,
                "LOSS": AnalysisOutcome.BAD_TIMING.value,
                "RISK_MISMATCH": AnalysisOutcome.MODEL_HALLUCINATION.value,
            }
            cat = synonym_map.get(cat, cat)
        else:
            cat = AnalysisOutcome.MODEL_HALLUCINATION.value

        if cat not in {c.value for c in AnalysisOutcome}:
            cat = AnalysisOutcome.MODEL_HALLUCINATION.value
        normalized["outcome_category"] = cat

        # Root cause
        normalized["root_cause"] = normalized.get(
            "root_cause",
            "LLM did not provide a root cause."
        )

        # Lesson learned
        normalized["lesson_learned"] = normalized.get(
            "lesson_learned",
            "No lesson provided."
        )

        # Adjusted confidence clamped to [0,1]
        adj_conf = normalized.get("adjusted_confidence", confidence)
        try:
            adj_conf = float(adj_conf)
        except Exception:
            adj_conf = 0.0
        normalized["adjusted_confidence"] = max(0.0, min(1.0, adj_conf))

        return normalized

