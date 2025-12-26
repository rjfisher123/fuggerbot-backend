"""
Vector Logger for Research Reports - Semantic Search Indexing.

Indexes research reports by section for semantic retrieval and longitudinal analysis.
All indexing is append-only and read-only - reports cannot influence execution.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import vector DB libraries (optional dependencies)
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not available - vector logging disabled. Install with: pip install chromadb")


class ReportVectorLogger:
    """
    Logs research reports to vector database for semantic search.
    
    Each report is chunked by section and indexed with metadata.
    All operations are append-only and read-only.
    """
    
    def __init__(self, vector_db_path: Optional[Path] = None):
        """
        Initialize vector logger.
        
        Args:
            vector_db_path: Path to vector database (default: data/vector_db)
        """
        if not CHROMA_AVAILABLE:
            logger.warning("Vector logging disabled - ChromaDB not installed")
            self.available = False
            return
        
        self.available = True
        
        if vector_db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            vector_db_path = project_root / "data" / "vector_db"
        
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.vector_db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="research_reports",
                metadata={"description": "FuggerBot research reports for semantic search"}
            )
            
            logger.info(f"VectorLogger initialized (db: {self.vector_db_path})")
        except Exception as e:
            logger.error(f"Failed to initialize vector logger: {e}")
            self.available = False
    
    def index_report(
        self,
        report_id: str,
        report_content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Index a research report by section.
        
        Args:
            report_id: Report identifier
            report_content: Full markdown report content
            metadata: Report metadata (from meta.json)
        
        Returns:
            True if indexing succeeded, False otherwise
        """
        if not self.available:
            return False
        
        try:
            # Check if already indexed (append-only: don't re-index)
            existing = self.collection.get(
                where={"report_id": report_id},
                limit=1
            )
            if existing["ids"]:
                logger.info(f"Report {report_id} already indexed (append-only)")
                return True
            
            # Chunk report by section
            sections = self._chunk_by_section(report_content, report_id, metadata)
            
            if not sections:
                logger.warning(f"No sections found in report {report_id}")
                return False
            
            # Index each section
            ids = []
            documents = []
            metadatas = []
            
            for section in sections:
                ids.append(section["id"])
                documents.append(section["content"])
                metadatas.append(section["metadata"])
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Indexed report {report_id} ({len(sections)} sections)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index report {report_id}: {e}", exc_info=True)
            return False
    
    def _chunk_by_section(
        self,
        content: str,
        report_id: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk report content by section.
        
        Sections:
        - Executive Summary
        - Confirmed Insights
        - Preliminary Insights
        - Failure Boundaries
        - Historical Context (if present)
        
        Args:
            content: Markdown report content
            report_id: Report identifier
            metadata: Report metadata
        
        Returns:
            List of section chunks with metadata
        """
        sections = []
        lines = content.split('\n')
        
        current_section = None
        current_content = []
        
        for line in lines:
            # Detect section headers
            if line.startswith('## '):
                # Save previous section
                if current_section and current_content:
                    sections.append({
                        "id": f"{report_id}_{current_section}",
                        "content": '\n'.join(current_content),
                        "metadata": {
                            "report_id": report_id,
                            "section": current_section,
                            "generated_at": metadata.get("generated_at", ""),
                            "strategy_version": metadata.get("strategy_version", "1.0.0"),
                            "data_fingerprint": metadata.get("data_fingerprint", ""),
                            "deterministic": True
                        }
                    })
                
                # Start new section
                section_name = line.replace('## ', '').strip()
                current_section = self._normalize_section_name(section_name)
                current_content = [line]
            elif line.startswith('### '):
                # Subsection - include in current section
                current_content.append(line)
            else:
                # Regular content
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections.append({
                "id": f"{report_id}_{current_section}",
                "content": '\n'.join(current_content),
                "metadata": {
                    "report_id": report_id,
                    "section": current_section,
                    "generated_at": metadata.get("generated_at", ""),
                    "strategy_version": metadata.get("strategy_version", "1.0.0"),
                    "data_fingerprint": metadata.get("data_fingerprint", ""),
                    "deterministic": True
                }
            })
        
        return sections
    
    def _normalize_section_name(self, name: str) -> str:
        """Normalize section name for consistent indexing."""
        name_lower = name.lower()
        
        # Map common section names
        if "executive" in name_lower or "summary" in name_lower:
            return "executive_summary"
        elif "confirmed insights" in name_lower or "strong insights" in name_lower:
            return "confirmed_insights"
        elif "preliminary insights" in name_lower:
            return "preliminary_insights"
        elif "failure boundaries" in name_lower:
            return "failure_boundaries"
        elif "historical context" in name_lower or "historonics" in name_lower:
            return "historical_context"
        elif "recommended experiments" in name_lower:
            return "recommended_experiments"
        elif "regime coverage" in name_lower:
            return "regime_coverage"
        else:
            # Use normalized version of name
            return name_lower.replace(' ', '_').replace('-', '_')
    
    def search(
        self,
        query: str,
        limit: int = 10,
        section_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over indexed reports.
        
        Args:
            query: Search query
            limit: Maximum number of results
            section_filter: Optional section filter (e.g., "confirmed_insights")
        
        Returns:
            List of matching chunks with metadata
        """
        if not self.available:
            return []
        
        try:
            where_clause = {"deterministic": True}
            if section_filter:
                where_clause["section"] = section_filter
            
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []


# Singleton instance
_vector_logger: Optional[ReportVectorLogger] = None


def get_vector_logger(vector_db_path: Optional[Path] = None) -> ReportVectorLogger:
    """Get or create vector logger instance."""
    global _vector_logger
    if _vector_logger is None:
        _vector_logger = ReportVectorLogger(vector_db_path=vector_db_path)
    return _vector_logger

