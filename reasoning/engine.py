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
    
    def _get_adversarial_prompt(self, thesis: str) -> str:
        """
        Generate adversarial critique prompt for Red Team persona.
        
        Args:
            thesis: Initial trading thesis to critique
        
        Returns:
            Adversarial prompt string
        """
        return (
            "You are a RED TEAM adversarial risk analyst. Your job is to find flaws in trading theses.\n\n"
            f"TRADING THESIS TO CRITIQUE:\n{thesis}\n\n"
            "INSTRUCTIONS:\n"
            "1. Find AT LEAST 3 specific flaws, risks, or weaknesses in this thesis.\n"
            "2. Be harsh but fair. Look for:\n"
            "   - Overconfidence in forecasts\n"
            "   - Ignored risk factors\n"
            "   - Historical precedents that contradict the thesis\n"
            "   - Market regime mismatches\n"
            "   - Data quality issues\n"
            "3. Rate the severity of each flaw (LOW, MEDIUM, HIGH, CRITICAL).\n"
            "4. Provide a revised confidence score (0.0 to 1.0) accounting for these flaws.\n\n"
            "Respond in JSON format with:\n"
            "- flaws: [list of flaw objects with 'description' and 'severity']\n"
            "- revised_confidence: float (0.0 to 1.0)\n"
            "- critique_summary: string"
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
        """
        Analyze trade with adversarial critique loop (v1.5).
        
        Step A: Generate initial thesis (Thinking Mode)
        Step B: Pass thesis to Red Team for critique
        Step C: Final synthesis into JSON decision
        
        Records proposer_confidence vs final_confidence for metrics.
        """
        # Step A: Generate initial thesis
        logger.info(f"[Step A] Generating initial thesis for {context.symbol}...")
        
        proposer_prompt = (
            f"Analyze this Trade Setup:\n"
            f"Symbol: {context.symbol} @ ${context.price}\n"
            f"Forecast: Target ${context.forecast_target} (Conf: {context.forecast_confidence:.2f})\n"
            f"Trust Score: {context.trust_score:.2f}\n"
            f"Volatility Data: {context.volatility_metrics}\n\n"
            f"{context.memory_summary}\n\n"
            "Think through this trade setup and provide your initial analysis.\n"
            "Respond with:\n"
            "- decision: APPROVE, REJECT, or WAIT\n"
            "- confidence: 0.0 to 1.0\n"
            "- thesis: A clear 2-3 sentence explanation of why you made this decision\n"
            "- risk_analysis: Key risks you identified\n"
            "- rationale: Your reasoning"
        )
        
        proposer_confidence = None
        initial_thesis = None
        critique_data = None  # Initialize to None
        
        try:
            # Step A: Get initial proposal
            proposer_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(False)},  # Standard mode for initial thesis
                    {"role": "user", "content": proposer_prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            proposer_content = proposer_response.choices[0].message.content
            proposer_json = self._clean_json_response(proposer_content)
            proposer_data = json.loads(proposer_json)
            
            if isinstance(proposer_data, list) and len(proposer_data) > 0:
                proposer_data = proposer_data[0]
            
            proposer_confidence = float(proposer_data.get("confidence", 0.5))
            initial_thesis = proposer_data.get("thesis", proposer_data.get("rationale", ""))
            
            logger.info(f"[Step A] Initial thesis: {proposer_data.get('decision', 'UNKNOWN')} @ {proposer_confidence:.2f} confidence")
            
            # Step B: Adversarial critique (if not already in red_team_mode)
            if not red_team_mode:
                logger.info(f"[Step B] Running adversarial critique...")
                
                try:
                    adversarial_prompt = self._get_adversarial_prompt(initial_thesis)
                    
                    critique_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a RED TEAM adversarial risk analyst."},
                            {"role": "user", "content": adversarial_prompt}
                        ],
                        temperature=0.3,  # Lower temp for more focused critique
                        response_format={"type": "json_object"}
                    )
                    
                    critique_content = critique_response.choices[0].message.content
                    critique_json = self._clean_json_response(critique_content)
                    critique_data = json.loads(critique_json)
                    
                    if isinstance(critique_data, list) and len(critique_data) > 0:
                        critique_data = critique_data[0]
                    
                    revised_confidence = critique_data.get("revised_confidence", proposer_confidence)
                    flaws = critique_data.get("flaws", [])
                    
                    logger.info(f"[Step B] Critique found {len(flaws)} flaws. Revised confidence: {revised_confidence:.2f} (from {proposer_confidence:.2f})")
                except Exception as e:
                    logger.warning(f"[Step B] Critique failed: {e}. Proceeding without critique.")
                    critique_data = None  # Ensure it's None if critique fails
            
            # Step C: Final synthesis
            logger.info(f"[Step C] Synthesizing final decision...")
            
            synthesis_prompt = (
                f"Initial Analysis:\n"
                f"Decision: {proposer_data.get('decision', 'UNKNOWN')}\n"
                f"Confidence: {proposer_confidence:.2f}\n"
                f"Thesis: {initial_thesis}\n\n"
            )
            
            if critique_data:
                synthesis_prompt += (
                    f"Red Team Critique:\n"
                    f"Flaws Found: {len(critique_data.get('flaws', []))}\n"
                    f"Revised Confidence: {critique_data.get('revised_confidence', proposer_confidence):.2f}\n"
                    f"Critique Summary: {critique_data.get('critique_summary', '')}\n\n"
                )
            
            synthesis_prompt += (
                "Synthesize the initial analysis and critique into a final decision.\n"
                "Respond in strictly valid JSON with keys: decision, confidence, risk_analysis, rationale.\n"
                "The confidence should reflect the critique if provided."
            )
            
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(red_team_mode)},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.1 if red_team_mode else 0.2,
                response_format={"type": "json_object"}
            )
            
            raw_content = final_response.choices[0].message.content
            
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
            
            # 5. Add metrics for v1.5
            data["proposer_confidence"] = proposer_confidence
            data["final_confidence"] = data.get("confidence", proposer_confidence)
            if critique_data:
                data["critique_flaws_count"] = len(critique_data.get("flaws", []))
                data["critique_summary"] = critique_data.get("critique_summary", "")

            # 6. Validate with Pydantic (but we need to handle extra fields)
            # Create a dict with only the fields Pydantic expects
            pydantic_data = {
                "decision": data.get("decision"),
                "confidence": data.get("confidence", data.get("final_confidence", proposer_confidence)),
                "risk_analysis": data.get("risk_analysis", ""),
                "rationale": data.get("rationale", "")
            }
            
            decision_obj = DeepSeekResponse(**pydantic_data)
            
            # Attach metrics as attributes (not in Pydantic model)
            # Always set proposer_confidence (use final confidence as fallback if Step A failed)
            if proposer_confidence is None:
                proposer_confidence = decision_obj.confidence
                logger.warning(f"[Step C] proposer_confidence was None, using final confidence {proposer_confidence:.2f} as fallback")
            
            decision_obj.proposer_confidence = proposer_confidence
            decision_obj.final_confidence = data.get("final_confidence", decision_obj.confidence)
            
            if critique_data:
                decision_obj.critique_flaws_count = len(critique_data.get("flaws", []))
                decision_obj.critique_summary = critique_data.get("critique_summary", "")
            else:
                # Even if critique failed, set to 0 to indicate no critique was performed
                decision_obj.critique_flaws_count = 0
            
            # Safety Logic
            if decision_obj.decision == ReasoningDecision.APPROVE:
                if not decision_obj.is_actionable():
                    logger.warning(f"Trade Approved by LLM but confidence {decision_obj.confidence} below threshold.")
                    decision_obj.decision = ReasoningDecision.WAIT
            
            logger.info(f"[Step C] Final decision: {decision_obj.decision.value} @ {decision_obj.confidence:.2f} (proposer: {proposer_confidence:.2f})")
            
            return decision_obj

        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            # EXTENSIVE LOGGING FOR DEBUGGING
            logger.error("="*40)
            logger.error(f"❌ LLM PARSING ERROR: {e}")
            if 'raw_content' in locals():
                logger.error(f"RAW CONTENT START:\n{raw_content}")
                logger.error("RAW CONTENT END")
            logger.error("="*40)
            
            # Create error response but still preserve proposer_confidence if we have it
            error_response = DeepSeekResponse(
                decision=ReasoningDecision.REJECT,
                confidence=1.0,
                risk_analysis="System Error: Parsing Failed",
                rationale=f"Error parsing LLM response. Check logs for raw output."
            )
            # Preserve proposer_confidence if it was set before the error, otherwise use error confidence
            if proposer_confidence is not None:
                error_response.proposer_confidence = proposer_confidence
            else:
                # Fallback: use error confidence as proposer (indicates Step A failed)
                error_response.proposer_confidence = 1.0
                logger.warning("[Error Handler] proposer_confidence was None, using error confidence as fallback")
            error_response.final_confidence = 1.0  # Error state
            error_response.critique_flaws_count = 0  # No critique performed due to error
            return error_response
        except Exception as e:
            logger.error(f"Critical API Error: {e}", exc_info=True)
            # Return error response with metrics if available
            error_response = DeepSeekResponse(
                decision=ReasoningDecision.REJECT,
                confidence=0.0,
                risk_analysis="System Error: API call failed",
                rationale=f"Error: {str(e)}"
            )
            if proposer_confidence is not None:
                error_response.proposer_confidence = proposer_confidence
            else:
                # Fallback: use error confidence as proposer (indicates Step A failed)
                error_response.proposer_confidence = 0.0
                logger.warning("[Error Handler] proposer_confidence was None, using error confidence as fallback")
            error_response.final_confidence = 0.0
            error_response.critique_flaws_count = 0  # No critique performed due to error
            return error_response


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
