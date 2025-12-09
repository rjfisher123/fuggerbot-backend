import json
import os
import logging
import re
from typing import Optional, Dict, Any
from pydantic import ValidationError
from openai import OpenAI

from reasoning.schemas import TradeContext, DeepSeekResponse, ReasoningDecision

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FuggerReasoning")


class DeepSeekEngine:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-reasoner"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _get_system_prompt(self, red_team_mode: bool) -> str:
        base_persona = (
            "You are the Senior Risk Officer for a quantitative trading fund. "
            "Your sole purpose is to validate statistical forecasts against broader logic and safety criteria."
        )
        
        if red_team_mode:
            return (
                f"{base_persona} "
                "CURRENT MODE: RED TEAM / ADVERSARIAL.\n"
                "The market is volatile. You must act as a hostile reviewer.\n"
                "1. Assume the forecast is overfitting.\n"
                "2. Look for ANY reason to REJECT the trade.\n"
                "3. Only APPROVE if the setup is virtually flawless.\n"
                "4. If 'Memory Summary' shows a losing streak, reject all marginal trades."
            )
        else:
            return (
                f"{base_persona} "
                "CURRENT MODE: STANDARD.\n"
                "Balance profit opportunity with risk management.\n"
                "1. If 'Regret Rate' in memory is high, loosen your criteria slightly.\n"
                "2. Ensure the Risk/Reward ratio is logical."
            )

    def _clean_json_response(self, raw_content: str) -> str:
        """
        Robust cleaning for Reasoning models (DeepSeek R1).
        Removes <think> tags, markdown fences, and conversational filler.
        """
        if not raw_content:
            return "{}"

        # 1. Remove <think>...</think> blocks (DeepSeek R1 specific)
        # Use DOTALL to match across newlines
        cleaned = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
        
        # 2. Extract JSON from Markdown fences if present
        json_match = re.search(r'```json\s*({.*?})\s*```', cleaned, re.DOTALL)
        if json_match:
            return json_match.group(1)
            
        # 3. Fallback: Try to find the first '{' and last '}'
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            return cleaned[start:end+1]
            
        return cleaned

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fixes common LLM data type errors before Pydantic validation.
        """
        # Fix Decision Casing (e.g. "Approve" -> "APPROVE")
        if "decision" in data and isinstance(data["decision"], str):
            data["decision"] = data["decision"].upper()
            # Map synonyms
            if "BUY" in data["decision"]: data["decision"] = "APPROVE"
            if "SELL" in data["decision"]: data["decision"] = "REJECT"
            if "HOLD" in data["decision"]: data["decision"] = "WAIT"

        # Fix Confidence Scale (e.g. 85 -> 0.85)
        if "confidence" in data:
            try:
                conf = float(data["confidence"])
                if conf > 1.0:
                    data["confidence"] = conf / 100.0
            except:
                pass
        
        # Fix risk_analysis: Convert dict to string if needed
        if "risk_analysis" in data and isinstance(data["risk_analysis"], dict):
            # Convert dict to formatted string
            risk_dict = data["risk_analysis"]
            risk_parts = []
            for key, value in risk_dict.items():
                if isinstance(value, float):
                    risk_parts.append(f"{key}: {value:.4f}")
                else:
                    risk_parts.append(f"{key}: {value}")
            data["risk_analysis"] = "; ".join(risk_parts)
        
        # Fix rationale: Convert dict to string if needed
        if "rationale" in data and isinstance(data["rationale"], dict):
            # Convert dict to formatted string
            rationale_dict = data["rationale"]
            rationale_parts = []
            for key, value in rationale_dict.items():
                if isinstance(value, float):
                    rationale_parts.append(f"{key}: {value:.4f}")
                else:
                    rationale_parts.append(f"{key}: {value}")
            data["rationale"] = "; ".join(rationale_parts)
                
        return data

    def analyze_trade(self, context: TradeContext, red_team_mode: bool = False) -> Optional[DeepSeekResponse]:
        system_prompt = self._get_system_prompt(red_team_mode)
        
        user_message = (
            f"Analyze this Trade Setup:\n"
            f"Symbol: {context.symbol} @ ${context.price}\n"
            f"Forecast: Target ${context.forecast_target} (Conf: {context.forecast_confidence:.2f})\n"
            f"Trust Score: {context.trust_score:.2f}\n"
            f"Volatility Data: {context.volatility_metrics}\n\n"
            f"{context.memory_summary}\n\n"
            "Respond in strictly valid JSON with keys: decision, confidence, risk_analysis, rationale."
        )

        raw_content = ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1 if red_team_mode else 0.4,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
            
            # 1. Clean String
            clean_json = self._clean_json_response(raw_content)
            
            # 2. Parse JSON
            data = json.loads(clean_json)
            
            # 3. Handle List vs Dict (common API quirk)
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    raise ValueError("Empty list returned by LLM")

            # 4. Sanitize Values (Fix strict types)
            data = self._sanitize_data(data)

            # 5. Validate with Pydantic
            decision_obj = DeepSeekResponse(**data)
            
            # Safety Logic
            if decision_obj.decision == ReasoningDecision.APPROVE:
                if not decision_obj.is_actionable():
                    logger.warning(f"Trade Approved by LLM but confidence {decision_obj.confidence} below threshold.")
                    decision_obj.decision = ReasoningDecision.WAIT
            
            return decision_obj

        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            # EXTENSIVE LOGGING FOR DEBUGGING
            logger.error("="*40)
            logger.error(f"❌ LLM PARSING ERROR: {e}")
            logger.error(f"RAW CONTENT START:\n{raw_content}")
            logger.error("RAW CONTENT END")
            logger.error("="*40)
            
            return DeepSeekResponse(
                decision=ReasoningDecision.REJECT,
                confidence=1.0,
                risk_analysis="System Error: Parsing Failed",
                rationale=f"Error parsing LLM response. Check logs for raw output."
            )
        except Exception as e:
            logger.error(f"Critical API Error: {e}")
            return None


# Backward compatibility: Singleton pattern and settings integration
_deepseek_engine: Optional[DeepSeekEngine] = None


def get_deepseek_engine(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None
) -> DeepSeekEngine:
    """
    Get or create a singleton DeepSeek engine instance.
    
    For backward compatibility with existing code that uses settings.
    """
    global _deepseek_engine
    
    if _deepseek_engine is None:
        # Try to load from settings if not provided
        if not api_key:
            try:
                from config import get_settings
                settings = get_settings()
                api_key = settings.openrouter_api_key
                model_name = model_name or settings.deepseek_model
                base_url = base_url or "https://openrouter.ai/api/v1"
            except Exception as e:
                logger.warning(f"Could not load settings, using env vars: {e}")
                api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
                model_name = model_name or os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-r1")
                base_url = base_url or "https://api.deepseek.com/v1"
        
        if not api_key:
            raise ValueError(
                "API key not found. Set OPENROUTER_API_KEY in your .env file "
                "or pass it as a parameter."
            )
        
        _deepseek_engine = DeepSeekEngine(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
            model=model_name or "deepseek/deepseek-r1"
        )
    
    return _deepseek_engine
