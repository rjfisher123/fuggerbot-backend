import logging
import time
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from config.settings import get_settings
from models.tsfm.inference import ChronosInferenceEngine
from models.tsfm.schemas import ForecastInput
from models.trust.filter import TrustFilter
from reasoning.engine import DeepSeekEngine
from reasoning.memory import TradeMemory
from reasoning.schemas import TradeContext, ReasoningDecision, DeepSeekResponse
from execution.ibkr import IBKRBridge
from context.tracker import RegimeTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("engine.orchestrator")


class TradeDecision:
    """Result of trade decision process (for backward compatibility)."""
    def __init__(
        self,
        symbol: str,
        decision: str,
        stage: str,
        reason: str,
        forecast_output=None,
        trust_evaluation=None,
        llm_response=None,
        execution_order=None,
        **kwargs
    ):
        self.symbol = symbol
        self.decision = decision
        self.stage = stage
        self.reason = reason
        self.forecast_output = forecast_output
        self.trust_evaluation = trust_evaluation
        self.llm_response = llm_response
        self.execution_order = execution_order
        # Allow additional attributes via kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class ExecutionOrder:
    """Structured execution order (for backward compatibility)."""
    def __init__(self, symbol: str, action: str, quantity: float, **kwargs):
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        for key, value in kwargs.items():
            setattr(self, key, value)


class TradeOrchestrator:
    def __init__(self, env: str = "prod"):
        self.settings = get_settings()
        self.env = env
        
        # Initialize Components
        self.tsfm = ChronosInferenceEngine(model_name="amazon/chronos-t5-tiny") 
        self.trust_filter = TrustFilter()
        self.reasoning_engine = DeepSeekEngine(
            api_key=self.settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=self.settings.deepseek_model
        )
        self.memory = TradeMemory()
        
        # Initialize Regime Tracker for Macro Context
        self.regime_tracker = RegimeTracker()
        
        # Initialize Execution Bridge
        # We default to Paper Trading port (7497). Change to 7496 for Live.
        try:
            self.broker = IBKRBridge(port=7497)
            self.broker.connect()
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}. Execution will be disabled.")
            self.broker = None
        
        # Load Learning Book (History Miner)
        self.learning_book = self._load_learning_book()
        
        logger.info(f"TradeOrchestrator initialized (env: {self.env})")

    def _load_learning_book(self) -> List[dict]:
        path = "data/learning_book.json"
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    book = json.load(f)
                # Handle both formats: list of records or dict with 'records' key
                if isinstance(book, dict) and 'records' in book:
                    records = book['records']
                elif isinstance(book, list):
                    records = book
                else:
                    records = []
                logger.info(f"📘 Loaded Learning Book with {len(records)} historical precedents.")
                return records
            except Exception as e:
                logger.error(f"Failed to load Learning Book: {e}")
                return []
        else:
            logger.warning("No Learning Book found. Run 'python research/miner.py' to generate history.")
            return []

    def find_precedents(self, symbol: str, current_volatility: float, current_trust: float) -> str:
        """
        Retrieves similar historical setups from the Learning Book.
        """
        if not self.learning_book:
            return "No historical data available."

        matches = [x for x in self.learning_book if x.get('symbol') == symbol]
        if len(matches) < 5:
            matches = self.learning_book
        
        current_vol_state = "HIGH" if current_volatility > 0.03 else ("LOW" if current_volatility < 0.01 else "NORMAL")
        matches = [x for x in matches if x.get('volatility_state') == current_vol_state]
        matches = [x for x in matches if abs(x.get('trust_score', 0) - current_trust) < 0.15]
        
        if not matches:
            return f"No direct historical precedents found for {current_vol_state} volatility regime."

        wins = [x for x in matches if x.get('actual_outcome') == 'Win' or x.get('outcome') == 'WIN']
        win_rate = len(wins) / len(matches) if matches else 0
        avg_return = np.mean([x.get('pnl_pct', 0) for x in matches]) if matches else 0
        
        return (
            f"HISTORICAL PRECEDENT ({len(matches)} cases found):\n"
            f"- Market Regime: {current_vol_state} Volatility\n"
            f"- Similar Trust Score Range: {current_trust:.2f} +/- 0.15\n"
            f"- Win Rate in this regime: {win_rate:.1%}\n"
            f"- Avg Return: {avg_return:.2%}\n"
            f"Insight: This setup has historically {'performed well' if win_rate > 0.55 else 'underperformed'}."
        )

    def fetch_data(self, symbol: str) -> pd.DataFrame:
        logger.info(f"📊 Fetching data for {symbol} via yfinance...")
        try:
            # Use Ticker().history() instead of download() to avoid progress argument issues
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="60d", interval="90m")
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
            
            df = df.dropna()
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if 'Close' not in df.columns:
                if 'Adj Close' in df.columns:
                    df['Close'] = df['Adj Close']
                else:
                    return pd.DataFrame()
            
            logger.info(f"✅ Fetched {len(df)} data points for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Data fetch error for {symbol}: {e}")
            return pd.DataFrame()

    def process_ticker(self, symbol: str, red_team_mode: bool = False) -> Optional[dict]:
        logger.info("="*60)
        logger.info(f"🚀 PROCESSING TICKER: {symbol}")
        logger.info("="*60)
        
        start_time = time.time()
        
        # --- STAGE 0: DATA ---
        df = self.fetch_data(symbol)
        if df.empty or len(df) < 50:
            return None
        current_price = float(df['Close'].iloc[-1])
        
        returns = df['Close'].pct_change().dropna()
        current_vol = float(returns.std() * np.sqrt(24))

        # --- STAGE 1: FORECAST ---
        logger.info(f"[STAGE 1] 🔮 Generating forecast for {symbol}...")
        try:
            series = [x for x in df['Close'].tolist() if not (isinstance(x, float) and (np.isnan(x) or np.isinf(x)))]
            
            # Create ForecastInput
            forecast_input = ForecastInput(
                series=series,
                forecast_horizon=30,
                context_length=None,
                metadata={"symbol": symbol}
            )
            
            # Generate forecast
            forecast_output = self.tsfm.forecast(forecast_input, num_samples=10)
            
            # Get target price (mean of point forecast)
            target_price = float(np.mean(forecast_output.point_forecast))
            logger.info(f"✅ [STAGE 1] Target=${target_price:.2f}")
        except Exception as e:
            logger.error(f"❌ [STAGE 1] Forecast failed: {e}")
            return None

        # --- STAGE 2: TRUST FILTER ---
        logger.info(f"[STAGE 2] 🛡️ Evaluating trust...")
        try:
            historical_vol = float(returns.std() * np.sqrt(24)) if len(returns) > 0 else current_vol
            
            trust_result = self.trust_filter.evaluate(
                forecast=forecast_output,
                input_data=forecast_input,
                symbol=symbol,
                current_volatility=current_vol,
                historical_volatility=historical_vol
            )
            
            if not trust_result.is_trusted:
                logger.info(f"🔴 [STAGE 2] REJECTED by Trust Filter ({trust_result.metrics.overall_trust_score:.3f})")
                return None
            
            logger.info(f"✅ [STAGE 2] Trust Score: {trust_result.metrics.overall_trust_score:.3f}")
        except Exception as e:
            logger.error(f"❌ [STAGE 2] Trust evaluation failed: {e}")
            return None

        # --- STAGE 3: DEEPSEEK REASONING ---
        logger.info(f"[STAGE 3] 🤖 Calling LLM...")
        
        # 1. Get Current Macro Regime
        regime = self.regime_tracker.get_current_regime()
        logger.info(f"🌍 Market Regime: {regime.id} ({regime.name})")
        
        # 2. Fetch Precedents
        precedent_summary = self.find_precedents(symbol, current_vol, trust_result.metrics.overall_trust_score)
        
        # 3. Build Context with Macro Regime
        memory_str = self.memory.get_summary(symbol)
        
        # Format market behavior list as bullet points
        behavior_text = "\n".join([f"- {behavior}" for behavior in regime.market_behavior]) if regime.market_behavior else "No specific behaviors documented."
        
        macro_context = (
            f"MACRO CONTEXT ({regime.name}):\n"
            f"{regime.description}\n\n"
            f"Key Behaviors:\n{behavior_text}\n\n"
            f"Guidance: {regime.embedding_hint}"
        )
        
        full_memory_context = f"{memory_str}\n\n{precedent_summary}\n\n{macro_context}"
        
        # Calculate forecast confidence from forecast output
        forecast_confidence = 1.0 - (
            np.mean(np.array(forecast_output.upper_bound) - np.array(forecast_output.lower_bound))
            / target_price
        ) if target_price > 0 else 0.85
        forecast_confidence = max(0.0, min(1.0, forecast_confidence))
        
        context = TradeContext(
            symbol=symbol,
            price=current_price,
            forecast_target=target_price,
            forecast_confidence=forecast_confidence, 
            trust_score=trust_result.metrics.overall_trust_score,
            volatility_metrics={"volatility": current_vol},
            memory_summary=full_memory_context 
        )
        
        # 3. Call LLM
        try:
            llm_decision = self.reasoning_engine.analyze_trade(context, red_team_mode=red_team_mode)
        except Exception as e:
            logger.error(f"❌ [STAGE 3] LLM reasoning failed: {e}")
            return None
        
        if not llm_decision:
            logger.error("❌ [STAGE 3] LLM returned None")
            return None

        logger.info(f"✅ [STAGE 3] Decision: {llm_decision.decision.value} (Conf: {llm_decision.confidence:.2f})")

        # --- EXECUTION ---
        trade_id = self.memory.add_trade(
            context=context,
            response=llm_decision
        )

        if llm_decision.decision == ReasoningDecision.APPROVE:
            processing_time = time.time() - start_time
            
            # Determine Size
            quantity = 0.0001 if "-USD" in symbol else 1
            
            logger.info(f"🟢 [EXECUTION] APPROVED! Sending BUY for {quantity} {symbol}...")
            
            if self.broker and self.broker.is_connected():
                order = self.broker.execute_trade("BUY", symbol, quantity)
                if order:
                    logger.info(f"🚀 Order Placed: Order ID {order.orderId}")
                else:
                    logger.error("❌ Order Placement Failed")
            else:
                logger.warning("⚠️ Broker not connected. Trade skipped.")
            
            # Return TradeDecision for backward compatibility
            return TradeDecision(
                symbol=symbol,
                decision="APPROVE",
                stage="execution",
                reason=f"LLM approved with confidence {llm_decision.confidence:.2f}",
                forecast_output=forecast_output,
                trust_evaluation=trust_result,
                llm_response=llm_decision,
                execution_order={"action": "BUY", "symbol": symbol, "price": current_price, "quantity": quantity}
            )
        else:
            logger.info(f"⚠️ [EXECUTION] REJECTED by LLM. Logged to memory.")
            # Return TradeDecision even when rejected (for backward compatibility)
            return TradeDecision(
                symbol=symbol,
                decision=llm_decision.decision.value,
                stage="execution",
                reason=f"LLM {llm_decision.decision.value}: {llm_decision.rationale[:100]}",
                forecast_output=forecast_output,
                trust_evaluation=trust_result,
                llm_response=llm_decision
            )

    def shutdown(self):
        if self.broker:
            self.broker.disconnect()
            logger.info("Broker disconnected.")
