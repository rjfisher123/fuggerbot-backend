# A2A Integration Test Guide

## Overview

This document describes the end-to-end A2A (Agent-to-Agent) integration test for FuggerBot's Strategic Reasoner.

## Implementation Status

✅ **Complete:**
- A2A API endpoints (`/api/a2a/ingest`, `/api/a2a/feedback/{signal_id}`, `/api/a2a/status`)
- Signal ingestion handler
- Strategic reasoning integration
- Feedback emission
- End-to-end test script

## Prerequisites

1. **FastAPI Server Running**: The FuggerBot API server must be running on `http://localhost:8000`
2. **Router Registered**: The A2A router is registered in `main.py` (line 83: `app.include_router(a2a_router)`)

## Running the Test

### Step 1: Start the FastAPI Server

```bash
cd /Users/ryanfisher/fuggerbot
# Use the start script or run directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Run the Integration Test

```bash
python tests/test_a2a_integration.py
```

## Test Procedure

The test performs the following steps:

### Step 1: Endpoint Discovery
- Verifies that `/api/a2a/status` is accessible
- Verifies that `/api/a2a/ingest` exists (POST-only endpoint)

### Step 2: Signal Ingestion
- Creates a test A2ASignal payload (simulating ai_inbox_digest v1.0 output)
- Sends POST request to `/api/a2a/ingest`
- Validates response contains:
  - `success: true`
  - `signal_id`
  - `strategic_relevance`
  - `feedback_id`

### Step 3: Feedback Retrieval
- Retrieves feedback for the processed signal
- Validates feedback structure and content

### Step 4: Status Endpoint
- Checks `/api/a2a/status` for processed signals count

## Expected Output

```
============================================================
FuggerBot A2A Integration Test
============================================================
API Base URL: http://localhost:8000

============================================================
Step 1: Endpoint Discovery
============================================================
✅ Status endpoint accessible: http://localhost:8000/api/a2a/status
✅ Ingest endpoint accessible: http://localhost:8000/api/a2a/ingest

============================================================
Step 2: Signal Ingestion
============================================================
Sending signal: sig_test_20251225_151517
  Class: policy
  Summary: Fed signals potential rate cut in Q2 2025...
  Effective Priority: 0.78
  Corroboration: 0.82

Response Status: 200
✅ Signal ingestion successful!
  Signal ID: sig_test_20251225_151517
  Strategic Relevance: 0.80
  Feedback ID: fb_abc123...
  Message: Signal processed successfully. Strategic relevance: 0.80

============================================================
Step 3: Feedback Retrieval
============================================================
✅ Feedback retrieval successful!
  Signal ID: sig_test_20251225_151517
  Feedback Count: 1

  Feedback 1:
    ID: fb_abc123...
    Type: high_interest
    Summary: Policy: Fed signals potential rate cut...
    Strategic Relevance: 0.80
    Time Horizon: quarters

============================================================
Step 4: Status Endpoint
============================================================
✅ Status endpoint working!
  Status: operational
  Processed Signals: 1
  Total Feedback: 1

============================================================
Test Summary
============================================================
✅ End-to-end A2A flow completed successfully!
   Signal ID: sig_test_20251225_151517
   Strategic Relevance: 0.80
```

## API Endpoints

### POST `/api/a2a/ingest`

Ingests a signal from ai_inbox_digest v1.0.

**Request Body:**
```json
{
  "signal_id": "sig_001",
  "signal_class": "policy",
  "summary": "Fed signals potential rate cut",
  "base_priority": 0.85,
  "effective_priority": 0.78,
  "corroboration_score": 0.82,
  "citations": [],
  "created_at": "2025-12-25T15:00:00",
  "signal_lineage": {
    "upstream_message_ids": ["msg_001"],
    "upstream_agents": ["news_filter"],
    "processing_chain": ["news_filter", "priority_engine"]
  },
  "decay_annotation": {...},
  "corroboration_annotation": {...},
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "signal_id": "sig_001",
  "interpretation_id": "int_sig_001",
  "feedback_id": "fb_abc123",
  "strategic_relevance": 0.80,
  "message": "Signal processed successfully..."
}
```

### GET `/api/a2a/feedback/{signal_id}`

Retrieves feedback history for a specific signal.

**Response:**
```json
{
  "signal_id": "sig_001",
  "feedback_count": 1,
  "feedback": [
    {
      "feedback_id": "fb_abc123",
      "signal_id": "sig_001",
      "feedback_type": "high_interest",
      "summary": "...",
      "reasoning": "...",
      "strategic_relevance": 0.80,
      "time_horizon": "quarters",
      "emitted_at": "2025-12-25T15:00:00",
      ...
    }
  ]
}
```

### GET `/api/a2a/status`

Returns A2A adapter status and statistics.

**Response:**
```json
{
  "status": "operational",
  "processed_signals_count": 1,
  "total_feedback_count": 1,
  "processed_signal_ids": ["sig_001"]
}
```

## Troubleshooting

### Endpoints Return 404

**Problem**: Endpoints return 404 Not Found

**Solution**: 
1. Verify the server is running: `curl http://localhost:8000/health`
2. Verify router is registered in `main.py`: Check for `app.include_router(a2a_router)`
3. Restart the FastAPI server to load the new router

### Import Errors

**Problem**: Module import errors when starting server

**Solution**:
1. Verify all dependencies are installed: `pip install -r requirements.txt`
2. Check that `agents/strategic/` module is properly structured
3. Verify Python path includes project root

### Validation Errors

**Problem**: Signal validation fails

**Solution**:
1. Ensure signal payload conforms to `A2ASignal` schema
2. Check required fields are present: `signal_id`, `signal_class`, `summary`, etc.
3. Verify timestamps are ISO 8601 format
4. Check that `effective_priority <= base_priority`

## Next Steps

After successful integration test:

1. **Production Readiness**:
   - Add authentication/authorization
   - Add rate limiting
   - Add request validation middleware
   - Add error handling improvements

2. **Enhanced Strategic Reasoning**:
   - Integrate LLM-based strategic analysis
   - Add regime interaction analysis
   - Integrate memory store for historical context

3. **Monitoring**:
   - Add metrics collection
   - Add logging aggregation
   - Add health check enhancements

## Files

- **API Endpoint**: `api/a2a.py`
- **Test Script**: `tests/test_a2a_integration.py`
- **Strategic Agent**: `agents/strategic/strategic_reasoner_agent.py`
- **A2A Schema**: `agents/strategic/a2a_schema.py`
- **A2A Adapter**: `agents/strategic/a2a_adapter.py`

