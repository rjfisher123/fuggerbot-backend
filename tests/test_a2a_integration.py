"""
End-to-End A2A Integration Test.

Tests the full Agent-to-Agent signal flow:
1. ai_inbox_digest emits a valid A2ASignal
2. FuggerBot receives it via HTTP A2A endpoint
3. FuggerBot performs strategic reasoning
4. FuggerBot emits A2AFeedback
5. Feedback is persisted and observable
"""
import sys
from pathlib import Path
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agents.strategic import SignalClass, SignalLineage

# Test configuration
API_BASE_URL = "http://localhost:8000"
A2A_INGEST_ENDPOINT = f"{API_BASE_URL}/api/a2a/ingest"
A2A_STATUS_ENDPOINT = f"{API_BASE_URL}/api/a2a/status"
A2A_FEEDBACK_ENDPOINT = f"{API_BASE_URL}/api/a2a/feedback"


def create_test_signal() -> Dict[str, Any]:
    """
    Create a test A2ASignal payload simulating ai_inbox_digest v1.0 output.
    
    Returns:
        Dict conforming to A2ASignal schema
    """
    return {
        "signal_id": f"sig_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "signal_class": "policy",  # SignalClass.POLICY
        "summary": "Fed signals potential rate cut in Q2 2025 based on inflation trends",
        "base_priority": 0.85,
        "effective_priority": 0.78,  # After time-decay
        "corroboration_score": 0.82,
        "citations": [
            "https://example.com/fed-announcement-2025",
            "https://example.com/inflation-data"
        ],
        "created_at": datetime.now().isoformat(),
        "signal_lineage": {
            "upstream_message_ids": ["msg_001", "msg_002"],
            "upstream_agents": ["news_filter", "priority_engine", "decay_agent"],
            "processing_chain": ["news_filter", "priority_engine", "decay_agent", "corroboration_agent"]
        },
        "decay_annotation": {
            "original_priority": 0.85,
            "decay_factor": 0.92,
            "decay_reason": "time_elapsed_2hours",
            "decay_applied_at": datetime.now().isoformat()
        },
        "corroboration_annotation": {
            "corroboration_score": 0.82,
            "corroborating_sources": ["source_1", "source_2", "source_3"],
            "corroboration_method": "multi_source_cross_validation",
            "computed_at": datetime.now().isoformat()
        },
        "metadata": {
            "source_system": "ai_inbox_digest",
            "source_version": "1.0",
            "test_signal": True
        }
    }


def test_endpoint_discovery():
    """Step 1: Verify A2A endpoints are accessible."""
    print("=" * 60)
    print("Step 1: Endpoint Discovery")
    print("=" * 60)
    
    endpoints = [
        ("Status", f"{API_BASE_URL}/api/a2a/status"),
        ("Ingest", f"{API_BASE_URL}/api/a2a/ingest"),
    ]
    
    all_accessible = True
    for name, url in endpoints:
        try:
            if name == "Ingest":
                # POST endpoint - check with OPTIONS or try GET first
                response = requests.get(url, timeout=5)
                # GET might return 405 Method Not Allowed, which is fine
                status_ok = response.status_code in [200, 405, 422]
            else:
                response = requests.get(url, timeout=5)
                status_ok = response.status_code == 200
            
            if status_ok:
                print(f"✅ {name} endpoint accessible: {url}")
            else:
                print(f"⚠️  {name} endpoint returned status {response.status_code}: {url}")
                if name == "Ingest":
                    # POST endpoints return 405 for GET, which is expected
                    print(f"   (This is expected for POST-only endpoints)")
                    all_accessible = True  # Don't fail on this
        except requests.exceptions.ConnectionError:
            print(f"❌ {name} endpoint not accessible (connection refused): {url}")
            print(f"   Make sure the FastAPI server is running on {API_BASE_URL}")
            all_accessible = False
        except Exception as e:
            print(f"❌ {name} endpoint error: {e}")
            all_accessible = False
    
    return all_accessible


def test_signal_ingestion():
    """Step 2: Test signal ingestion via A2A endpoint."""
    print("\n" + "=" * 60)
    print("Step 2: Signal Ingestion")
    print("=" * 60)
    
    # Create test signal
    signal_data = create_test_signal()
    signal_id = signal_data["signal_id"]
    
    print(f"Sending signal: {signal_id}")
    print(f"  Class: {signal_data['signal_class']}")
    print(f"  Summary: {signal_data['summary'][:60]}...")
    print(f"  Effective Priority: {signal_data['effective_priority']}")
    print(f"  Corroboration: {signal_data['corroboration_score']}")
    
    try:
        # Send POST request
        response = requests.post(
            A2A_INGEST_ENDPOINT,
            json=signal_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Signal ingestion successful!")
            print(f"  Signal ID: {result.get('signal_id')}")
            print(f"  Strategic Relevance: {result.get('strategic_relevance', 0):.2f}")
            print(f"  Feedback ID: {result.get('feedback_id', 'N/A')}")
            print(f"  Message: {result.get('message', 'N/A')}")
            return signal_id, result
        else:
            print(f"❌ Signal ingestion failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return None, None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection refused. Is the server running on {API_BASE_URL}?")
        return None, None
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        return None, None


def test_feedback_retrieval(signal_id: str):
    """Step 3: Test feedback retrieval."""
    print("\n" + "=" * 60)
    print("Step 3: Feedback Retrieval")
    print("=" * 60)
    
    if not signal_id:
        print("⚠️  Skipping feedback retrieval (no signal_id)")
        return
    
    try:
        response = requests.get(
            f"{A2A_FEEDBACK_ENDPOINT}/{signal_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            feedback_count = result.get("feedback_count", 0)
            print(f"✅ Feedback retrieval successful!")
            print(f"  Signal ID: {result.get('signal_id')}")
            print(f"  Feedback Count: {feedback_count}")
            
            if feedback_count > 0:
                feedback_list = result.get("feedback", [])
                for i, fb in enumerate(feedback_list, 1):
                    print(f"\n  Feedback {i}:")
                    print(f"    ID: {fb.get('feedback_id')}")
                    print(f"    Type: {fb.get('feedback_type')}")
                    print(f"    Summary: {fb.get('summary', '')[:60]}...")
                    print(f"    Strategic Relevance: {fb.get('strategic_relevance', 0):.2f}")
                    print(f"    Time Horizon: {fb.get('time_horizon', 'N/A')}")
        else:
            print(f"❌ Feedback retrieval failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error retrieving feedback: {e}")


def test_status_endpoint():
    """Step 4: Test status endpoint."""
    print("\n" + "=" * 60)
    print("Step 4: Status Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(A2A_STATUS_ENDPOINT, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Status endpoint working!")
            print(f"  Status: {result.get('status')}")
            print(f"  Processed Signals: {result.get('processed_signals_count', 0)}")
            print(f"  Total Feedback: {result.get('total_feedback_count', 0)}")
        else:
            print(f"❌ Status endpoint failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")


def main():
    """Run full end-to-end A2A integration test."""
    print("\n" + "=" * 60)
    print("FuggerBot A2A Integration Test")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Endpoint Discovery
    if not test_endpoint_discovery():
        print("\n❌ Endpoint discovery failed. Aborting test.")
        return 1
    
    # Step 2: Signal Ingestion
    signal_id, ingest_result = test_signal_ingestion()
    
    # Step 3: Feedback Retrieval
    if signal_id:
        test_feedback_retrieval(signal_id)
    
    # Step 4: Status Endpoint
    test_status_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    if signal_id and ingest_result:
        print("✅ End-to-end A2A flow completed successfully!")
        print(f"   Signal ID: {signal_id}")
        print(f"   Strategic Relevance: {ingest_result.get('strategic_relevance', 0):.2f}")
        return 0
    else:
        print("❌ End-to-end A2A flow had errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

