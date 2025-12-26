"""
CLI Entrypoint for Report Diffing.

Usage:
    python -m research.diff --base reports/FRR-2025-02-01.md --compare reports/FRR-2025-02-14.md --output reports/diff-0201-0214.md
"""
import argparse
import sys
import json
from typing import Optional
from pathlib import Path

from agents.research.report.report_schema import ResearchReport
from agents.research.diff.report_diff import get_diff_engine
from agents.research.diff.diff_renderer import get_diff_renderer


def load_report_from_json(json_path: Path) -> ResearchReport:
    """Load report from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return ResearchReport.model_validate(data)


def find_json_for_markdown(markdown_path: Path) -> Optional[Path]:
    """Try to find corresponding JSON file for a Markdown report."""
    # Try same directory, same name but .json extension
    json_path = markdown_path.with_suffix('.json')
    if json_path.exists():
        return json_path
    
    # Try in a json/ subdirectory
    json_path = markdown_path.parent / "json" / (markdown_path.stem + ".json")
    if json_path.exists():
        return json_path
    
    return None


def main():
    """CLI entrypoint for report diffing."""
    parser = argparse.ArgumentParser(description="Compare two FuggerBot Research Reports")
    parser.add_argument(
        "--base",
        type=str,
        required=True,
        help="Path to base report (JSON or Markdown)"
    )
    parser.add_argument(
        "--compare",
        type=str,
        required=True,
        help="Path to compare report (JSON or Markdown)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path for diff Markdown"
    )
    parser.add_argument(
        "--base-json",
        type=str,
        default=None,
        help="Explicit path to base report JSON (if Markdown provided)"
    )
    parser.add_argument(
        "--compare-json",
        type=str,
        default=None,
        help="Explicit path to compare report JSON (if Markdown provided)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load reports
        base_path = Path(args.base)
        compare_path = Path(args.compare)
        
        # Determine JSON paths
        base_json_path = Path(args.base_json) if args.base_json else None
        compare_json_path = Path(args.compare_json) if args.compare_json else None
        
        # If Markdown provided, try to find JSON
        if base_path.suffix == '.md' and not base_json_path:
            base_json_path = find_json_for_markdown(base_path)
            if not base_json_path:
                print(f"❌ Error: No JSON file found for base report {base_path}", file=sys.stderr)
                print("   Please provide --base-json or ensure .json file exists", file=sys.stderr)
                return 1
        
        if compare_path.suffix == '.md' and not compare_json_path:
            compare_json_path = find_json_for_markdown(compare_path)
            if not compare_json_path:
                print(f"❌ Error: No JSON file found for compare report {compare_path}", file=sys.stderr)
                print("   Please provide --compare-json or ensure .json file exists", file=sys.stderr)
                return 1
        
        # Use JSON path if available, otherwise use provided path
        base_report_path = base_json_path if base_json_path else base_path
        compare_report_path = compare_json_path if compare_json_path else compare_path
        
        # Load reports
        if base_report_path.suffix != '.json':
            print(f"❌ Error: Base report must be JSON format, got {base_report_path.suffix}", file=sys.stderr)
            return 1
        
        if compare_report_path.suffix != '.json':
            print(f"❌ Error: Compare report must be JSON format, got {compare_report_path.suffix}", file=sys.stderr)
            return 1
        
        print(f"Loading base report: {base_report_path}")
        base_report = load_report_from_json(base_report_path)
        
        print(f"Loading compare report: {compare_report_path}")
        compare_report = load_report_from_json(compare_report_path)
        
        # Compute diff
        diff_engine = get_diff_engine()
        diff = diff_engine.compute_diff(base_report, compare_report)
        
        # Render diff
        renderer = get_diff_renderer()
        markdown = renderer.render(diff)
        
        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(markdown)
        
        print(f"✅ Diff generated: {output_path}")
        print(f"   Insight changes: {diff.total_insight_changes}")
        print(f"   Coverage changes: {diff.total_coverage_changes}")
        print(f"   New boundaries: {len(diff.new_failure_boundaries)}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error computing diff: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

