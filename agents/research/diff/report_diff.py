"""
Report Diff Engine - Semantic Diff Computation.

Computes semantic diffs between two research reports.
All diff logic is deterministic and replayable.
"""
import logging
from typing import List, Dict, Optional, Tuple

from agents.research.report.report_schema import ResearchReport, ReportInsight, RegimeCoverageEntry, FailureBoundary, RecommendedExperiment
from agents.research.diff.diff_schema import (
    ReportDiff,
    InsightChange,
    RegimeCoverageChange,
    FailureBoundaryChange,
    ProposalRankingChange
)

logger = logging.getLogger(__name__)

# Explicit thresholds for diff classification
CONFIDENCE_CHANGE_THRESHOLD = 0.05  # Minimum change to report
COVERAGE_CHANGE_THRESHOLD = 1.0  # Minimum percentage change to report


class ReportDiffEngine:
    """
    Computes semantic diffs between research reports.
    """
    
    def compute_diff(
        self,
        base_report: ResearchReport,
        compare_report: ResearchReport
    ) -> ReportDiff:
        """
        Compute semantic diff between two reports.
        
        Args:
            base_report: Base report (older)
            compare_report: Compare report (newer)
        
        Returns:
            ReportDiff object
        """
        logger.info(f"Computing diff: {base_report.metadata.report_id} → {compare_report.metadata.report_id}")
        
        # Compute insight changes
        new_insights, removed_insights, confidence_changes = self._diff_insights(
            base_report.confirmed_insights,
            compare_report.confirmed_insights
        )
        
        # Compute regime coverage changes
        regime_coverage_changes = self._diff_regime_coverage(
            base_report.regime_coverage,
            compare_report.regime_coverage
        )
        
        # Compute failure boundary changes
        new_boundaries, removed_boundaries = self._diff_failure_boundaries(
            base_report.failure_boundaries,
            compare_report.failure_boundaries
        )
        
        # Compute proposal ranking changes
        proposal_ranking_changes = self._diff_proposal_rankings(
            base_report.recommended_experiments,
            compare_report.recommended_experiments
        )
        
        # Build diff
        diff = ReportDiff(
            base_report_id=base_report.metadata.report_id,
            compare_report_id=compare_report.metadata.report_id,
            base_generated_at=base_report.metadata.generated_at,
            compare_generated_at=compare_report.metadata.generated_at,
            new_insights=new_insights,
            removed_insights=removed_insights,
            confidence_changes=confidence_changes,
            regime_coverage_changes=regime_coverage_changes,
            new_failure_boundaries=new_boundaries,
            removed_failure_boundaries=removed_boundaries,
            proposal_ranking_changes=proposal_ranking_changes,
            total_insight_changes=len(new_insights) + len(removed_insights) + len(confidence_changes),
            total_coverage_changes=len(regime_coverage_changes)
        )
        
        logger.info(f"Diff computed: {diff.total_insight_changes} insight changes, {diff.total_coverage_changes} coverage changes")
        return diff
    
    def _diff_insights(
        self,
        base_insights: List[ReportInsight],
        compare_insights: List[ReportInsight]
    ) -> Tuple[List[InsightChange], List[InsightChange], List[InsightChange]]:
        """Compute insight differences."""
        # Build maps for efficient lookup
        base_map = {insight.insight_id: insight for insight in base_insights}
        compare_map = {insight.insight_id: insight for insight in compare_insights}
        
        new_insights = []
        removed_insights = []
        confidence_changes = []
        
        # Find new insights
        for insight_id, insight in compare_map.items():
            if insight_id not in base_map:
                new_insights.append(InsightChange(
                    insight_id=insight_id,
                    change_type="new",
                    new_confidence=insight.confidence,
                    description=f"New insight: {insight.description[:100]}"
                ))
        
        # Find removed insights
        for insight_id, insight in base_map.items():
            if insight_id not in compare_map:
                removed_insights.append(InsightChange(
                    insight_id=insight_id,
                    change_type="removed",
                    old_confidence=insight.confidence,
                    description=f"Removed insight: {insight.description[:100]}"
                ))
        
        # Find confidence changes
        for insight_id, compare_insight in compare_map.items():
            if insight_id in base_map:
                base_insight = base_map[insight_id]
                confidence_delta = compare_insight.confidence - base_insight.confidence
                
                # Only report if change exceeds threshold
                if abs(confidence_delta) >= CONFIDENCE_CHANGE_THRESHOLD:
                    confidence_changes.append(InsightChange(
                        insight_id=insight_id,
                        change_type="confidence_changed",
                        old_confidence=base_insight.confidence,
                        new_confidence=compare_insight.confidence,
                        confidence_delta=confidence_delta,
                        description=f"Confidence changed: {base_insight.confidence:.2f} → {compare_insight.confidence:.2f} ({confidence_delta:+.2f})"
                    ))
        
        return new_insights, removed_insights, confidence_changes
    
    def _diff_regime_coverage(
        self,
        base_coverage: List[RegimeCoverageEntry],
        compare_coverage: List[RegimeCoverageEntry]
    ) -> List[RegimeCoverageChange]:
        """Compute regime coverage differences."""
        # Build maps for efficient lookup
        base_map = {entry.regime_id: entry for entry in base_coverage}
        compare_map = {entry.regime_id: entry for entry in compare_coverage}
        
        changes = []
        
        # Check all regimes in either report
        all_regime_ids = set(base_map.keys()) | set(compare_map.keys())
        
        for regime_id in all_regime_ids:
            base_entry = base_map.get(regime_id)
            compare_entry = compare_map.get(regime_id)
            
            # If regime exists in both, check for changes
            if base_entry and compare_entry:
                coverage_delta = compare_entry.coverage_percentage - base_entry.coverage_percentage
                
                # Only report if change exceeds threshold
                if abs(coverage_delta) >= COVERAGE_CHANGE_THRESHOLD:
                    changes.append(RegimeCoverageChange(
                        regime_id=regime_id,
                        regime_description=compare_entry.regime_description,
                        old_coverage_pct=base_entry.coverage_percentage,
                        new_coverage_pct=compare_entry.coverage_percentage,
                        coverage_delta=coverage_delta,
                        old_scenario_count=base_entry.scenario_count,
                        new_scenario_count=compare_entry.scenario_count
                    ))
            elif compare_entry and not base_entry:
                # New regime coverage
                changes.append(RegimeCoverageChange(
                    regime_id=regime_id,
                    regime_description=compare_entry.regime_description,
                    old_coverage_pct=0.0,
                    new_coverage_pct=compare_entry.coverage_percentage,
                    coverage_delta=compare_entry.coverage_percentage,
                    old_scenario_count=0,
                    new_scenario_count=compare_entry.scenario_count
                ))
        
        return changes
    
    def _diff_failure_boundaries(
        self,
        base_boundaries: List[FailureBoundary],
        compare_boundaries: List[FailureBoundary]
    ) -> Tuple[List[FailureBoundaryChange], List[FailureBoundaryChange]]:
        """Compute failure boundary differences."""
        # Create keys for boundaries (param_name + boundary_type)
        base_keys = {f"{b.parameter_name}:{b.boundary_type}": b for b in base_boundaries}
        compare_keys = {f"{b.parameter_name}:{b.boundary_type}": b for b in compare_boundaries}
        
        new_boundaries = []
        removed_boundaries = []
        
        # Find new boundaries
        for key, boundary in compare_keys.items():
            if key not in base_keys:
                new_boundaries.append(FailureBoundaryChange(
                    parameter_name=boundary.parameter_name,
                    change_type="new_boundary",
                    boundary_type=boundary.boundary_type,
                    description=f"New {boundary.boundary_type} detected for {boundary.parameter_name}: {boundary.description}"
                ))
        
        # Find removed boundaries
        for key, boundary in base_keys.items():
            if key not in compare_keys:
                removed_boundaries.append(FailureBoundaryChange(
                    parameter_name=boundary.parameter_name,
                    change_type="removed_boundary",
                    boundary_type=boundary.boundary_type,
                    description=f"{boundary.boundary_type} no longer detected for {boundary.parameter_name}"
                ))
        
        return new_boundaries, removed_boundaries
    
    def _diff_proposal_rankings(
        self,
        base_proposals: List[RecommendedExperiment],
        compare_proposals: List[RecommendedExperiment]
    ) -> List[ProposalRankingChange]:
        """Compute proposal ranking differences."""
        # Build maps for efficient lookup
        base_map = {proposal.proposal_id: (i + 1, proposal) for i, proposal in enumerate(base_proposals)}
        compare_map = {proposal.proposal_id: (i + 1, proposal) for i, proposal in enumerate(compare_proposals)}
        
        changes = []
        
        # Check all proposals in either report
        all_proposal_ids = set(base_map.keys()) | set(compare_map.keys())
        
        for proposal_id in all_proposal_ids:
            base_data = base_map.get(proposal_id)
            compare_data = compare_map.get(proposal_id)
            
            if base_data and compare_data:
                base_rank, base_proposal = base_data
                compare_rank, compare_proposal = compare_data
                
                # Check if rank or info gain changed
                rank_changed = base_rank != compare_rank
                info_gain_changed = abs(base_proposal.expected_info_gain - compare_proposal.expected_info_gain) > 0.01
                
                if rank_changed or info_gain_changed:
                    # Format description
                    desc_parts = []
                    if rank_changed:
                        desc_parts.append(f"Rank: {base_rank} → {compare_rank}")
                    if info_gain_changed:
                        desc_parts.append(f"Info gain: {base_proposal.expected_info_gain:.2f} → {compare_proposal.expected_info_gain:.2f}")
                    
                    changes.append(ProposalRankingChange(
                        proposal_id=proposal_id,
                        old_rank=base_rank if rank_changed else None,
                        new_rank=compare_rank if rank_changed else None,
                        old_info_gain=base_proposal.expected_info_gain if info_gain_changed else None,
                        new_info_gain=compare_proposal.expected_info_gain if info_gain_changed else None,
                        description=" | ".join(desc_parts) if desc_parts else "Proposal updated"
                    ))
            elif compare_data and not base_data:
                # New proposal
                compare_rank, compare_proposal = compare_data
                changes.append(ProposalRankingChange(
                    proposal_id=proposal_id,
                    new_rank=compare_rank,
                    new_info_gain=compare_proposal.expected_info_gain,
                    description=f"New proposal at rank {compare_rank}: {compare_proposal.title}"
                ))
        
        return changes
    


# Singleton instance
_diff_engine: Optional[ReportDiffEngine] = None


def get_diff_engine() -> ReportDiffEngine:
    """Get or create diff engine instance."""
    global _diff_engine
    if _diff_engine is None:
        _diff_engine = ReportDiffEngine()
    return _diff_engine

