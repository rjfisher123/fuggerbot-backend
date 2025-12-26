"""
Research Reports API - Read-Only Endpoints.

Provides REST API for retrieving research reports.
All endpoints are read-only - reports cannot be modified via API.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import logger

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Reports directory (append-only) - Canonical absolute path
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

# Log configuration on module load
logger.info(f"Reports API initialized - REPORTS_DIR: {REPORTS_DIR.resolve()}")
if not REPORTS_DIR.exists():
    logger.warning(f"Reports directory does not exist: {REPORTS_DIR.resolve()}. Creating...")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
else:
    # Log existing reports count
    md_files = list(REPORTS_DIR.glob("*.md"))
    meta_files = list(REPORTS_DIR.glob("*.meta.json"))
    logger.info(f"Reports directory exists - {len(md_files)} markdown files, {len(meta_files)} meta files")


class ReportMetadata(BaseModel):
    """Report metadata response."""
    report_id: str
    generated_at: str
    strategy_version: str
    research_loop_version: str
    data_fingerprint: str
    scenario_count: int
    insight_count: int
    simulator_commit_hash: str
    markdown_path: Optional[str] = None
    meta_path: Optional[str] = None


@router.get("/", response_model=List[ReportMetadata])
async def list_reports():
    """
    List all available research reports.
    
    Returns:
        List of report metadata, sorted by generated_at (descending)
    """
    if not REPORTS_DIR.exists():
        return []
    
    reports = []
    
    # Find all .meta.json files
    meta_files = list(REPORTS_DIR.glob("*.meta.json"))
    logger.info(f"Found {len(meta_files)} meta.json files in {REPORTS_DIR.resolve()}")
    
    for meta_file in sorted(meta_files, reverse=True):
        try:
            with open(meta_file, 'r') as f:
                meta_data = json.load(f)
            
            # Find corresponding markdown file
            report_id = meta_data.get("report_id", meta_file.stem.replace(".meta", ""))
            md_file = meta_file.with_suffix('').with_suffix('.md')
            
            # Use relative paths from project_root for consistency
            if md_file.exists():
                markdown_path = str(md_file.relative_to(project_root))
            elif (REPORTS_DIR / f"{report_id}.md").exists():
                markdown_path = str((REPORTS_DIR / f"{report_id}.md").relative_to(project_root))
            else:
                markdown_path = None
            
            meta_path = str(meta_file.relative_to(project_root))
            
            report_meta = ReportMetadata(
                report_id=report_id,
                generated_at=meta_data.get("generated_at", ""),
                strategy_version=meta_data.get("strategy_version", "1.0.0"),
                research_loop_version=meta_data.get("research_loop_version", "2.0"),
                data_fingerprint=meta_data.get("data_fingerprint", ""),
                scenario_count=meta_data.get("scenario_count", 0),
                insight_count=meta_data.get("insight_count", 0),
                simulator_commit_hash=meta_data.get("simulator_commit_hash", "unknown"),
                markdown_path=markdown_path,
                meta_path=meta_path
            )
            reports.append(report_meta)
        except Exception as e:
            logger.error(f"Failed to load report metadata {meta_file}: {e}", exc_info=True)
            continue
    
    logger.info(f"Successfully loaded {len(reports)} reports from meta.json files")
    
    # Also include reports without meta.json (legacy support)
    md_files = list(REPORTS_DIR.glob("*.md"))
    logger.info(f"Found {len(md_files)} markdown files (checking for legacy reports)")
    
    for md_file in sorted(md_files, reverse=True):
        report_id = md_file.stem
        # Skip if already in list
        if any(r.report_id == report_id for r in reports):
            continue
        
        # Create minimal metadata
        report_meta = ReportMetadata(
            report_id=report_id,
            generated_at="",
            strategy_version="1.0.0",
            research_loop_version="2.0",
            data_fingerprint="",
            scenario_count=0,
            insight_count=0,
            simulator_commit_hash="unknown",
            markdown_path=str(md_file.relative_to(project_root))
        )
        reports.append(report_meta)
    
    # Sort by generated_at (descending), then by report_id
    reports.sort(key=lambda x: (x.generated_at or "", x.report_id), reverse=True)
    
    logger.info(f"Returning {len(reports)} total reports (sorted)")
    return reports


@router.get("/search")
async def search_reports(
    query: str = Query(..., description="Semantic search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    section: Optional[str] = Query(None, description="Filter by section (e.g., 'confirmed_insights')")
):
    """
    Semantic search over indexed research reports.
    
    Args:
        query: Search query (e.g., "drawdown failures", "trust thresholds")
        limit: Maximum number of results
        section: Optional section filter
    
    Returns:
        List of matching report sections
    """
    try:
        from agents.research.report.vector_logger import get_vector_logger
        vector_logger = get_vector_logger()
        
        if not vector_logger.available:
            return JSONResponse(
                content={"error": "Vector search not available (ChromaDB not installed)"},
                status_code=503
            )
        
        results = vector_logger.search(query=query, limit=limit, section_filter=section)
        
        return JSONResponse(content={
            "query": query,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    format: str = Query("markdown", regex="^(markdown|html|json|meta)$")
):
    """
    Get a specific research report by ID.
    
    Args:
        report_id: Report identifier
        format: Output format (markdown, html, json, or meta)
    
    Returns:
        Report content in requested format
    """
    logger.info(f"Get report called - report_id: {report_id}, format: {format}, REPORTS_DIR: {REPORTS_DIR.resolve()}")
    
    # Find report files
    md_file = REPORTS_DIR / f"{report_id}.md"
    meta_file = REPORTS_DIR / f"{report_id}.meta.json"
    json_file = REPORTS_DIR / f"{report_id}.json"
    
    logger.debug(f"Looking for files: md={md_file.exists()}, meta={meta_file.exists()}, json={json_file.exists()}")
    
    if format == "meta":
        if not meta_file.exists():
            logger.error(f"Report metadata not found: {meta_file.resolve()}")
            raise HTTPException(status_code=404, detail=f"Report metadata not found: {report_id}")
        
        with open(meta_file, 'r') as f:
            meta_data = json.load(f)
        return JSONResponse(content=meta_data)
    
    if format == "json":
        if not json_file.exists():
            raise HTTPException(status_code=404, detail=f"Report JSON not found: {report_id}")
        
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        return JSONResponse(content=json_data)
    
    if format == "html":
        if not md_file.exists():
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
        
        # Convert markdown to HTML (simple conversion)
        with open(md_file, 'r') as f:
            markdown_content = f.read()
        
        # Simple markdown to HTML conversion (or use a library like markdown)
        html_content = _markdown_to_html(markdown_content)
        return PlainTextResponse(content=html_content, media_type="text/html")
    
    # Default: markdown
    if not md_file.exists():
        logger.error(f"Report markdown not found: {md_file.resolve()}")
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    
    with open(md_file, 'r') as f:
        markdown_content = f.read()
    
    return PlainTextResponse(content=markdown_content, media_type="text/markdown")


def _markdown_to_html(markdown: str) -> str:
    """
    Simple markdown to HTML converter.
    
    For production, consider using a library like markdown or markdown2.
    """
    html = markdown
    
    # Headers
    html = html.replace("## ", "<h2>").replace("\n", "</h2>\n", 1) if "## " in html else html
    html = html.replace("### ", "<h3>").replace("\n", "</h3>\n", 1) if "### " in html else html
    
    # Bold
    html = html.replace("**", "<strong>").replace("**", "</strong>")
    
    # Code blocks (basic)
    html = html.replace("```", "<pre><code>").replace("```", "</code></pre>")
    
    # Line breaks
    html = html.replace("\n\n", "</p><p>")
    html = f"<html><head><title>Research Report</title></head><body><p>{html}</p></body></html>"
    
    return html

