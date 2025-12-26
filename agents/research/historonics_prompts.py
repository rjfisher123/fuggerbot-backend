"""
Historonics Agent Prompts - LLM Safety-Enforced Prompt Templates.

All prompts explicitly instruct the LLM to:
- Act as a research historian, not a trader
- Avoid optimizing or predicting returns
- State uncertainty explicitly
- Avoid numeric prescriptions
- Reference evidence IDs when possible
"""
from typing import List, Dict, Any, Optional


def get_historonics_system_prompt() -> str:
    """
    Get the system prompt for Historonics Agent.
    
    This prompt enforces LLM safety rules:
    - Research historian role only
    - No optimization or prediction
    - Explicit uncertainty
    - No numeric prescriptions
    - Evidence-based reasoning
    """
    return """You are a research historian working with a quantitative trading research system.

YOUR ROLE:
- Synthesize historical patterns and research insights
- Generate structured hypotheses about what to study next
- Identify relevant historical analogies and regime transitions
- Suggest areas of uncertainty that merit investigation

CRITICAL CONSTRAINTS (YOU MUST FOLLOW THESE):
1. You are NOT a trader - do not optimize, predict returns, or make trading recommendations
2. You are NOT an optimizer - do not suggest parameter values or thresholds
3. You are NOT an authority - all hypotheses are UNTESTED and ADVISORY ONLY
4. State uncertainty explicitly - acknowledge limitations and unknowns
5. Avoid numeric prescriptions - suggest WHAT to study, not HOW to compute
6. Reference evidence IDs when possible - link to specific insights, scenarios, or regimes

OUTPUT REQUIREMENTS:
- Generate structured JSON hypotheses conforming to the provided schema
- Each hypothesis must include:
  * A clear summary statement
  * Historical analogs (if applicable) with confidence scores
  * Linked insight IDs (if applicable)
  * Implicated regime IDs (if applicable)
  * Explicit uncertainty notes
  * Non-binding validation recommendations

REJECTION RULES (DO NOT GENERATE IF):
- Hypothesis contains numeric parameter values or thresholds
- Hypothesis suggests executable code or logic changes
- Hypothesis claims certainty or authority
- Hypothesis lacks explicit uncertainty notes

You exist to steepen the learning curve through historical context, not to shortcut it through optimization.
"""


def build_historonics_user_prompt(
    report_summary: str,
    insights_summary: List[Dict[str, Any]],
    regime_coverage_summary: Dict[str, int],
    scenario_metadata: List[Dict[str, str]]
) -> str:
    """
    Build the user prompt for Historonics Agent.
    
    Args:
        report_summary: Executive summary from research report
        insights_summary: List of insight summaries (ID, description, confidence)
        regime_coverage_summary: Dict of regime_id -> scenario count
        scenario_metadata: List of scenario metadata (ID, regime, parameters - NO METRICS)
    
    Returns:
        Formatted user prompt string
    """
    # Format insights
    insights_text = ""
    if insights_summary:
        insights_text = "\n".join([
            f"- {insight.get('insight_id', 'unknown')}: {insight.get('description', '')} "
            f"(confidence: {insight.get('confidence', 0.0):.2f}, "
            f"evidence_status: {insight.get('evidence_status', 'unknown')})"
            for insight in insights_summary
        ])
    else:
        insights_text = "No insights recorded yet."
    
    # Format regime coverage
    regime_text = "\n".join([
        f"- {regime_id}: {count} scenarios"
        for regime_id, count in sorted(regime_coverage_summary.items())
    ]) if regime_coverage_summary else "No regime coverage data available."
    
    # Format scenario metadata (NO METRICS - just IDs, regimes, param names)
    scenario_text = ""
    if scenario_metadata:
        scenario_text = f"\n{len(scenario_metadata)} scenarios tested:\n"
        for scenario in scenario_metadata[:10]:  # Limit to top 10 for brevity
            scenario_text += f"- {scenario.get('scenario_id', 'unknown')}: {scenario.get('regime_id', 'unknown')} regime\n"
        if len(scenario_metadata) > 10:
            scenario_text += f"... and {len(scenario_metadata) - 10} more scenarios\n"
    else:
        scenario_text = "No scenarios tested yet."
    
    prompt = f"""Analyze the following research findings and generate structured hypotheses about what to study next.

RESEARCH REPORT SUMMARY:
{report_summary}

ACCUMULATED INSIGHTS:
{insights_text}

REGIME COVERAGE:
{regime_text}

SCENARIO METADATA (NO METRICS):
{scenario_text}

YOUR TASK:
Generate 2-5 structured hypotheses that:
1. Identify historical analogies relevant to current findings
2. Suggest regime transitions or patterns worth investigating
3. Highlight potential failure precursors based on historical patterns
4. Flag parameter risks or boundary conditions that may need testing

FOR EACH HYPOTHESIS:
- Provide a clear, concise summary statement
- List relevant historical analogs (periods, events) with confidence scores
- Link to specific insight IDs that inform this hypothesis
- Identify implicated regime IDs
- Explicitly state uncertainties and limitations
- Suggest non-binding validation approaches (WHAT to test, not HOW to compute)

REMEMBER:
- All hypotheses are UNTESTED and ADVISORY ONLY
- Do NOT suggest parameter values, thresholds, or numeric prescriptions
- Do NOT claim certainty or authority
- Do NOT generate executable code or logic changes
- State uncertainty explicitly

Respond with a JSON object containing:
{{
  "hypotheses": [
    {{
      "hypothesis_id": "stable_hash_or_identifier",
      "hypothesis_type": "historical_analogy | regime_transition | failure_precursor | parameter_risk",
      "summary": "Concise statement",
      "historical_analogs": [
        {{
          "period": "e.g. Q4 2018",
          "description": "Why this period is relevant",
          "confidence": 0.0
        }}
      ],
      "linked_insights": ["insight_id_1"],
      "regimes_implicated": ["regime_id_1"],
      "uncertainty_notes": "Explicit limitations and unknowns",
      "recommended_validation": "How this could be tested (non-numeric, non-binding)"
    }}
  ]
}}
"""
    return prompt

