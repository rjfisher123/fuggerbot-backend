#!/usr/bin/env python3
"""
FuggerBot Trading Bot - Main execution script.

Runs the complete trade decision pipeline for target assets.
"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine import TradeOrchestrator
from config import get_settings
from core.logger import logger

# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Target assets to process
TARGET_ASSETS = ['BTC-USD', 'ETH-USD', 'NVDA']


def print_summary(decision, elapsed_time: float = 0.0):
    """
    Print rich CLI summary of trade decision.
    
    Args:
        decision: TradeDecision object
        elapsed_time: Time taken to process (seconds)
    """
    if not decision:
        print("❌ ERROR: No decision returned")
        return
    
    symbol = decision.symbol
    decision_type = decision.decision.upper()
    stage = decision.stage
    
    # Color coding and emojis
    if decision_type == "APPROVE":
        emoji = "🟢"
        status = "APPROVED"
        color_code = "\033[92m"  # Green
    elif decision_type == "REJECT":
        emoji = "🔴"
        status = "REJECTED"
        color_code = "\033[91m"  # Red
    elif decision_type == "WAIT":
        emoji = "🟡"
        status = "WAIT"
        color_code = "\033[93m"  # Yellow
    else:
        emoji = "⚪"
        status = decision_type
        color_code = "\033[0m"  # Reset
    
    reset_code = "\033[0m"
    
    # Stage-specific messages
    stage_messages = {
        "data": f"Rejected: {decision.reason}",
        "forecast": f"Rejected: Forecast generation failed",
        "trust": f"Rejected by Trust Filter (score: {decision.trust_evaluation.metrics.overall_trust_score:.3f})" if decision.trust_evaluation else f"Rejected: {decision.reason}",
        "reasoning": f"Rejected by LLM Reasoning",
        "execution": f"Rejected: {decision.reason}" if decision_type != "APPROVE" else f"APPROVED by DeepSeek"
    }
    
    message = stage_messages.get(stage, decision.reason)
    
    # Print summary
    print(f"{emoji} {color_code}{symbol}: {status}{reset_code} - {message}")
    
    # Additional details for approved trades
    if decision_type == "APPROVE" and decision.execution_order:
        order = decision.execution_order
        # Handle both dict and object formats
        if isinstance(order, dict):
            action = order.get("action", "BUY")
            quantity = order.get("quantity", 0)
            symbol = order.get("symbol", decision.symbol)
            confidence = order.get("confidence", decision.llm_response.confidence if decision.llm_response else 0.0)
            rationale = order.get("rationale", decision.llm_response.rationale if decision.llm_response else "")
        else:
            action = order.action
            quantity = order.quantity
            symbol = order.symbol
            confidence = getattr(order, "confidence", decision.llm_response.confidence if decision.llm_response else 0.0)
            rationale = getattr(order, "rationale", decision.llm_response.rationale if decision.llm_response else "")
        
        print(f"   📋 Order: {action} {quantity} {symbol}")
        print(f"   💰 Confidence: {confidence:.2%}")
        if rationale:
            print(f"   💭 Rationale: {rationale[:100]}...")
    
    # Show stage breakdown
    if decision.forecast_output:
        forecast = decision.forecast_output
        target = sum(forecast.point_forecast) / len(forecast.point_forecast)
        print(f"   📊 Forecast Target: ${target:.2f}")
    
    if decision.trust_evaluation:
        trust = decision.trust_evaluation.metrics.overall_trust_score
        print(f"   🛡️  Trust Score: {trust:.3f}")
    
    if decision.llm_response:
        llm_conf = decision.llm_response.confidence
        print(f"   🤖 LLM Confidence: {llm_conf:.2%}")
    
    if elapsed_time > 0:
        print(f"   ⏱️  Processing Time: {elapsed_time:.2f}s")
    
    print()  # Blank line for readability


def run_once():
    """Run the bot once through all target assets."""
    print("=" * 60)
    print("🚀 FUGGERBOT TRADING BOT - Single Run")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target Assets: {', '.join(TARGET_ASSETS)}")
    print()
    
    try:
        settings = get_settings()
        print(f"⚙️  Environment: {settings.env_state.upper()}")
        print(f"🤖 Model: {settings.deepseek_model}")
        print()
    except Exception as e:
        logger.warning(f"Could not load settings: {e}")
    
    # Initialize orchestrator
    orchestrator = None
    try:
        orchestrator = TradeOrchestrator(env="dev")
        print("✅ TradeOrchestrator initialized")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize TradeOrchestrator: {e}")
        logger.error(f"Orchestrator initialization failed: {e}", exc_info=True)
        return
    
    # Process each asset with graceful shutdown
    results = []
    try:
        for asset in TARGET_ASSETS:
            print(f"🔄 Processing {asset}...")
            start_time = time.time()
            
            try:
                decision = orchestrator.process_ticker(asset, red_team_mode=False)
                elapsed = time.time() - start_time
                print_summary(decision, elapsed_time=elapsed)
                results.append((asset, decision))
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ {asset}: ERROR - {str(e)}")
                print(f"   ⏱️  Processing Time: {elapsed:.2f}s")
                print()
                logger.error(f"Error processing {asset}: {e}", exc_info=True)
                results.append((asset, None))
        
        # Final summary
        print("=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        
        approved = [r for r in results if r[1] and r[1].decision == "APPROVE"]
        rejected = [r for r in results if r[1] and r[1].decision == "REJECT"]
        errors = [r for r in results if r[1] is None]
        
        print(f"✅ Approved: {len(approved)}")
        print(f"❌ Rejected: {len(rejected)}")
        if errors:
            print(f"⚠️  Errors: {len(errors)}")
        
        if approved:
            print("\n🟢 APPROVED TRADES:")
            for asset, decision in approved:
                if decision.execution_order:
                    order = decision.execution_order
                    print(f"   • {asset}: {order.action} {order.quantity} shares")
        
        print(f"\n📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    finally:
        # Graceful shutdown: disconnect from IBKR
        if orchestrator is not None:
            try:
                orchestrator.shutdown()
                logger.info("Broker disconnected.")
                print("✅ Broker disconnected.")
            except Exception as e:
                logger.warning(f"Error during shutdown: {e}")
                print(f"⚠️  Warning: Error during shutdown: {e}")


def run_continuous(interval_seconds: int = 300):
    """
    Run the bot in a continuous loop.
    
    Args:
        interval_seconds: Time to wait between runs (default: 5 minutes)
    """
    print("=" * 60)
    print("🚀 FUGGERBOT TRADING BOT - Continuous Mode")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target Assets: {', '.join(TARGET_ASSETS)}")
    print(f"⏰ Interval: {interval_seconds}s ({interval_seconds/60:.1f} minutes)")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        settings = get_settings()
        print(f"⚙️  Environment: {settings.env_state.upper()}")
        print()
    except Exception as e:
        logger.warning(f"Could not load settings: {e}")
    
    # Initialize orchestrator
    orchestrator = None
    try:
        orchestrator = TradeOrchestrator(env="dev")
        print("✅ TradeOrchestrator initialized")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize TradeOrchestrator: {e}")
        logger.error(f"Orchestrator initialization failed: {e}", exc_info=True)
        return
    
    run_count = 0
    
    try:
        while True:
            run_count += 1
            print("=" * 60)
            print(f"🔄 RUN #{run_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            print()
            
            # Process each asset
            for asset in TARGET_ASSETS:
                print(f"🔄 Processing {asset}...")
                start_time = time.time()
                
                try:
                    decision = orchestrator.process_ticker(asset, red_team_mode=False)
                    elapsed = time.time() - start_time
                    print_summary(decision, elapsed_time=elapsed)
                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"❌ {asset}: ERROR - {str(e)}")
                    print(f"   ⏱️  Processing Time: {elapsed:.2f}s")
                    print()
                    logger.error(f"Error processing {asset}: {e}", exc_info=True)
            
            # Update outcomes for recent trades (every run)
            try:
                from tools.update_outcomes import update_trade_outcomes
                updated = update_trade_outcomes(orchestrator.memory, lookback_hours=24)
                if updated > 0:
                    print(f"📊 Updated {updated} trade outcomes")
            except Exception as e:
                logger.debug(f"Could not update outcomes: {e}")
            
            # Wait before next run
            print(f"⏸️  Waiting {interval_seconds}s before next run...")
            print()
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("🛑 STOPPED BY USER")
        print("=" * 60)
        print(f"📊 Total Runs: {run_count}")
        print(f"📅 Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    finally:
        # Graceful shutdown: disconnect from IBKR
        if orchestrator is not None:
            try:
                orchestrator.shutdown()
                logger.info("Broker disconnected.")
                print("✅ Broker disconnected.")
            except Exception as e:
                logger.warning(f"Error during shutdown: {e}")
                print(f"⚠️  Warning: Error during shutdown: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FuggerBot Trading Bot")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run in continuous loop mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between runs in seconds (default: 300 = 5 minutes)"
    )
    
    args = parser.parse_args()
    
    if args.continuous:
        run_continuous(interval_seconds=args.interval)
    else:
        run_once()

