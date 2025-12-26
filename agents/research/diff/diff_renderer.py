"""
Diff Renderer - Deterministic Diff Rendering.

Renders ReportDiff objects to Markdown format.
All formatting is deterministic and stable across runs.
"""
import logging
from typing import List, Optional

from agents.research.diff.diff_schema import (
    ReportDiff,
    InsightChange,
    RegimeCoverageChange,
    FailureBoundaryChange,
    ProposalRankingChange
)

logger = logging.getLogger(__name__)


class DiffRenderer:
    """
    Renders report diffs to Markdown format.
    """
    
    def render(self, diff: ReportDiff) -> str:
        """
        Render complete diff to Markdown.
        
        Args:
            diff: ReportDiff object
        
        Returns:
            Markdown string
        """
        lines = []
        
        # Title
        lines.append("## Research Report Diff")
        lines.append("")
        lines.append(f"**Base Report**: {diff.base_report_id}")
        lines.append(f"**Compare Report**: {diff.compare_report_id}")
        lines.append("")
        lines.append(f"- Base generated: {diff.base_generated_at}")
        lines.append(f"- Compare generated: {diff.compare_generated_at}")
        lines.append(f"- Diff generated: {diff.generated_at}")
        lines.append("")
        
        # Summary
        lines.append("### Summary")
        lines.append("")
        lines.append(f"- Total insight changes: {diff.total_insight_changes}")
        lines.append(f"- New insights: {len(diff.new_insights)}")
        lines.append(f"- Removed insights: {len(diff.removed_insights)}")
        lines.append(f"- Confidence changes: {len(diff.confidence_changes)}")
        lines.append(f"- Regime coverage changes: {diff.total_coverage_changes}")
        lines.append(f"- New failure boundaries: {len(diff.new_failure_boundaries)}")
        lines.append(f"- Removed failure boundaries: {len(diff.removed_failure_boundaries)}")
        lines.append(f"- Proposal ranking changes: {len(diff.proposal_ranking_changes)}")
        lines.append("")
        
        # New Insights
        if diff.new_insights:
            lines.append("### New Insights")
            lines.append("")
            for change in diff.new_insights:
                lines.append(f"- **{change.insight_id}** (Confidence: {change.new_confidence:.2f})")
                if change.description:
                    lines.append(f"  - {change.description}")
            lines.append("")
        
        # Removed Insights
        if diff.removed_insights:
            lines.append("### Removed Insights")
            lines.append("")
            for change in diff.removed_insights:
                lines.append(f"- **{change.insight_id}** (Confidence: {change.old_confidence:.2f})")
                if change.description:
                    lines.append(f"  - {change.description}")
            lines.append("")
        
        # Confidence Changes
        if diff.confidence_changes:
            lines.append("### Confidence Changes")
            lines.append("")
            
            # Sort by magnitude of change (descending)
            sorted_changes = sorted(
                diff.confidence_changes,
                key=lambda x: abs(x.confidence_delta) if x.confidence_delta else 0,
                reverse=True
            )
            
            for change in sorted_changes:
                direction = "↑" if change.confidence_delta and change.confidence_delta > 0 else "↓"
                lines.append(
                    f"- **{change.insight_id}**: "
                    f"{change.old_confidence:.2f} → {change.new_confidence:.2f} ({direction})"
                )
                if change.confidence_delta:
                    lines.append(f"  - Delta: {change.confidence_delta:+.2f}")
            lines.append("")
        
        # Regime Coverage Changes
        if diff.regime_coverage_changes:
            lines.append("### Regime Coverage Changes")
            lines.append("")
            
            # Sort by magnitude of change (descending)
            sorted_changes = sorted(
                diff.regime_coverage_changes,
                key=lambda x: abs(x.coverage_delta),
                reverse=True
            )
            
            for change in sorted_changes:
                direction = "↑" if change.coverage_delta > 0 else "↓"
                lines.append(
                    f"- **{change.regime_id}**: "
                    f"{change.old_coverage_pct:.1f}% → {change.new_coverage_pct:.1f}% ({direction})"
                )
                lines.append(f"  - {change.regime_description}")
                lines.append(f"  - Scenarios: {change.old_scenario_count} → {change.new_scenario_count}")
            lines.append("")
        
        # New Failure Boundaries
        if diff.new_failure_boundaries:
            lines.append("### New Failure Boundaries")
            lines.append("")
            for change in diff.new_failure_boundaries:
                lines.append(f"- **{change.parameter_name}** ({change.boundary_type})")
                lines.append(f"  - {change.description}")
            lines.append("")
        
        # Removed Failure Boundaries
        if diff.removed_failure_boundaries:
            lines.append("### Removed Failure Boundaries")
            lines.append("")
            for change in diff.removed_failure_boundaries:
                lines.append(f"- **{change.parameter_name}** ({change.boundary_type})")
                lines.append(f"  - {change.description}")
            lines.append("")
        
        # Proposal Ranking Changes
        if diff.proposal_ranking_changes:
            lines.append("### Proposal Ranking Changes")
            lines.append("")
            
            # Group by type of change
            rank_changes = [c for c in diff.proposal_ranking_changes if c.old_rank is not None and c.new_rank is not None]
            info_gain_changes = [c for c in diff.proposal_ranking_changes if c.old_info_gain is not None and c.new_info_gain is not None]
            
            if rank_changes:
                lines.append("**Rank Changes:**")
                lines.append("")
                for change in rank_changes:
                    lines.append(f"- **{change.proposal_id}**: Rank {change.old_rank} → {change.new_rank}")
                lines.append("")
            
            if info_gain_changes:
                lines.append("**Info Gain Changes:**")
                lines.append("")
                for change in info_gain_changes:
                    lines.append(
                        f"- **{change.proposal_id}**: "
                        f"{change.old_info_gain:.2f} → {change.new_info_gain:.2f}"
                    )
                lines.append("")
        
        return "\n".join(lines)


# Singleton instance
_diff_renderer: Optional[DiffRenderer] = None


def get_diff_renderer() -> DiffRenderer:
    """Get or create diff renderer instance."""
    global _diff_renderer
    if _diff_renderer is None:
        _diff_renderer = DiffRenderer()
    return _diff_renderer

