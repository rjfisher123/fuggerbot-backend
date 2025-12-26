"""
Historonics Agent - Historical Research and Hypothesis Generation.

A read-only agent that synthesizes research reports, insights, and historical context
to generate structured hypotheses about what to study next.

CRITICAL INVARIANTS:
- All outputs are advisory only (never executable)
- Cannot modify simulation results or scoring logic
- Cannot set parameters or thresholds
- Only informs what to study, never how to compute
"""
import logging
import json
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from agents.research.historonics_schema import (
    Hypothesis,
    HypothesisType,
    HistoricalAnalog,
    HistoronicsOutput
)
from agents.research.historonics_prompts import (
    get_historonics_system_prompt,
    build_historonics_user_prompt
)
from reasoning.engine import get_deepseek_engine

logger = logging.getLogger(__name__)


class HistoronicsAgent:
    """
    Historical research agent that generates advisory hypotheses.
    
    Reads research outputs and generates structured hypotheses without
    modifying simulation logic, scoring, or parameters.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Historonics Agent.
        
        Args:
            api_key: Optional OpenRouter API key (defaults to settings)
        """
        try:
            self.llm_engine = get_deepseek_engine(api_key=api_key)
            logger.info("HistoronicsAgent initialized with LLM engine")
        except Exception as e:
            logger.error(f"Failed to initialize LLM engine for HistoronicsAgent: {e}")
            self.llm_engine = None
    
    def generate_hypotheses(
        self,
        report_summary: str,
        insights: List[Dict[str, Any]],
        regime_coverage: Dict[str, int],
        scenario_metadata: List[Dict[str, str]],
        report_id: Optional[str] = None,
        iteration_id: Optional[str] = None
    ) -> HistoronicsOutput:
        """
        Generate structured hypotheses from research findings.
        
        Args:
            report_summary: Executive summary from research report
            insights: List of insight dicts (must include insight_id, description, confidence, evidence_status)
            regime_coverage: Dict of regime_id -> scenario count
            scenario_metadata: List of scenario metadata (ID, regime_id - NO METRICS)
            report_id: Optional report ID
            iteration_id: Optional iteration ID
        
        Returns:
            HistoronicsOutput with generated hypotheses
        
        Raises:
            ValueError: If LLM engine not available or output validation fails
        """
        if not self.llm_engine:
            logger.warning("LLM engine not available - returning empty hypotheses")
            return HistoronicsOutput(
                hypotheses=[],
                report_id=report_id,
                iteration_id=iteration_id
            )
        
        logger.info("Generating historical hypotheses...")
        
        # Build prompts
        system_prompt = get_historonics_system_prompt()
        user_prompt = build_historonics_user_prompt(
            report_summary=report_summary,
            insights_summary=insights,
            regime_coverage_summary=regime_coverage,
            scenario_metadata=scenario_metadata
        )
        
        try:
            # Call LLM
            response = self.llm_engine.client.chat.completions.create(
                model=self.llm_engine.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # Moderate creativity for hypothesis generation
                max_tokens=2000
            )
            
            # Extract content
            raw_content = response.choices[0].message.content
            if not raw_content:
                logger.warning("Empty LLM response")
                return HistoronicsOutput(
                    hypotheses=[],
                    report_id=report_id,
                    iteration_id=iteration_id
                )
            
            # Parse JSON from response
            parsed = self._parse_llm_response(raw_content)
            
            # Validate and convert to schema
            hypotheses = []
            for hyp_data in parsed.get("hypotheses", []):
                try:
                    hypothesis = self._validate_and_create_hypothesis(hyp_data)
                    if hypothesis:
                        hypotheses.append(hypothesis)
                except Exception as e:
                    logger.warning(f"Failed to validate hypothesis: {e}")
                    continue
            
            logger.info(f"Generated {len(hypotheses)} valid hypotheses")
            
            return HistoronicsOutput(
                hypotheses=hypotheses,
                report_id=report_id,
                iteration_id=iteration_id
            )
            
        except Exception as e:
            logger.error(f"Failed to generate hypotheses: {e}", exc_info=True)
            # Return empty output on error (fail gracefully)
            return HistoronicsOutput(
                hypotheses=[],
                report_id=report_id,
                iteration_id=iteration_id
            )
    
    def _parse_llm_response(self, raw_content: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown fences and cleaning.
        
        Args:
            raw_content: Raw LLM response content
        
        Returns:
            Parsed JSON dict
        """
        # Remove markdown code fences if present
        json_match = re.search(r'```json\s*({.*?})\s*```', raw_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object
            start = raw_content.find('{')
            end = raw_content.rfind('}')
            if start >= 0 and end > start:
                json_str = raw_content[start:end+1]
            else:
                json_str = raw_content
        
        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw content: {raw_content[:500]}")
            return {"hypotheses": []}
    
    def _validate_and_create_hypothesis(self, hyp_data: Dict[str, Any]) -> Optional[Hypothesis]:
        """
        Validate hypothesis data and create Hypothesis object.
        
        Performs safety checks to ensure hypothesis doesn't violate invariants:
        - No numeric prescriptions
        - No executable code
        - Explicit uncertainty notes
        
        Args:
            hyp_data: Raw hypothesis data from LLM
        
        Returns:
            Validated Hypothesis object, or None if validation fails
        """
        # Safety check: Reject if contains numeric prescriptions
        summary = hyp_data.get("summary", "")
        validation = hyp_data.get("recommended_validation", "")
        
        # Check for numeric thresholds or parameter values
        numeric_pattern = r'\b(threshold|parameter|value|set to|should be|must be)\s*[=:]\s*\d+'
        if re.search(numeric_pattern, summary, re.IGNORECASE):
            logger.warning(f"Rejected hypothesis with numeric prescription: {summary[:100]}")
            return None
        
        if re.search(numeric_pattern, validation, re.IGNORECASE):
            logger.warning(f"Rejected hypothesis validation with numeric prescription: {validation[:100]}")
            return None
        
        # Check for executable code patterns
        code_patterns = [r'def\s+\w+', r'class\s+\w+', r'import\s+\w+', r'if\s+\w+\s*:', r'return\s+']
        for pattern in code_patterns:
            if re.search(pattern, summary + validation):
                logger.warning(f"Rejected hypothesis with code-like content: {summary[:100]}")
                return None
        
        # Generate stable hypothesis_id if not provided
        hypothesis_id = hyp_data.get("hypothesis_id")
        if not hypothesis_id:
            # Generate from summary hash
            hash_input = f"{hyp_data.get('summary', '')}{hyp_data.get('hypothesis_type', '')}"
            hypothesis_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        # Parse hypothesis type
        try:
            hyp_type = HypothesisType(hyp_data.get("hypothesis_type", "historical_analogy"))
        except ValueError:
            hyp_type = HypothesisType.HISTORICAL_ANALOGY
        
        # Parse historical analogs
        analogs = []
        for analog_data in hyp_data.get("historical_analogs", []):
            try:
                analog = HistoricalAnalog(
                    period=analog_data.get("period", "Unknown"),
                    description=analog_data.get("description", ""),
                    confidence=float(analog_data.get("confidence", 0.0))
                )
                analogs.append(analog)
            except Exception as e:
                logger.warning(f"Failed to parse historical analog: {e}")
        
        # Ensure uncertainty_notes is present and not empty
        uncertainty = hyp_data.get("uncertainty_notes", "")
        if not uncertainty or uncertainty.strip() == "":
            uncertainty = "This hypothesis is untested and based on narrative analysis only."
        
        # Create hypothesis
        try:
            hypothesis = Hypothesis(
                hypothesis_id=hypothesis_id,
                hypothesis_type=hyp_type,
                summary=hyp_data.get("summary", ""),
                historical_analogs=analogs,
                linked_insights=hyp_data.get("linked_insights", []),
                regimes_implicated=hyp_data.get("regimes_implicated", []),
                uncertainty_notes=uncertainty,
                recommended_validation=hyp_data.get("recommended_validation", "")
            )
            return hypothesis
        except Exception as e:
            logger.error(f"Failed to create Hypothesis object: {e}")
            return None


# Singleton instance
_historonics_agent: Optional[HistoronicsAgent] = None


def get_historonics_agent(api_key: Optional[str] = None) -> HistoronicsAgent:
    """Get or create Historonics Agent instance."""
    global _historonics_agent
    if _historonics_agent is None:
        _historonics_agent = HistoronicsAgent(api_key=api_key)
    return _historonics_agent

