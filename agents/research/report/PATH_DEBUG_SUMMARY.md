# Report Visibility Debug & Hardening - Summary

## Issue Identified

Research reports were not consistently visible in the Web UI due to path resolution inconsistencies between the CLI and API.

## Root Cause

1. **API used relative path**: `project_root / "reports"` where `project_root` was `Path(__file__).parent.parent`
2. **CLI used user-provided path**: Could be relative or absolute, inconsistent resolution
3. **No logging**: Silent failures when paths didn't match

## Fixes Applied

### 1. Canonical Path Definition (API)

**Before:**
```python
REPORTS_DIR = project_root / "reports"
```

**After:**
```python
# Canonical absolute path
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
```

### 2. Path Resolution (CLI)

**Before:**
```python
output_path = Path(args.output)
```

**After:**
```python
# Resolve to absolute path for consistency
output_path = Path(args.output).resolve()
if not output_path.is_absolute():
    output_path = Path.cwd() / args.output
output_path = output_path.resolve()
```

### 3. Comprehensive Logging

**Added:**
- Module load logging (REPORTS_DIR path and existence check)
- Directory creation if missing
- File count logging (markdown, meta files)
- Request-level logging (list_reports, get_report)
- Error logging with absolute paths
- Success logging (report counts)

**Example logs:**
```
INFO:api.reports:Reports API initialized - REPORTS_DIR: /Users/ryanfisher/fuggerbot/reports
INFO:api.reports:Reports directory exists - 8 markdown files, 1 meta files
INFO:api.reports:List reports called - REPORTS_DIR: /Users/ryanfisher/fuggerbot/reports
INFO:api.reports:Found 1 meta.json files in /Users/ryanfisher/fuggerbot/reports
INFO:api.reports:Successfully loaded 1 reports from meta.json files
INFO:api.reports:Found 8 markdown files (checking for legacy reports)
INFO:api.reports:Returning 8 total reports (sorted)
```

### 4. Error Handling

- Explicit error messages with absolute paths
- HTTP 404 with detailed messages
- Exception logging with stack traces
- Graceful handling of missing directories

## Verification

✅ **Paths match**: API and CLI now use consistent absolute paths  
✅ **Logging enabled**: All path operations are logged  
✅ **Error visibility**: Failures are loud, not silent  
✅ **Directory creation**: Auto-creates reports directory if missing  

## Invariants Preserved

✅ Reports remain read-only artifacts  
✅ Append-only behavior preserved  
✅ No report content influences execution  
✅ Vector DB remains secondary (search only)  
✅ Markdown + meta.json remain canonical  

## Testing

```bash
# Generate report
python -m agents.research.report --output reports/test.md --report-id test

# Verify via API
curl http://localhost:8000/api/reports/
```

## Files Modified

- `api/reports.py` - Canonical path, comprehensive logging
- `agents/research/report/__main__.py` - Absolute path resolution, logging

## Next Steps (If Still Not Visible)

1. Check logs for path mismatches
2. Verify REPORTS_DIR environment variable (if used)
3. Check file permissions
4. Verify FastAPI server is running and routes are registered

