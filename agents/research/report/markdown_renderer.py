"""
Markdown Renderer - Deterministic Report Rendering.

Renders ResearchReport objects to Markdown format.
All formatting is deterministic and stable across runs.
"""
import logging
from typing import List, Optional, Dict, Any
from agents.research.report.report_schema import (
    ResearchReport,
    ReportInsight,
    FailureBoundary,
    RegimeCoverageEntry,
    RecommendedExperiment
)

logger = logging.getLogger(__name__)


class MarkdownRenderer:
    """
    Renders research reports to Markdown format.
    """
    
    def render(self, report: ResearchReport) -> str:
        """
        Render complete report to Markdown.
        
        Args:
            report: ResearchReport object
        
        Returns:
            Markdown string
        """
        lines = []
        
        # Title
        lines.append(f"# FuggerBot Research Report: {report.metadata.report_id}")
        lines.append("")
        
        # Metadata
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Report ID**: {report.metadata.report_id}")
        lines.append(f"- **Strategy Version**: {report.metadata.strategy_version}")
        lines.append(f"- **Research Loop Version**: {report.metadata.research_loop_version}")
        lines.append(f"- **Simulator Commit Hash**: {report.metadata.simulator_commit_hash}")
        lines.append(f"- **Data Fingerprint**: {report.metadata.data_fingerprint}")
        lines.append(f"- **Generated At**: {report.metadata.generated_at}")
        lines.append(f"- **Total Insights**: {report.metadata.total_insights}")
        lines.append(f"- **Total Scenarios**: {report.metadata.total_scenarios}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(report.executive_summary)
        lines.append("")
        
        # Performance Overview
        lines.append("## Performance Overview")
        lines.append("")
        perf = report.performance_metrics
        lines.append(f"- **Total Scenarios**: {perf.total_scenarios}")
        lines.append(f"- **Average Return**: {perf.avg_return_pct:.2f}%")
        lines.append(f"- **Return Range**: {perf.min_return_pct:.2f}% to {perf.max_return_pct:.2f}%")
        
        # Sharpe ratio statistics (with validity disclosure)
        lines.append(f"- **Average Sharpe Ratio**: {perf.avg_sharpe_ratio:.2f} (valid values only)")
        if perf.median_sharpe_ratio is not None:
            lines.append(f"- **Median Sharpe Ratio**: {perf.median_sharpe_ratio:.2f}")
        if perf.sharpe_p10 is not None and perf.sharpe_p90 is not None:
            lines.append(f"- **Sharpe Ratio Range (p10-p90)**: {perf.sharpe_p10:.2f} to {perf.sharpe_p90:.2f}")
        if perf.invalid_sharpe_count > 0:
            lines.append(f"- **Invalid Sharpe Count**: {perf.invalid_sharpe_count} scenarios excluded (zero variance or numerical issues)")
        
        lines.append(f"- **Average Max Drawdown**: {perf.avg_max_drawdown_pct:.2f}%")
        lines.append(f"- **Average Win Rate**: {perf.avg_win_rate:.2%}")
        lines.append("")
        
        # Top 5 Scenarios
        if report.appendix_top_scenarios:
            lines.append("### Top 5 Scenarios (by Return)")
            lines.append("")
            lines.append("| Scenario ID | Symbol | Return % | Sharpe | Drawdown % | Win Rate | Trades |")
            lines.append("|-------------|--------|----------|--------|------------|----------|--------|")
            for scenario in report.appendix_top_scenarios:
                lines.append(
                    f"| {scenario['scenario_id'][:12]}... | {scenario['symbol']} | "
                    f"{scenario['return_pct']:.2f}% | {scenario['sharpe_ratio']:.2f} | "
                    f"{scenario['drawdown_pct']:.2f}% | {scenario['win_rate']:.2%} | {scenario['trades_count']} |"
                )
            lines.append("")
        
        # Bottom 5 Scenarios
        if report.appendix_bottom_scenarios:
            lines.append("### Bottom 5 Scenarios (by Return)")
            lines.append("")
            lines.append("| Scenario ID | Symbol | Return % | Sharpe | Drawdown % | Win Rate | Trades |")
            lines.append("|-------------|--------|----------|--------|------------|----------|--------|")
            for scenario in report.appendix_bottom_scenarios:
                lines.append(
                    f"| {scenario['scenario_id'][:12]}... | {scenario['symbol']} | "
                    f"{scenario['return_pct']:.2f}% | {scenario['sharpe_ratio']:.2f} | "
                    f"{scenario['drawdown_pct']:.2f}% | {scenario['win_rate']:.2%} | {scenario['trades_count']} |"
                )
            lines.append("")
        
        # Per-Symbol Summary
        if report.appendix_symbol_stats:
            lines.append("### Per-Symbol Summary")
            lines.append("")
            lines.append("| Symbol | Scenarios | Avg Return % | Median Return % | Avg Drawdown % | Avg Win Rate |")
            lines.append("|--------|-----------|--------------|-----------------|----------------|--------------|")
            # Sort by symbol name for deterministic ordering
            for symbol in sorted(report.appendix_symbol_stats.keys()):
                stats = report.appendix_symbol_stats[symbol]
                lines.append(
                    f"| {symbol} | {stats['scenario_count']} | {stats['avg_return_pct']:.2f}% | "
                    f"{stats['median_return_pct']:.2f}% | {stats['avg_drawdown_pct']:.2f}% | "
                    f"{stats['avg_win_rate']:.2%} |"
                )
            lines.append("")
        
        # Per-Regime Summary (top 10 only)
        if report.appendix_regime_stats:
            lines.append("### Per-Regime Summary (Top 10 by Scenario Count)")
            lines.append("")
            lines.append("| Regime ID | Scenarios | Avg Return % | Median Return % | Avg Drawdown % | Avg Win Rate |")
            lines.append("|-----------|-----------|--------------|-----------------|----------------|--------------|")
            # Sort by scenario_count descending, then regime_id
            sorted_regimes = sorted(
                report.appendix_regime_stats.items(),
                key=lambda x: (x[1]['scenario_count'], x[0]),
                reverse=True
            )[:10]  # Top 10 only
            for regime_id, stats in sorted_regimes:
                lines.append(
                    f"| {regime_id[:30]}... | {stats['scenario_count']} | {stats['avg_return_pct']:.2f}% | "
                    f"{stats['median_return_pct']:.2f}% | {stats['avg_drawdown_pct']:.2f}% | "
                    f"{stats['avg_win_rate']:.2%} |"
                )
            lines.append("")
        
        # Confirmed Insights (grouped by evidence status)
        lines.append("## Confirmed Insights")
        lines.append("")
        if not report.confirmed_insights:
            lines.append("*No insights recorded.*")
        else:
            # Group by evidence status first (STRONG vs PRELIMINARY)
            strong_evidence = [i for i in report.confirmed_insights if i.evidence_status.value == "strong"]
            preliminary = [i for i in report.confirmed_insights if i.evidence_status.value == "preliminary"]
            
            if strong_evidence:
                lines.append("### Strong Insights (Evidence-Qualified)")
                lines.append("")
                lines.append("*Qualified by: ≥3 supporting scenarios AND ≥2 regime coverage*")
                lines.append("")
                for insight in strong_evidence:
                    lines.extend(self._render_insight(insight, indent=""))
                lines.append("")
            
            if preliminary:
                lines.append("### Preliminary Insights (Insufficient Evidence)")
                lines.append("")
                lines.append("*Preliminary status: <3 scenarios OR <2 regime coverage (may have high confidence but lacks evidence breadth)*")
                lines.append("")
                for insight in preliminary:
                    lines.extend(self._render_insight(insight, indent=""))
                lines.append("")
        
        # Known Unknowns
        lines.append("## Known Unknowns")
        lines.append("")
        if not report.known_unknowns:
            lines.append("*No known unknowns identified.*")
        else:
            for unknown in report.known_unknowns:
                lines.append(f"- {unknown}")
        lines.append("")
        
        # Failure Boundaries
        lines.append("## Failure Boundaries")
        lines.append("")
        if not report.failure_boundaries:
            lines.append("*No failure boundaries detected.*")
        else:
            for boundary in report.failure_boundaries:
                lines.extend(self._render_failure_boundary(boundary))
                lines.append("")
        
        # Regime Coverage
        lines.append("## Regime Coverage")
        lines.append("")
        if not report.regime_coverage:
            lines.append("*No regime coverage data available.*")
        else:
            lines.append("| Regime ID | Description | Scenarios | Coverage % |")
            lines.append("|-----------|-------------|-----------|------------|")
            for entry in report.regime_coverage:
                lines.append(
                    f"| {entry.regime_id} | {entry.regime_description[:50]} | "
                    f"{entry.scenario_count} | {entry.coverage_percentage:.1f}% |"
                )
        lines.append("")
        
        # Recommended Experiments (Top 3 only)
        lines.append("## Recommended Experiments (Top 3)")
        lines.append("")
        if not report.recommended_experiments:
            lines.append("*No experiments recommended.*")
        else:
            # Show only top 3
            top_3 = report.recommended_experiments[:3]
            for i, experiment in enumerate(top_3, 1):
                lines.extend(self._render_experiment(experiment, index=i))
                lines.append("")
        
        # Experiment Backlog (remaining proposals)
        if len(report.recommended_experiments) > 3:
            lines.append("## Experiment Backlog (Deferred)")
            lines.append("")
            lines.append(f"*{len(report.recommended_experiments) - 3} additional proposals deferred due to lower marginal information gain*")
            lines.append("")
            backlog = report.recommended_experiments[3:]
            
            # Group by type for cleaner display
            backlog_by_type: Dict[str, List[RecommendedExperiment]] = {}
            for exp in backlog:
                exp_type = exp.proposal_type
                if exp_type not in backlog_by_type:
                    backlog_by_type[exp_type] = []
                backlog_by_type[exp_type].append(exp)
            
            for exp_type in sorted(backlog_by_type.keys()):  # Deterministic ordering
                lines.append(f"### {exp_type.replace('_', ' ').title()} ({len(backlog_by_type[exp_type])} proposals)")
                lines.append("")
                for exp in backlog_by_type[exp_type]:
                    # Extract focus (regime ID or parameter name) from scenario_spec if available
                    focus = exp.title.split(":")[-1].strip() if ":" in exp.title else exp.title[:50]
                    lines.append(f"- **{focus}** (Info Gain: {exp.expected_info_gain:.2f}, Priority: {exp.priority}/10)")
                    lines.append(f"  - Reason for deferral: Lower marginal information gain compared to top 3")
                lines.append("")
        
        # Appendices
        lines.append("## Appendices")
        lines.append("")
        
        lines.append("### Scenario IDs")
        lines.append("")
        if report.appendix_scenario_ids:
            for scenario_id in report.appendix_scenario_ids[:20]:  # Limit to first 20 for readability
                lines.append(f"- `{scenario_id}`")
            if len(report.appendix_scenario_ids) > 20:
                lines.append(f"\n*... and {len(report.appendix_scenario_ids) - 20} more scenarios*")
        else:
            lines.append("*No scenario IDs available.*")
        lines.append("")
        
        if report.appendix_sensitivity_analysis:
            lines.append("### Sensitivity Analysis Summary")
            lines.append("")
            sensitivity = report.appendix_sensitivity_analysis
            high_sensitivity = sensitivity.get("high_sensitivity_params", {})
            if high_sensitivity:
                lines.append("**High-Sensitivity Parameters:**")
                lines.append("")
                for param, metrics in high_sensitivity.items():
                    lines.append(f"- **{param}**: range={metrics.get('range', 0):.2f}%, std={metrics.get('std', 0):.2f}")
                lines.append("")
        
        if report.appendix_metric_definitions:
            lines.append("### Metric Definitions")
            lines.append("")
            for metric_name, definition in report.appendix_metric_definitions.items():
                lines.append(f"#### {metric_name.replace('_', ' ').title()}")
                lines.append("")
                # Format definition (preserve newlines)
                for line in definition.split('\n'):
                    lines.append(line)
                lines.append("")
        
        if report.appendix_historonics_hypotheses:
            lines.append("## Historical Context & Hypothesis Generation (Advisory)")
            lines.append("")
            lines.append("*The following hypotheses are generated by the Historonics Agent.")
            lines.append("They are non-binding, unvalidated, and require deterministic testing.*")
            lines.append("")
            for hyp_data in report.appendix_historonics_hypotheses:
                lines.extend(self._render_historonics_hypothesis(hyp_data))
                lines.append("")
        
        return "\n".join(lines)
    
    def _render_historonics_hypothesis(self, hyp_data: Dict[str, Any]) -> List[str]:
        """Render a single Historonics hypothesis."""
        lines = []
        
        hyp_type = hyp_data.get("hypothesis_type", "unknown").replace("_", " ").title()
        lines.append(f"### {hyp_data.get('hypothesis_id', 'unknown')[:12]}... ({hyp_type})")
        lines.append("")
        lines.append(f"**Status**: {hyp_data.get('status', 'UNTESTED')} | **Source**: {hyp_data.get('source', 'Historonics Agent')} | **Evidence Level**: {hyp_data.get('evidence_level', 'Narrative only')}")
        lines.append("")
        lines.append(f"**Summary**: {hyp_data.get('summary', '')}")
        lines.append("")
        
        # Historical analogs
        analogs = hyp_data.get("historical_analogs", [])
        if analogs:
            lines.append("**Historical Analogs**:")
            lines.append("")
            for analog in analogs:
                conf = analog.get("confidence", 0.0)
                lines.append(f"- {analog.get('period', 'Unknown')}: {analog.get('description', '')} (confidence: {conf:.2f})")
            lines.append("")
        
        # Linked insights
        linked = hyp_data.get("linked_insights", [])
        if linked:
            lines.append(f"**Linked Insights**: {', '.join(linked)}")
            lines.append("")
        
        # Regimes implicated
        regimes = hyp_data.get("regimes_implicated", [])
        if regimes:
            lines.append(f"**Regimes Implicated**: {', '.join(regimes)}")
            lines.append("")
        
        # Uncertainty notes
        uncertainty = hyp_data.get("uncertainty_notes", "")
        if uncertainty:
            lines.append(f"**Uncertainty Notes**: {uncertainty}")
            lines.append("")
        
        # Recommended validation
        validation = hyp_data.get("recommended_validation", "")
        if validation:
            lines.append(f"**Recommended Validation**: {validation}")
            lines.append("")
        
        return lines
    
    def _render_insight(self, insight: ReportInsight, indent: str = "") -> List[str]:
        """Render a single insight with evidence status."""
        lines = []
        
        # Status badge
        status_badge = "✅ STRONG" if insight.evidence_status.value == "strong" else "⚠️ PRELIMINARY"
        lines.append(f"{indent}**{insight.insight_id}** ({insight.insight_type}, Confidence: {insight.confidence:.2f}, Status: {status_badge})")
        lines.append("")
        lines.append(f"{indent}{insight.description}")
        lines.append("")
        lines.append(f"{indent}- **Supporting scenarios**: {insight.scenario_count}")
        lines.append(f"{indent}- **Regime coverage count**: {insight.regime_coverage_count}")
        if insight.regime_coverage:
            lines.append(f"{indent}- **Regimes**: {', '.join(insight.regime_coverage[:5])}")
            if len(insight.regime_coverage) > 5:
                lines.append(f"{indent}  ... and {len(insight.regime_coverage) - 5} more regimes")
        if insight.has_contradictions:
            lines.append(f"{indent}- ⚠️ Has been contradicted")
        lines.append("")
        
        return lines
    
    def _render_failure_boundary(self, boundary: FailureBoundary) -> List[str]:
        """Render a failure boundary."""
        lines = []
        
        lines.append(f"### {boundary.parameter_name} ({boundary.boundary_type})")
        lines.append("")
        lines.append(boundary.description)
        if boundary.param_value is not None:
            lines.append(f"- Parameter value: {boundary.param_value}")
        if boundary.return_before is not None and boundary.return_after is not None:
            lines.append(f"- Return change: {boundary.return_before:.2f}% → {boundary.return_after:.2f}%")
        if boundary.drop_magnitude is not None:
            lines.append(f"- Drop magnitude: {boundary.drop_magnitude:.2f}%")
        
        return lines
    
    def _render_experiment(self, experiment: RecommendedExperiment, index: int) -> List[str]:
        """Render a recommended experiment."""
        lines = []
        
        lines.append(f"### {index}. {experiment.title}")
        lines.append("")
        lines.append(f"**Type**: {experiment.proposal_type}  ")
        lines.append(f"**Expected Info Gain**: {experiment.expected_info_gain:.2f}  ")
        lines.append(f"**Priority**: {experiment.priority}/10")
        lines.append("")
        lines.append(experiment.description)
        lines.append("")
        lines.append(f"**Reasoning**: {experiment.reasoning}")
        if experiment.based_on_insights:
            lines.append("")
            lines.append(f"**Based on insights**: {', '.join(experiment.based_on_insights[:3])}")
            if len(experiment.based_on_insights) > 3:
                lines.append(f"  ... and {len(experiment.based_on_insights) - 3} more")
        
        return lines


# Singleton instance
_renderer: Optional[MarkdownRenderer] = None


def get_markdown_renderer() -> MarkdownRenderer:
    """Get or create markdown renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = MarkdownRenderer()
    return _renderer

