"""
Strategy Optimizer Agent for FuggerBot v2.3.

Automatically selects optimal trading parameters by analyzing War Games results.
Groups campaigns by Symbol + Market Regime, scores each using risk-adjusted metrics,
and outputs the best parameter set for each combination.

This removes human guesswork from parameter tuning.

Author: FuggerBot AI Team
Version: Phase 4 - Automated Parameter Optimization
"""
import json
import os
import pandas as pd
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from pathlib import Path

logger = logging.getLogger("StrategyOptimizer")

INPUT_FILE = "data/war_games_results.json"
OUTPUT_FILE = "data/optimized_params.json"


class OptimizationResult(BaseModel):
    """Result of strategy optimization for a specific Symbol+Regime combination."""
    symbol: str
    regime: str
    best_strategy_name: str
    best_params: Dict[str, float]
    metrics: Dict[str, float]
    score: float


class StrategyOptimizerAgent:
    """
    Analyzes War Games simulation results and selects optimal parameters.
    
    Scoring Formula:
        Score = (Sharpe × 10) + (WinRate × 50) - (MaxDD × 2) + (Return × 0.5)
        
    Prioritizes:
        1. Risk-adjusted returns (Sharpe)
        2. Consistency (Win Rate)
        3. Capital preservation (low drawdown)
        4. Absolute returns (secondary)
    """
    
    def __init__(self, input_file: str = INPUT_FILE, output_file: str = OUTPUT_FILE):
        """
        Initialize the Strategy Optimizer Agent.
        
        Args:
            input_file: Path to war_games_results.json
            output_file: Path to save optimized_params.json
        """
        self.input_file = input_file
        self.output_file = output_file
        self.results = []

    def load_results(self):
        """Load War Games simulation results."""
        if not os.path.exists(self.input_file):
            logger.warning(f"No simulation results found at {self.input_file}")
            return
        
        with open(self.input_file, 'r') as f:
            data = json.load(f)
            # Handle the structure returned by WarGamesRunner (dict with 'results' key)
            if isinstance(data, dict) and 'results' in data:
                self.results = data['results']
            else:
                self.results = data  # Fallback for flat list
        
        logger.info(f"📊 Loaded {len(self.results)} campaign results")

    def score_campaign(self, campaign: dict) -> float:
        """
        Calculate optimization score for a campaign.
        
        Scoring Formula:
            Score = (Sharpe × 10) + (WinRate × 50) - (MaxDD × 2) + (Return × 0.5)
            
        Disqualification Rules:
            - Drawdown > 25%: Score = -999
            - Negative return: Score = -100
            - Zero trades: Score = -500
            
        Args:
            campaign: Campaign result dictionary
            
        Returns:
            Optimization score (higher is better)
        """
        sharpe = campaign.get('sharpe_ratio', 0) or 0
        win_rate = campaign.get('win_rate', 0)
        drawdown = abs(campaign.get('max_drawdown_pct', 0))
        return_pct = campaign.get('total_return_pct', 0)
        total_trades = campaign.get('total_trades', 0)

        # Disqualify catastrophic failures
        if total_trades == 0:
            return -500.0  # No trades = no data
        
        if drawdown > 25.0:
            return -999.0  # Too risky
        
        if return_pct < 0:
            return -100.0  # Prefer flat over loss (for now)

        # Weighted Score (prioritize consistency and risk-adjusted returns)
        score = (
            sharpe * 10.0 +          # Sharpe ratio (risk-adjusted return)
            win_rate * 50.0 +        # Consistency
            - drawdown * 2.0 +       # Penalty for drawdown
            return_pct * 0.5         # Absolute return (lower weight)
        )
        
        return score

    def optimize(self) -> List[OptimizationResult]:
        """
        Analyze all campaigns and select best parameters for each Symbol+Regime.
        
        Returns:
            List of OptimizationResult objects
        """
        logger.info("🧠 Running Strategy Optimization...")
        self.load_results()
        
        if not self.results:
            logger.error("No results to optimize!")
            return []

        df = pd.DataFrame(self.results)
        
        # Add optimization score
        df['opt_score'] = df.apply(self.score_campaign, axis=1)
        
        # Group by Symbol + Scenario (Market Regime)
        group_cols = ['symbol', 'scenario_description']
        
        optimized = []
        
        for (symbol, regime), group in df.groupby(group_cols):
            # Find best campaign in this group
            best_run = group.loc[group['opt_score'].idxmax()]
            
            # Extract parameters
            params = best_run.get('params', {})
            
            result = OptimizationResult(
                symbol=symbol,
                regime=regime,
                best_strategy_name=best_run.get('campaign_name', 'Unknown'),
                best_params=params,
                metrics={
                    "sharpe": float(best_run.get('sharpe_ratio', 0) or 0),
                    "return": float(best_run.get('total_return_pct', 0)),
                    "drawdown": float(best_run.get('max_drawdown_pct', 0)),
                    "win_rate": float(best_run.get('win_rate', 0)),
                    "total_trades": int(best_run.get('total_trades', 0))
                },
                score=float(best_run['opt_score'])
            )
            
            optimized.append(result)
            
            logger.info(
                f"🏆 Best for {symbol} in '{regime[:30]}': "
                f"{result.best_strategy_name} (Score: {result.score:.1f})"
            )

        # Save results
        self.save_optimized_params(optimized)
        
        return optimized

    def save_optimized_params(self, results: List[OptimizationResult]):
        """
        Save optimized parameters to JSON file.
        
        Args:
            results: List of OptimizationResult objects
        """
        output = [r.model_dump() for r in results]  # Pydantic V2
        
        # Save flat list for easy loading
        with open(self.output_file, 'w') as f:
            json.dump(output, f, indent=2)
            
        logger.info(f"💾 Saved {len(output)} optimized configurations to {self.output_file}")
        
        # Also save a summary report
        summary_file = self.output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("STRATEGY OPTIMIZATION SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            for result in results:
                f.write(f"Symbol: {result.symbol}\n")
                f.write(f"Regime: {result.regime}\n")
                f.write(f"Best Strategy: {result.best_strategy_name}\n")
                f.write(f"Score: {result.score:.2f}\n")
                f.write(f"Metrics:\n")
                f.write(f"  - Return: {result.metrics['return']:+.1f}%\n")
                f.write(f"  - Sharpe: {result.metrics['sharpe']:.2f}\n")
                f.write(f"  - Win Rate: {result.metrics['win_rate']:.1%}\n")
                f.write(f"  - Max DD: {result.metrics['drawdown']:.1f}%\n")
                f.write(f"  - Trades: {result.metrics['total_trades']}\n")
                f.write(f"Parameters:\n")
                for key, value in result.best_params.items():
                    f.write(f"  - {key}: {value}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        
        logger.info(f"📄 Summary saved to {summary_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    optimizer = StrategyOptimizerAgent()
    results = optimizer.optimize()
    
    print(f"\n✅ Optimization complete! {len(results)} configurations saved.")
    print(f"📁 Output: {OUTPUT_FILE}")
    print(f"\nTop 3 Optimized Strategies:")
    
    # Sort by score and show top 3
    sorted_results = sorted(results, key=lambda x: x.score, reverse=True)[:3]
    
    for i, result in enumerate(sorted_results, 1):
        print(f"\n{i}. {result.symbol} - {result.regime[:40]}")
        print(f"   Strategy: {result.best_strategy_name}")
        print(f"   Score: {result.score:.1f}")
        print(f"   Return: {result.metrics['return']:+.1f}%, DD: {result.metrics['drawdown']:.1f}%")

