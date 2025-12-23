
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Mock connection manager for testing news
import unittest.mock as mock
from services.news_fetcher import get_news_fetcher

async def test_macro_api():
    print("--- Testing Macro API ---")
    
    # We can't easily spin up full FastAPI in script without uvicorn, 
    # but we can test the logic by calling the router handler directly or mocking.
    # Actually, let's just test get_news_fetcher logic directly.
    
    fetcher = get_news_fetcher()
    
    # 1. Test get_context_async (Source Badging)
    print("Fetching context for SPY...")
    context = await fetcher.get_context_async("SPY")
    print("Context Header:", context.split('\n')[0])
    
    if "RECENT NEWS" in context or "BROADER MARKET" in context or "NEWS FOR" in context:
        print("✅ Context fetching works.")
    else:
        print("❌ Context fetching failed or empty.")
        
    # Check for strict IBKR tagging if we can mock it, but for now just see if format allows it.
    # The new format in get_context_async adds [IBKR] or [RSS].
    
    # Let's mock fetch_ibkr_news to return something
    with mock.patch.object(fetcher, 'fetch_ibkr_news', new_callable=mock.AsyncMock) as mock_ib:
        mock_ib.return_value = [{
            "title": "Mock IBKR News",
            "published": "2023-01-01",
            "link": "",
            "source": "IBKR"
        }]
        
        context_mock = await fetcher.get_context_async("AAPL")
        print("\nMocked Context:\n", context_mock)
        
        if "[IBKR]" in context_mock:
            print("✅ Source Badging Logic Verified.")
        else:
            print("❌ Source Badging Logic Failed.")
            
async def test_job_progress():
    print("\n--- Testing Job Progress Callback ---")
    from daemon.simulator.war_games_runner import WarGamesRunner
    
    runner = WarGamesRunner(db_path=Path("data/market_history.duckdb"))
    
    # Mock run_campaign to be fast
    with mock.patch.object(runner, 'run_campaign') as mock_run:
        mock_run.return_value = None # Just return None to skip logic
        
        callback_called = False
        def cb(pct, msg):
            nonlocal callback_called
            callback_called = True
            print(f"Callback: {pct}% - {msg}")
            
        # Run quick test
        # run_all_scenarios loops scenarios*symbols*params
        # We'll rely on it calling the callback
        try:
             # We need to mock scenarios in run_all_scenarios or just let it run if db is missing it catches exception
             # Actually run_all_scenarios catches exceptions per campaign. 
             # So safely runnable even without DB.
             runner.run_all_scenarios(output_path=Path("data/test_results.json"), progress_callback=cb)
        except Exception as e:
            pass
            
        if callback_called:
            print("✅ Progress Callback Verified.")
        else:
            print("❌ Progress Callback NOT Called.")

async def main():
    await test_macro_api()
    await test_job_progress()

if __name__ == "__main__":
    asyncio.run(main())
