# 🛠️ FuggerBot Repair Mission: "Operation Clean Slate"

## 1. Situation Analysis
The system is theoretically feature-complete (v2.0), but functionally broken in two ways:
1.  **The "Ghost" Data:** The War Games dashboard shows 0 trades and 0% return for BTC campaigns.
    * *Root Cause:* The `learning_book.json` is likely empty/corrupt, causing the Simulator's proxy logic to reject every trade.
2.  **Missing Assets:** The user cannot select "NVDA" in the War Games dropdown.
    * *Root Cause:* `war_games_runner.py` is likely not iterating through the new `STOCKS` asset class defined in the Data Lake.

---

## 2. Objective
We need to perform a **Deep Clean and Rebuild** of the data pipeline.

**Target State:**
- `data/ingest_global.py` successfully fetches NVDA.
- `research/miner.py` successfully builds a valid `learning_book.json` ( > 100 records).
- `daemon/simulator/war_games_runner.py` runs for BOTH BTC and NVDA, with proper risk management (no -90% losses).

---

## 3. Implementation Tasks (Cursor Instructions)

### Task A: Patch the Simulator (`daemon/simulator/war_games_runner.py`)
1.  **Asset Scope:** Modify `run_all_scenarios()` to explicitly include `NVDA` and `ETH-USD` in the target list.
    ```python
    assets_to_test = ['BTC-USD', 'ETH-USD', 'NVDA', 'MSFT']
    ```
2.  **Risk Management (Critical):** Implement Volatility-Adjusted Sizing to prevent the -90% ruin seen previously.
    -   `target_risk = account_equity * 0.02` (Risk 2% per trade).
    -   `position_size = target_risk / (entry * 0.05)` (Assume 5% stop loss distance).
    -   **Cap:** `max_position_size = 0.2` (Never bet >20% of account).

### Task B: Patch the Miner (`research/miner.py`)
1.  Ensure it uses `yf.Ticker(symbol).history()` (Safe Mode) to avoid the `progress` bug.
2.  Add a fallback: If `learning_book.json` is empty, the Simulator should use a **Default Proxy** (e.g., "If Trust > 0.9, Take Trade") rather than doing nothing. *This prevents the "0 Trades" bug if mining fails.*

### Task C: Verification Script (`scripts/verify_system.py`)
Create a new script that prints the health status:
- "Checking Data Lake... OK (300k rows)"
- "Checking Learning Book... OK (150 records)"
- "Checking War Games Results... OK (NVDA Found)"

---

## 4. Execution Sequence for the User

After you (Cursor) complete the code edits, instruct the user to run this **exact sequence** to reboot the brain:

1.  `python data/ingest_global.py` (Ensure NVDA data exists)
2.  `python research/miner.py` (Rebuild the Brain)
3.  `python daemon/simulator/war_games_runner.py` (Run the Simulation)
4.  `streamlit run tools/dashboard.py` (Verify Fix)

