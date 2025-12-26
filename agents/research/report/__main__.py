"""
CLI Entrypoint for Report Generation.

Usage:
    python -m research.report --output reports/FRR-2025-02-14.md
"""
import argparse
import sys
import json
from pathlib import Path

from agents.research.report.report_generator import get_report_generator
from agents.research.report.markdown_renderer import get_markdown_renderer
from agents.research.report.data_loader import ReportDataError
import logging

logger = logging.getLogger(__name__)


def main():
    """CLI entrypoint for report generation."""
    parser = argparse.ArgumentParser(description="Generate FuggerBot Research Report")
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path for Markdown report"
    )
    parser.add_argument(
        "--report-id",
        type=str,
        default=None,
        help="Report ID (default: derived from output filename)"
    )
    parser.add_argument(
        "--strategy-version",
        type=str,
        default="1.0.0",
        help="Strategy version identifier"
    )
    parser.add_argument(
        "--simulator-hash",
        type=str,
        default="unknown",
        help="Simulator commit hash"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Optional path to save report JSON (for validation/diffing)"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run ID to generate report for (default: latest)"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use latest iteration (default behavior)"
    )
    
    args = parser.parse_args()
    
    # Derive report ID from filename if not provided
    report_id = args.report_id
    if not report_id:
        output_path = Path(args.output)
        report_id = output_path.stem  # Use filename without extension
    
    try:
        # Generate report
        generator = get_report_generator()
        
        json_output_path = Path(args.json_output) if args.json_output else None
        
        # Determine run_id (--run-id takes precedence, otherwise use latest)
        run_id = args.run_id if args.run_id else None
        
        try:
            report = generator.generate_report(
                report_id=report_id,
                run_id=run_id,
                strategy_version=args.strategy_version,
                simulator_commit_hash=args.simulator_hash,
                output_path=json_output_path
            )
        except ReportDataError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 1
        
        # Render to Markdown
        renderer = get_markdown_renderer()
        markdown = renderer.render(report)
        
        # Write output - resolve to absolute path for consistency
        output_path = Path(args.output).resolve()
        if not output_path.is_absolute():
            # If relative, resolve relative to current working directory
            output_path = Path.cwd() / args.output
        
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure .md extension
        if not output_path.suffix:
            output_path = output_path.with_suffix('.md')
        
        logger.info(f"Writing report to: {output_path.resolve()}")
        
        with open(output_path, 'w') as f:
            f.write(markdown)
        
        # Write meta.json (append-only artifact contract)
        meta_path = output_path.with_suffix('.meta.json')
        meta_data = {
            "report_id": report_id,
            "generated_at": report.metadata.generated_at,
            "strategy_version": report.metadata.strategy_version,
            "research_loop_version": report.metadata.research_loop_version,
            "data_fingerprint": report.metadata.data_fingerprint,
            "scenario_count": report.metadata.total_scenarios,
            "insight_count": report.metadata.total_insights,
            "simulator_commit_hash": report.metadata.simulator_commit_hash
        }
        
        # Append-only: Don't overwrite if exists (preserve history)
        if not meta_path.exists():
            with open(meta_path, 'w') as f:
                json.dump(meta_data, f, indent=2)
        else:
            logger.warning(f"Meta file exists: {meta_path} (preserving existing)")
        
        # Index in vector database (optional, non-blocking)
        try:
            from agents.research.report.vector_logger import get_vector_logger
            vector_logger = get_vector_logger()
            if vector_logger.available:
                vector_logger.index_report(
                    report_id=report_id,
                    report_content=markdown,
                    metadata=meta_data
                )
                print(f"   Vector indexed: ✓")
        except Exception as e:
            logger.warning(f"Vector indexing failed (non-critical): {e}")
        
        print(f"✅ Report generated: {output_path}")
        print(f"   Report ID: {report_id}")
        print(f"   Insights: {len(report.confirmed_insights)}")
        print(f"   Scenarios: {report.metadata.total_scenarios}")
        print(f"   Meta: {meta_path}")
        
        if json_output_path:
            print(f"   JSON saved: {json_output_path}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

