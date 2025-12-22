"""
FuggerBot System Health Verification Script.

Checks the health of all critical components:
- Global Data Lake
- Learning Book
- War Games Results
- TRM Components

Author: FuggerBot AI Team
Status: Operation Clean Slate v2.0
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import json
from typing import Dict, Any, Tuple


class SystemHealthChecker:
    """Verifies FuggerBot system health."""
    
    def __init__(self):
        self.root = PROJECT_ROOT
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
    
    def check_data_lake(self) -> Tuple[bool, str]:
        """Check Global Data Lake health."""
        db_path = self.root / "data" / "market_history.duckdb"
        
        if not db_path.exists():
            return False, f"❌ Data Lake not found at {db_path}"
        
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
            
            # Check total rows
            total_rows = conn.execute("SELECT COUNT(*) FROM ohlcv_history").fetchone()[0]
            
            # Check symbols
            symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv_history").fetchone()[0]
            
            # Check asset classes
            asset_classes = conn.execute(
                "SELECT asset_class, COUNT(*) as cnt FROM ohlcv_history GROUP BY asset_class"
            ).fetchdf()
            
            conn.close()
            
            if total_rows < 100000:
                return False, f"⚠️  Data Lake has only {total_rows:,} rows (expected >100K)"
            
            if symbols < 30:
                self.warnings.append(f"⚠️  Only {symbols} symbols in Data Lake (expected >30)")
            
            # Check for required symbols
            conn = duckdb.connect(str(db_path), read_only=True)
            required_symbols = ['BTC-USD', 'NVDA', 'MSFT', '^GSPC']
            available = []
            
            for sym in required_symbols:
                count = conn.execute(
                    f"SELECT COUNT(*) FROM ohlcv_history WHERE symbol = '{sym}'"
                ).fetchone()[0]
                if count > 0:
                    available.append(sym)
            
            conn.close()
            
            if len(available) < len(required_symbols):
                missing = set(required_symbols) - set(available)
                self.warnings.append(f"⚠️  Missing symbols: {missing}")
            
            return True, f"✅ Data Lake OK: {total_rows:,} rows, {symbols} symbols, {len(asset_classes)} asset classes"
        
        except Exception as e:
            return False, f"❌ Data Lake error: {e}"
    
    def check_learning_book(self) -> Tuple[bool, str]:
        """Check Learning Book health."""
        book_path = self.root / "data" / "learning_book.json"
        
        if not book_path.exists():
            return False, f"⚠️  Learning Book not found (run: python research/miner.py)"
        
        try:
            with open(book_path, 'r') as f:
                book = json.load(f)
            
            patterns = book.get('patterns', [])
            
            if len(patterns) == 0:
                return False, "❌ Learning Book is empty (run: python research/miner.py)"
            
            if len(patterns) < 50:
                self.warnings.append(f"⚠️  Only {len(patterns)} patterns (expected >100)")
            
            symbols_covered = book.get('symbols_covered', [])
            
            return True, f"✅ Learning Book OK: {len(patterns)} patterns, {len(symbols_covered)} symbols"
        
        except Exception as e:
            return False, f"❌ Learning Book error: {e}"
    
    def check_war_games(self) -> Tuple[bool, str]:
        """Check War Games results."""
        results_path = self.root / "data" / "war_games_results.json"
        
        if not results_path.exists():
            return False, f"⚠️  War Games results not found (run: python daemon/simulator/war_games_runner.py)"
        
        try:
            with open(results_path, 'r') as f:
                results = json.load(f)
            
            campaigns = results.get('results', [])
            
            if len(campaigns) == 0:
                return False, "❌ No War Games campaigns found"
            
            # Check for NVDA campaigns
            nvda_campaigns = [c for c in campaigns if 'NVDA' in c.get('symbol', '')]
            
            if len(nvda_campaigns) == 0:
                self.warnings.append("⚠️  No NVDA campaigns found")
            
            # Check for ghost data (0 trades)
            zero_trade_campaigns = [c for c in campaigns if c.get('total_trades', 0) == 0]
            
            if len(zero_trade_campaigns) > 0:
                self.warnings.append(
                    f"⚠️  {len(zero_trade_campaigns)} campaigns with 0 trades (check proxy logic)"
                )
            
            return True, f"✅ War Games OK: {len(campaigns)} campaigns, {len(nvda_campaigns)} NVDA campaigns"
        
        except Exception as e:
            return False, f"❌ War Games error: {e}"
    
    def check_trade_memory(self) -> Tuple[bool, str]:
        """Check Trade Memory health."""
        memory_path = self.root / "data" / "trade_memory.json"
        
        if not memory_path.exists():
            return True, "ℹ️  Trade Memory not found (not yet used in live trading)"
        
        try:
            with open(memory_path, 'r') as f:
                memory = json.load(f)
            
            trades = memory.get('trades', [])
            
            return True, f"✅ Trade Memory OK: {len(trades)} historical trades"
        
        except Exception as e:
            return False, f"❌ Trade Memory error: {e}"
    
    def check_trm_agents(self) -> Tuple[bool, str]:
        """Check TRM agent files."""
        agents_to_check = [
            'agents/trm/news_digest_agent.py',
            'agents/trm/memory_summarizer.py',
            'agents/trm/risk_policy_agent.py'
        ]
        
        missing = []
        for agent_file in agents_to_check:
            if not (self.root / agent_file).exists():
                missing.append(agent_file)
        
        if missing:
            return False, f"❌ Missing TRM agents: {missing}"
        
        return True, f"✅ TRM Agents OK: {len(agents_to_check)} agents found"
    
    def run_all_checks(self):
        """Run all health checks."""
        print("=" * 80)
        print("🔍 FUGGERBOT SYSTEM HEALTH CHECK - Operation Clean Slate v2.0")
        print("=" * 80)
        print()
        
        checks = [
            ("Data Lake", self.check_data_lake),
            ("Learning Book", self.check_learning_book),
            ("War Games Results", self.check_war_games),
            ("Trade Memory", self.check_trade_memory),
            ("TRM Agents", self.check_trm_agents)
        ]
        
        for check_name, check_func in checks:
            try:
                passed, message = check_func()
                
                if passed:
                    self.checks_passed += 1
                else:
                    self.checks_failed += 1
                
                print(f"  {message}")
            
            except Exception as e:
                self.checks_failed += 1
                print(f"  ❌ {check_name} error: {e}")
        
        print()
        
        # Print warnings
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        # Print summary
        print("=" * 80)
        print(f"📊 SUMMARY: {self.checks_passed} passed, {self.checks_failed} failed, {len(self.warnings)} warnings")
        print("=" * 80)
        
        if self.checks_failed == 0 and len(self.warnings) == 0:
            print("\n🎉 ALL SYSTEMS OPERATIONAL - FuggerBot v2.0 Ready!")
            return True
        elif self.checks_failed == 0:
            print("\n✅ Core systems operational (minor warnings present)")
            return True
        else:
            print("\n❌ CRITICAL ISSUES DETECTED - Review errors above")
            print("\n🔧 Recommended Actions:")
            print("  1. python data/ingest_global.py      # Rebuild Data Lake")
            print("  2. python research/miner.py          # Rebuild Learning Book")
            print("  3. python daemon/simulator/war_games_runner.py  # Run War Games")
            print("  4. python scripts/verify_system.py   # Re-run this check")
            return False


if __name__ == "__main__":
    checker = SystemHealthChecker()
    success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)






