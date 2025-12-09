import time
import random
import logging
import os
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Import your actual modules
# Ensure your python path is set correctly, or run this from the root repo dir
try:
    from reasoning.schemas import TradeContext, DeepSeekResponse, ReasoningDecision
    from reasoning.memory import TradeMemory
    from reasoning.engine import DeepSeekEngine
except ImportError:
    # Fallback for when running casually without full path setup
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from reasoning.schemas import TradeContext, DeepSeekResponse, ReasoningDecision
    from reasoning.memory import TradeMemory
    from reasoning.engine import DeepSeekEngine

# --- CONFIGURATION ---
USE_REAL_LLM = True  # Set to True to use your actual DeepSeek API via OpenRouter
NUM_SCENARIOS = 50  # Increased sample size for better stats

# Try to load settings for real LLM mode
try:
    from config import get_settings
    _settings = get_settings()
    API_KEY = _settings.openrouter_api_key
    MODEL_NAME = _settings.deepseek_model
except Exception:
    # Fallback if settings not available
    API_KEY = None
    MODEL_NAME = "deepseek/deepseek-r1"

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("EvalScript")


class MockLLM:
    """
    A distinct mock class to test the harness without API costs.
    It randomly approves/rejects based on Trust Score to simulate 'intelligence'.
    """
    
    def __init__(self):
        """Initialize mock LLM (no API key needed)."""
        pass

    def analyze_trade(self, context: TradeContext, red_team_mode: bool = False, memory=None):
        """
        Mock trade analysis that simulates intelligent decision-making.
        
        Args:
            context: TradeContext with trade information
            red_team_mode: If True, be more conservative
            memory: Optional memory (ignored in mock)
        
        Returns:
            DeepSeekResponse with mock decision
        """
        # Simulation Logic: High trust + Low Volatility = Higher chance of Approve
        base_prob = context.trust_score
        
        # Red Team mode makes the mock model much more conservative
        if red_team_mode:
            base_prob -= 0.3
        
        # Ensure probability is in valid range
        base_prob = max(0.1, min(0.9, base_prob))
        
        decision = ReasoningDecision.APPROVE if random.random() < base_prob else ReasoningDecision.REJECT
        
        return DeepSeekResponse(
            decision=decision,
            confidence=round(random.uniform(0.7, 0.99), 2),
            risk_analysis="Mock simulation of risk analysis.",
            rationale=f"Mock rationale. Trust score {context.trust_score} was factor."
        )


def generate_mock_scenario(index: int) -> TradeContext:
    """Generates synthetic market data."""
    symbols = ["BTC-USD", "ETH-USD", "NVDA", "TSLA", "MSFT", "XAU-USD"]
    symbol = random.choice(symbols)
    
    # Create a correlation: High trust score usually leads to a 'winning' setup in our mock ground truth
    trust = round(random.uniform(0.5, 0.95), 2)
    
    return TradeContext(
        symbol=symbol,
        price=random.uniform(100, 50000),
        forecast_target=random.uniform(105, 51000),
        forecast_confidence=round(random.uniform(0.6, 0.9), 2),
        trust_score=trust,
        volatility_metrics={"atr": 1.5, "z_score": round(random.uniform(-2, 2), 1)},
        memory_summary="[Mock Memory Summary: Win Rate 60%]"
    )


def determine_mock_outcome(context: TradeContext) -> float:
    """
    Simulates the 'Ground Truth' market result.
    In this mock, higher trust score = higher probability of positive PnL.
    """
    # The 'Truth' is correlated to the inputs, so a good model SHOULD find it.
    chance_of_win = context.trust_score
    
    # Add some randomness (market noise)
    roll = random.random()
    if roll < chance_of_win:
        return random.uniform(1.0, 5.0)  # Win
    else:
        return random.uniform(-1.0, -3.0)  # Loss


def run_evaluation():
    logger.info("--- STARTING WAR GAMES SIMULATION ---")
    
    # 1. Init Components
    # Use a temp memory file to not pollute production memory
    project_root = Path(__file__).parent.parent
    test_memory_path = project_root / "data" / "test_memory_wargames.json"
    
    if test_memory_path.exists():
        test_memory_path.unlink()
    
    memory = TradeMemory(memory_file=test_memory_path)

    if USE_REAL_LLM:
        if not API_KEY:
            raise ValueError(
                "USE_REAL_LLM is True but API key not found. "
                "Set OPENROUTER_API_KEY in your .env file or use config/settings.py"
            )
        engine = DeepSeekEngine(api_key=API_KEY, model_name=MODEL_NAME)
        logger.info(f"Using REAL DeepSeek Engine via OpenRouter (model: {MODEL_NAME}).")
    else:
        engine = MockLLM()
        logger.info("Using MOCK LLM Engine.")

    results = []

    # 2. Run Scenarios
    for i in range(NUM_SCENARIOS):
        # A. Create Setup
        ctx = generate_mock_scenario(i)
        
        # B. Get Decision from LLM
        # We toggle 'Red Team' mode every 10 trades to test adaptation
        red_team = (i % 10 == 0)
        
        # Inject real memory into context
        ctx.memory_summary = memory.get_summary(ctx.symbol)
        
        response = engine.analyze_trade(ctx, red_team_mode=red_team, memory=memory)
        
        if not response:
            logger.error(f"Scenario {i}: LLM Failed.")
            continue

        # C. Store in Memory (using the actual method signature)
        trade_id = memory.add_trade(
            context=ctx,
            response=response
        )
        
        # D. Simulate Market Time Passing (Instant in this script)
        # Determine if it WOULD have won or lost
        pnl = determine_mock_outcome(ctx)
        
        # E. Update Memory (Feedback Loop)
        memory.update_outcome(trade_id, pnl)
        
        # Log concise output
        mode_str = "🛑 RED" if red_team else "🟢 STD"
        result_icon = "💰" if pnl > 0 else "🔻"
        logger.info(
            f"#{i+1:02d} {mode_str} | {ctx.symbol} | Trust: {ctx.trust_score:.2f} | "
            f"LLM: {response.decision.value} -> {result_icon} {pnl:+.2f}"
        )
        
        results.append({
            "decision": response.decision,
            "pnl": pnl
        })
        
        # Small sleep to prevent rate limits if using real API
        if USE_REAL_LLM:
            time.sleep(1)

    # 3. Calculate Metrics
    logger.info("\n" + "="*40)
    logger.info("       EVALUATION REPORT       ")
    logger.info("="*40)
    
    total_trades = len(results)
    approved = [r for r in results if r['decision'] == ReasoningDecision.APPROVE]
    rejected = [r for r in results if r['decision'] == ReasoningDecision.REJECT]
    
    # --- METRIC 1: PRECISION (Hit Rate) ---
    # Precision = True Positives / (True Positives + False Positives)
    # i.e., When we said BUY, how often did we win?
    true_positives = len([r for r in approved if r['pnl'] > 0])
    false_positives = len([r for r in approved if r['pnl'] <= 0])
    precision = true_positives / len(approved) if approved else 0.0
    
    # --- METRIC 2: RECALL (Sensitivity) ---
    # Recall = True Positives / (True Positives + False Negatives)
    # i.e., Of all the winning trades available, how many did we catch?
    total_market_winners = len([r for r in results if r['pnl'] > 0])
    missed_opportunities = len([r for r in rejected if r['pnl'] > 0])  # False Negatives
    recall = true_positives / total_market_winners if total_market_winners > 0 else 0.0
    
    # --- METRIC 3: REGRET RATE ---
    # Regret = False Negatives / Total Rejections
    # i.e., How painful are our rejections?
    regret_rate = missed_opportunities / len(rejected) if rejected else 0.0
    
    # --- METRIC 4: PnL Delta ---
    system_pnl = sum([r['pnl'] for r in approved])
    blind_pnl = sum([r['pnl'] for r in results])
    
    print(f"Total Scenarios:    {total_trades}")
    print(f"Approvals:          {len(approved)}")
    print(f"Rejections:         {len(rejected)}")
    print(f"Market Winners:     {total_market_winners} (Potential Alpha)")
    print("-" * 30)
    print(f"🎯 Precision (Hit Rate):  {precision:.1%}  (Target: >60%)")
    print(f"📡 Recall (Capture Rate): {recall:.1%}     (Target: >40%)")
    print(f"🤦 Regret Rate:           {regret_rate:.1%} (Target: <30%)")
    print("-" * 30)
    print(f"💰 System PnL:  ${system_pnl:.2f}")
    print(f"🎲 Random PnL:  ${blind_pnl:.2f}")
    
    if system_pnl > blind_pnl:
        print("\n✅ SUCCESS: Reasoning Engine outperformed blind luck.")
    else:
        print("\n❌ FAILURE: Reasoning Engine underperformed. Adjust prompts.")


if __name__ == "__main__":
    # Create data dir if not exists
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    run_evaluation()

