"""
System Verification Script.

Comprehensive health check for FuggerBot system components.
Verifies data lake, learning book, war games results, and system configuration.
"""
import sys
from pathlib import Path
import json
import duckdb

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_data_lake() -> bool:
    """Verify Data Lake (DuckDB) integrity."""
    print("\n" + "=" * 80)
    print("CHECKING: Data Lake (market_history.duckdb)")
    print("=" * 80)
    
    db_path = PROJECT_ROOT / "data" / "market_history.duckdb"
    
    if not db_path.exists():
        print("❌ FAIL: Data Lake not found at", db_path)
        return False
    
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        
        # Check table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        if not tables:
            print("❌ FAIL: No tables found in Data Lake")
            return False
        
        print(f"✅ Tables found: {[t[0] for t in tables]}")
        
        # Check row count
        row_count = conn.execute("SELECT COUNT(*) FROM ohlcv_history").fetchone()[0]
        print(f"✅ Total rows: {row_count:,}")
        
        # Check symbols
        symbols = conn.execute("SELECT DISTINCT symbol FROM ohlcv_history").fetchall()
        symbol_list = [s[0] for s in symbols]
        print(f"✅ Symbols: {', '.join(symbol_list)}")
        
        # Check for NVDA specifically (per mission requirements)
        if 'NVDA' in symbol_list:
            nvda_rows = conn.execute("SELECT COUNT(*) FROM ohlcv_history WHERE symbol = 'NVDA'").fetchone()[0]
            print(f"✅ NVDA data: {nvda_rows:,} rows")
        else:
            print("⚠️  WARNING: NVDA not found in Data Lake")
        
        conn.close()
        
        if row_count > 1000:
            print("✅ PASS: Data Lake OK")
            return True
        else:
            print("⚠️  WARNING: Data Lake has very few rows")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error checking Data Lake: {e}")
        return False


def check_learning_book() -> bool:
    """Verify Learning Book integrity."""
    print("\n" + "=" * 80)
    print("CHECKING: Learning Book (learning_book.json)")
    print("=" * 80)
    
    book_path = PROJECT_ROOT / "data" / "learning_book.json"
    
    if not book_path.exists():
        print("❌ FAIL: Learning Book not found at", book_path)
        return False
    
    try:
        with open(book_path, 'r') as f:
            data = json.load(f)
        
        if not data:
            print("❌ FAIL: Learning Book is empty")
            return False
        
        # Check structure (supports both 'episodes' and 'patterns' formats)
        if 'episodes' in data:
            records = data['episodes']
            record_type = "episodes"
        elif 'patterns' in data:
            records = data['patterns']
            record_type = "patterns"
        else:
            print("⚠️  WARNING: Learning Book structure unknown (no 'episodes' or 'patterns' key)")
            return False
        
        print(f"✅ {record_type.capitalize()}: {len(records)}")
        
        if 'version' in data:
            print(f"✅ Version: {data['version']}")
        
        if 'statistics' in data:
            stats = data['statistics']
            print(f"✅ Statistics: Win Rate={stats.get('win_rate', 'N/A')}, "
                  f"Avg Win={stats.get('avg_win_pct', 'N/A')}%, "
                  f"Avg Loss={stats.get('avg_loss_pct', 'N/A')}%")
        
        if len(records) > 0:
            # Sample first record
            sample = records[0]
            print(f"✅ Sample {record_type[:-1]} keys: {list(sample.keys())[:5]}...")
        
        if len(records) >= 100:
            print("✅ PASS: Learning Book OK (sufficient data)")
            return True
        else:
            print(f"⚠️  WARNING: Learning Book has < 100 {record_type} (found {len(records)})")
            return len(records) > 0  # Pass if there's at least some data
            
    except json.JSONDecodeError:
        print("❌ FAIL: Learning Book is corrupted (invalid JSON)")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error checking Learning Book: {e}")
        return False


def check_war_games_results() -> bool:
    """Verify War Games results."""
    print("\n" + "=" * 80)
    print("CHECKING: War Games Results (war_games_results.json)")
    print("=" * 80)
    
    results_path = PROJECT_ROOT / "data" / "war_games_results.json"
    
    if not results_path.exists():
        print("⚠️  WARNING: War Games results not found (may not have been run yet)")
        return True  # Not a failure - just hasn't been run
    
    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
        
        if 'results' not in data:
            print("❌ FAIL: Invalid War Games results format")
            return False
        
        results = data['results']
        print(f"✅ Total campaigns: {len(results)}")
        
        # Check for NVDA campaigns
        nvda_campaigns = [r for r in results if r.get('symbol') == 'NVDA']
        if nvda_campaigns:
            print(f"✅ NVDA campaigns: {len(nvda_campaigns)}")
            
            # Check for trades
            total_trades = sum(r.get('total_trades', 0) for r in nvda_campaigns)
            print(f"✅ NVDA total trades: {total_trades}")
            
            if total_trades > 0:
                print("✅ PASS: War Games results OK (NVDA found with trades)")
                return True
            else:
                print("⚠️  WARNING: NVDA campaigns exist but 0 trades executed")
                return False
        else:
            print("⚠️  WARNING: No NVDA campaigns found in results")
            return False
            
    except json.JSONDecodeError:
        print("❌ FAIL: War Games results corrupted (invalid JSON)")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error checking War Games results: {e}")
        return False


def check_configuration() -> bool:
    """Verify system configuration."""
    print("\n" + "=" * 80)
    print("CHECKING: System Configuration")
    print("=" * 80)
    
    # Check critical files exist
    critical_files = [
        "requirements.txt",
        "main.py",
        "engine/orchestrator.py",
        "daemon/simulator/war_games_runner.py",
        "services/news_fetcher.py",
        "execution/ibkr.py",
    ]
    
    all_exist = True
    for file_path in critical_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            all_exist = False
    
    if all_exist:
        print("✅ PASS: All critical files present")
        return True
    else:
        print("❌ FAIL: Some critical files missing")
        return False


def check_file_status_updates() -> bool:
    """Check for file-based status update mechanisms."""
    print("\n" + "=" * 80)
    print("CHECKING: File-Based Status Updates")
    print("=" * 80)
    
    # Check for status files that might be used for inter-process communication
    status_files = [
        "data/system_status.json",
        "data/ibkr_status.json",
        "data/connection_status.json",
        "data/daemon_status.json",
    ]
    
    found_any = False
    for status_file in status_files:
        full_path = PROJECT_ROOT / status_file
        if full_path.exists():
            print(f"✅ Found: {status_file}")
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    print(f"   Status: {data}")
                found_any = True
            except Exception as e:
                print(f"   ⚠️  Could not read: {e}")
        else:
            print(f"ℹ️  Not found: {status_file}")
    
    if not found_any:
        print("ℹ️  No file-based status updates detected (using in-memory state)")
    
    return True  # Not a failure condition


def run_verification():
    """Run all verification checks."""
    print("\n" + "=" * 80)
    print("FUGGERBOT SYSTEM VERIFICATION")
    print("=" * 80)
    
    checks = [
        ("Data Lake", check_data_lake),
        ("Learning Book", check_learning_book),
        ("War Games Results", check_war_games_results),
        ("Configuration", check_configuration),
        ("File Status Updates", check_file_status_updates),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Check '{name}' crashed: {e}", exc_info=True)
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_checks = len(results)
    
    print(f"\nResult: {total_passed}/{total_checks} checks passed")
    
    if total_passed == total_checks:
        print("\n🎉 System verification PASSED - all components healthy!")
    else:
        print("\n⚠️  System verification INCOMPLETE - some components need attention")
    
    return total_passed == total_checks


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
