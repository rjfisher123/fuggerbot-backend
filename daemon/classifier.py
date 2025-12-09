"""
Regime Classifier Daemon.

Uses LLM to analyze signals and determine if a Regime Shift occurred.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from reasoning.engine import DeepSeekEngine
from context.schemas import MacroRegime, RegimeType
from config.settings import get_settings

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """
    Classifies macroeconomic regimes using LLM analysis of hard and soft data.
    
    Analyzes FRED data and RSS headlines to determine the current market regime
    and detect regime shifts.
    """
    
    def __init__(self):
        """Initialize the regime classifier with DeepSeek engine."""
        settings = get_settings()
        
        self.engine = DeepSeekEngine(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=settings.deepseek_model
        )
        
        logger.info("RegimeClassifier initialized")
    
    def analyze_snapshot(
        self,
        hard_data: Dict[str, Any],
        headlines: List[str]
    ) -> Optional[MacroRegime]:
        """
        Analyze hard data and headlines to determine current market regime.
        
        Args:
            hard_data: Dictionary of FRED data (from SignalExtractor.get_hard_data())
            headlines: List of relevant headlines (from SignalExtractor.get_soft_data())
        
        Returns:
            MacroRegime object if analysis succeeds, None if it fails.
        """
        try:
            # Format hard data for prompt
            hard_data_str = self._format_hard_data(hard_data)
            
            # Format headlines for prompt
            headlines_str = "\n".join([f"- {h}" for h in headlines]) if headlines else "No relevant headlines found."
            
            # Construct prompt
            prompt = (
                "You are a Macro Strategist. Analyze this data:\n\n"
                f"Hard Data:\n{hard_data_str}\n\n"
                f"Headlines:\n{headlines_str}\n\n"
                "Determine the current market regime.\n\n"
                "Output JSON with the following structure:\n"
                "{\n"
                '  "regime_type": "INFLATIONARY" | "DEFLATIONARY" | "LIQUIDITY_CRISIS" | "GOLDILOCKS",\n'
                '  "confidence": 0.0-1.0,\n'
                '  "summary": "Brief description of the regime",\n'
                '  "risk_on": true | false,\n'
                '  "vibe_score": 0.0-1.0\n'
                "}\n\n"
                "Consider:\n"
                "- Fed liquidity (WALCL): Rising = more liquidity, falling = tightening\n"
                "- Yield curve (T10Y2Y): Negative = recession risk, positive = growth\n"
                "- VIX: High = fear/volatility, low = complacency\n"
                "- Headlines: Fed policy, inflation, GDP, rates\n"
                "- Regime types:\n"
                "  * INFLATIONARY: High inflation, Fed tightening, rising rates\n"
                "  * DEFLATIONARY: Low inflation, Fed easing, falling rates\n"
                "  * LIQUIDITY_CRISIS: Credit crunch, high VIX, Fed emergency actions\n"
                "  * GOLDILOCKS: Moderate growth, low inflation, stable rates\n"
            )
            
            # Call LLM
            logger.info("🤖 Calling LLM for regime classification...")
            
            try:
                # Use the engine's client directly for custom prompt
                response = self.engine.client.chat.completions.create(
                    model=self.engine.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert macro strategist. Analyze market data and return valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent classification
                    response_format={"type": "json_object"}
                )
                
                raw_content = response.choices[0].message.content
                
                if not raw_content:
                    logger.error("LLM returned empty content")
                    return None
                    
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                return None
            
            # Parse JSON response
            try:
                # Clean JSON (handle markdown fences, etc.)
                clean_json = self._clean_json_response(raw_content)
                data = json.loads(clean_json)
                
                # Handle case where LLM returns a list instead of dict
                if isinstance(data, list):
                    if len(data) > 0:
                        data = data[0]  # Take first element
                    else:
                        logger.error("LLM returned empty list")
                        return None
                
                # Handle case where LLM returns primitive types (int, float, str, bool)
                # This shouldn't happen with response_format={"type": "json_object"}, but handle it
                if not isinstance(data, dict):
                    logger.error(f"LLM returned non-dict type: {type(data)} (value: {data})")
                    logger.error(f"Raw content was: {raw_content[:200]}")
                    # Try to create a default regime as fallback
                    logger.warning("Creating default GOLDILOCKS regime as fallback")
                    from datetime import datetime
                    return MacroRegime(
                        id="GOLDILOCKS_50",
                        name="Goldilocks Regime",
                        summary="LLM classification failed, using default neutral regime",
                        risk_on=True,
                        vibe_score=0.5,
                        timestamp=datetime.now()
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.error(f"Raw content: {raw_content}")
                return None
            
            # Validate and map regime_type
            regime_type_str = data.get("regime_type", "").upper()
            try:
                regime_type = RegimeType(regime_type_str)
            except ValueError:
                logger.warning(f"Invalid regime_type '{regime_type_str}', defaulting to GOLDILOCKS")
                regime_type = RegimeType.GOLDILOCKS
            
            # Extract and validate fields
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
            
            summary = str(data.get("summary", "No summary provided"))
            risk_on = bool(data.get("risk_on", True))
            vibe_score = float(data.get("vibe_score", 0.5))
            vibe_score = max(0.0, min(1.0, vibe_score))  # Clamp to 0-1
            
            # Generate regime ID and name
            # Include confidence in ID for tracking, but also store it separately
            regime_id = f"{regime_type.value}_{int(confidence * 100)}"
            regime_name = f"{regime_type.value.replace('_', ' ').title()} Regime"
            
            # Store confidence in summary for later extraction if needed
            # (We'll parse it from ID in watcher, but this provides backup)
            
            # Create MacroRegime object
            from datetime import datetime
            regime = MacroRegime(
                id=regime_id,
                name=regime_name,
                summary=summary,
                risk_on=risk_on,
                vibe_score=vibe_score,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"✅ Regime classified: {regime.id} - {regime.name} "
                f"(confidence: {confidence:.2f}, risk_on: {risk_on}, vibe: {vibe_score:.2f})"
            )
            
            return regime
            
        except Exception as e:
            logger.error(f"Error in regime classification: {e}", exc_info=True)
            return None
    
    def _format_hard_data(self, hard_data: Dict[str, Any]) -> str:
        """
        Format hard data dictionary into readable string for prompt.
        
        Args:
            hard_data: Dictionary from SignalExtractor.get_hard_data()
        
        Returns:
            Formatted string
        """
        if not hard_data:
            return "No hard data available."
        
        lines = []
        for series_id, data in hard_data.items():
            desc = data.get("description", series_id)
            current = data.get("current", 0)
            change = data.get("change", 0)
            change_pct = data.get("change_pct", 0)
            
            lines.append(
                f"{desc} ({series_id}): {current:.2f} "
                f"(change: {change:+.2f}, {change_pct:+.2f}%)"
            )
        
        return "\n".join(lines) if lines else "No hard data available."
    
    def _clean_json_response(self, raw_content: str) -> str:
        """
        Clean JSON response from LLM (handle markdown, etc.).
        
        Args:
            raw_content: Raw content from LLM
        
        Returns:
            Cleaned JSON string
        """
        import re
        
        if not raw_content:
            return "{}"
        
        # Remove markdown code fences (json or plain)
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', raw_content, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find first { and last }
        start = raw_content.find('{')
        end = raw_content.rfind('}')
        if start != -1 and end != -1 and end > start:
            return raw_content[start:end+1]
        
        return raw_content.strip()

