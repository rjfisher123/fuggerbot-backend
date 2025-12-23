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
from config import AdaptiveParamLoader
from models.tsfm.inference import ChronosInferenceEngine
from models.tsfm.schemas import ForecastInput
from models.trust.filter import TrustFilter
from models.technical_analysis import add_indicators  # Phase 3: Quality filters
from reasoning.engine import DeepSeekEngine
from reasoning.memory import TradeMemory
from reasoning.schemas import TradeContext, ReasoningDecision, DeepSeekResponse
from execution.ibkr import IBKRBridge
from context.tracker import RegimeTracker

# Level 2 Perception Agents
from agents.trm.news_digest_agent import NewsDigestAgent, NewsDigest
from agents.trm.symbol_sentiment_agent import SymbolSentimentAgent
from agents.trm.memory_summarizer import MemorySummarizer, MemoryNarrative
from services.news_fetcher import NewsFetcher

# Level 4 Policy Agent
from agents.trm.risk_policy_agent import RiskPolicyAgent, TRMInput, FinalVerdict

# Task C: Portfolio Manager
from agents.portfolio_manager import PortfolioManager

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
        self.param_loader = AdaptiveParamLoader()
        
        # Initialize Regime Tracker for Macro Context
        self.regime_tracker = RegimeTracker()
        
        # Initialize Level 2 Perception Agents
        self.news_fetcher = NewsFetcher()
        self.news_digest = NewsDigestAgent()
        self.symbol_sentiment_agent = SymbolSentimentAgent()
        self.memory_summarizer = MemorySummarizer()
        
        # Initialize Level 4 Policy Agent
        self.risk_policy = RiskPolicyAgent()
        
        # Initialize Portfolio Manager (Task C)
        self.portfolio_manager = PortfolioManager()
        
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

        # Get current regime
        current_regime = self.regime_tracker.get_current_regime()
        
        # Load optimized parameters based on symbol and current regime
        params = self.param_loader.get_optimized_params(symbol, current_regime.name)
        trust_threshold = float(params.get("trust_threshold", 0.65))
        min_confidence = float(params.get("min_confidence", 0.75))
        max_position_size = float(params.get("max_position_size", 0.05))
        stop_loss = float(params.get("stop_loss", 0.05))
        take_profit = float(params.get("take_profit", 0.15))
        
        logger.info(
            f"📐 Using optimized params for {symbol} in '{current_regime.name}': "
            f"Trust>{trust_threshold:.2f}, Conf>{min_confidence:.2f}, "
            f"PosSize<{max_position_size:.0%}, SL={stop_loss:.0%}, TP={take_profit:.0%}"
        )
        
        # --- STAGE 0: DATA ---
        df = self.fetch_data(symbol)
        if df.empty or len(df) < 50:
            return None
        
        # Phase 3: Add technical indicators for quality filtering
        # Normalize column names to lowercase for add_indicators
        df.columns = df.columns.str.lower()
        df = add_indicators(df)
        
        current_price = float(df['close'].iloc[-1])
        
        # Phase 3: HARD QUALITY FILTERS (Fail Fast)
        latest = df.iloc[-1]
        
        # Filter 1: RSI Overbought Check
        if pd.notna(latest['rsi_14']) and latest['rsi_14'] > 70:
            logger.info(f"🔴 [STAGE 0] REJECTED: Overbought (RSI={latest['rsi_14']:.1f} > 70)")
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                stage="quality_filter",
                reason=f"RSI overbought: {latest['rsi_14']:.1f} > 70",
            )
        
        # Filter 2: MACD Momentum Check
        if pd.notna(latest['macd_hist']) and latest['macd_hist'] < 0:
            logger.info(f"🔴 [STAGE 0] REJECTED: Negative Momentum (MACD={latest['macd_hist']:.2f} < 0)")
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                stage="quality_filter",
                reason=f"MACD negative: {latest['macd_hist']:.2f} < 0",
            )
        
        # Log quality filter pass
        logger.info(
            f"✅ [STAGE 0] Quality Filters PASSED: "
            f"RSI={latest['rsi_14']:.1f}, MACD={latest['macd_hist']:.2f}, "
            f"Volume Ratio={latest['volume_ratio']:.2f}"
        )
        
        returns = df['close'].pct_change().dropna()
        current_vol = float(returns.std() * np.sqrt(24))

        # --- STAGE 1: FORECAST ---
        logger.info(f"[STAGE 1] 🔮 Generating forecast for {symbol}...")
        try:
            series = [x for x in df['close'].tolist() if not (isinstance(x, float) and (np.isnan(x) or np.isinf(x)))]
            
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
            
            trust_score = trust_result.metrics.overall_trust_score
            if not trust_result.is_trusted or trust_score < trust_threshold:
                logger.info(
                    f"🔴 [STAGE 2] REJECTED by Trust Filter "
                    f"(score={trust_score:.3f}, threshold={trust_threshold:.2f})"
                )
                return TradeDecision(
                    symbol=symbol,
                    decision="REJECT",
                    stage="trust",
                    reason=f"Trust score {trust_score:.3f} below threshold {trust_threshold:.2f}",
                    forecast_output=forecast_output,
                    trust_evaluation=trust_result,
                )
            
            logger.info(f"✅ [STAGE 2] Trust Score: {trust_score:.3f} (threshold {trust_threshold:.2f})")
        except Exception as e:
            logger.error(f"❌ [STAGE 2] Trust evaluation failed: {e}")
            return None

        # --- LEVEL 2: PERCEPTION ---
        logger.info(f"[LEVEL 2] 👁️ Perception Layer: News + Memory Analysis...")
        
        # 1. News Perception
        try:
            raw_news = self.news_fetcher.get_context(symbol)  # Returns formatted string
            news_digest = self.news_digest.digest(raw_news, symbol)  # Returns NewsDigest object
            logger.info(
                f"✅ [PERCEPTION] News: {news_digest.sentiment.value} "
                f"(Impact: {news_digest.impact_level.value}, Headlines: {news_digest.headline_count})"
            )
        except Exception as e:
            logger.error(f"❌ [PERCEPTION] News digest failed: {e}")
            # Fallback to neutral news digest
            from agents.trm.news_digest_agent import NewsImpact, NewsSentiment
            news_digest = NewsDigest(
                impact_level=NewsImpact.LOW,
                sentiment=NewsSentiment.NEUTRAL,
                summary="News fetch error - proceeding with neutral assumption",
                headline_count=0
            )
            
        # 1b. Symbol Specific Sentiment (New in v2.0)
        try:
            # We reuse the raw news string, but ideally we'd pass a list of headlines
            # Extract headlines from raw news for the agent
            headlines = [line.strip() for line in raw_news.split('\n') if line.strip() and not line.startswith("RECENT")]
            symbol_sentiment = self.symbol_sentiment_agent.analyze(symbol, headlines)
            logger.info(f"✅ [PERCEPTION] Symbol Sentiment: {symbol_sentiment.score:.2f} ({symbol_sentiment.zone.value})")
        except Exception as e:
            logger.error(f"❌ [PERCEPTION] Symbol sentiment failed: {e}")
            symbol_sentiment = None
        
        # 2. Memory Perception (Enhanced with Global Data Lake)
        try:
            # Get MemoryNarrative object for metrics
            memory_narrative = self.memory_summarizer.summarize(symbol, current_regime.id)
            
            # Get unified context (Trade History + Global Market Context)
            unified_memory_context = self.memory_summarizer.get_unified_context(
                symbol, 
                current_regime.id, 
                include_market=True
            )
            
            logger.info(
                f"✅ [PERCEPTION] Memory: Win Rate={memory_narrative.regime_win_rate:.1%}, "
                f"Hallucination Rate={memory_narrative.hallucination_rate:.1%}"
            )
            
            # Log market context from Global Data Lake
            market_context_only = self.memory_summarizer.get_market_context(symbol, days=30)
            logger.info(f"📊 [PERCEPTION] Global Market Context:\n{market_context_only}")
            
        except Exception as e:
            logger.error(f"❌ [PERCEPTION] Memory summarizer failed: {e}")
            # Fallback to neutral memory narrative
            memory_narrative = MemoryNarrative(
                regime_win_rate=0.5,
                total_trades_in_regime=0,
                primary_failure_mode="Unknown",
                hallucination_rate=0.0,
                confidence_calibration="N/A",
                narrative="Memory fetch error - no historical context available"
            )
            unified_memory_context = memory_narrative.narrative
        
        # --- LEVEL 3: COGNITION (LLM) ---
        logger.info(f"[LEVEL 3] 🤖 Cognition Layer: LLM Reasoning...")
        
        # 1. Get Current Macro Regime
        regime = current_regime
        logger.info(f"🌍 Market Regime: {regime.id} ({regime.name})")
        
        # 2. Fetch Precedents (Learning Book)
        precedent_summary = self.find_precedents(symbol, current_vol, trust_result.metrics.overall_trust_score)
        
        # 3. Build Enriched Context with Perception Layer Outputs
        memory_str = self.memory.get_summary(symbol)
        
        # Use RegimeTracker's get_prompt_context() method for formatted context
        macro_context = self.regime_tracker.get_prompt_context()
        
        # Inject News, Memory, and Technical Indicators into Context (Phase 3)
        full_memory_context = (
            f"{memory_str}\n\n"
            f"{precedent_summary}\n\n"
            f"MACRO CONTEXT:\n{macro_context}\n\n"
            f"--- PHASE 3: TECHNICAL INDICATORS ---\n"
            f"RSI(14): {latest['rsi_14']:.1f} (Overbought if > 70)\n"
            f"MACD Histogram: {latest['macd_hist']:.2f} (Positive = Bullish Momentum)\n"
            f"Volume Ratio: {latest['volume_ratio']:.2f}x (vs 20-day avg)\n"
            f"Trend SMA: {latest['trend_sma']:.2f} (Price vs 50-day MA)\n\n"
            f"--- PERCEPTION LAYER INSIGHTS ---\n"
            f"NEWS SENTIMENT: {news_digest.sentiment.value} (Impact: {news_digest.impact_level.value})\n"
            f"NEWS SUMMARY: {news_digest.summary}\n\n"
            f"--- UNIFIED MEMORY CONTEXT (Trade History + Global Market) ---\n"
            f"{unified_memory_context}"
        )
        
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

        # Enforce minimum confidence dynamically
        if (
            llm_decision.decision == ReasoningDecision.APPROVE
            and llm_decision.confidence < min_confidence
        ):
            logger.info(
                f"🔧 [STAGE 3] Downgrading decision to WAIT: "
                f"confidence {llm_decision.confidence:.2f} < min_confidence {min_confidence:.2f}"
            )
            llm_decision.decision = ReasoningDecision.WAIT
            llm_decision.rationale = (
                f"Confidence {llm_decision.confidence:.2f} below threshold {min_confidence:.2f}"
            )

        logger.info(
            f"✅ [LEVEL 3] Decision: {llm_decision.decision.value} "
            f"(Conf: {llm_decision.confidence:.2f}, min_conf={min_confidence:.2f})"
        )

        # --- LEVEL 4: POLICY (TRM) ---
        logger.info(f"[LEVEL 4] 🛡️ Policy Layer: Risk Policy Evaluation...")
        
        # Get v1.5 metrics from LLM response
        proposer_conf = getattr(llm_decision, 'proposer_confidence', None)
        critique_flaws = getattr(llm_decision, 'critique_flaws_count', None)
        
        # Construct TRM Input
        try:
            trm_input = TRMInput(
                symbol=symbol,
                forecast_confidence=forecast_confidence,
                trust_score=trust_result.metrics.overall_trust_score,
                news_digest=news_digest,
                symbol_sentiment=symbol_sentiment,
                memory_narrative=memory_narrative,
                llm_decision=llm_decision.decision,
                llm_confidence=llm_decision.confidence,
                critique_flaws_count=critique_flaws
            )
            
            # Call Risk Policy Agent
            final_verdict = self.risk_policy.decide(trm_input)
            
            logger.info(
                f"✅ [LEVEL 4] Final Verdict: {final_verdict.decision.value} "
                f"(Conf: {final_verdict.original_confidence:.2f} → {final_verdict.confidence:.2f}, "
                f"Veto: {final_verdict.veto_applied})"
            )
            logger.info(f"[LEVEL 4] {final_verdict.override_reason}")
            
        except Exception as e:
            logger.error(f"❌ [LEVEL 4] Risk policy failed: {e}")
            # Fallback: use LLM decision without policy enforcement
            final_verdict = FinalVerdict(
                decision=llm_decision.decision,
                confidence=llm_decision.confidence,
                original_confidence=llm_decision.confidence,
                confidence_adjustment=0.0,
                veto_applied=False,
                veto_reason="NO_VETO",
                override_reason="Policy evaluation error - using raw LLM decision"
            )

        # --- EXECUTION ---
        # Debug logging for v1.5 metrics
        logger.info(
            f"[EXECUTION] v1.5 Metrics extracted - "
            f"proposer_conf: {proposer_conf}, "
            f"critique_flaws: {critique_flaws}, "
            f"regime: {current_regime.id}"
        )
        
        # Save trade with all metrics including TRM details
        trade_id = self.memory.add_trade(
            context=context,
            response=llm_decision,
            proposer_confidence=proposer_conf,
            critique_flaws_count=critique_flaws,
            regime_id=current_regime.id,
            regime_name=current_regime.name,
            trm_details={
                "news_impact": news_digest.impact_level.value,
                "news_sentiment": news_digest.sentiment.value,
                "news_summary": news_digest.summary,
                "memory_win_rate": memory_narrative.regime_win_rate,
                "memory_hallucination_rate": memory_narrative.hallucination_rate,
                "critic_confidence": llm_decision.confidence,
                "critic_flaws": critique_flaws or 0,
                "policy_veto": final_verdict.veto_applied,
                "policy_veto_reason": final_verdict.veto_reason.value,
                "override_reason": final_verdict.override_reason,
                "waterfall_steps": {
                    "forecast_confidence": forecast_confidence,
                    "trust_score": trust_result.metrics.overall_trust_score,
                    "llm_confidence": llm_decision.confidence,
                    "final_confidence": final_verdict.confidence,
                    "confidence_adjustment": final_verdict.confidence_adjustment
                }
            }
        )
        
        logger.info(f"[EXECUTION] Trade {trade_id} saved with proposer_conf={proposer_conf}, critique_flaws={critique_flaws}")

        # Use Final Verdict for execution decision
        if final_verdict.decision == ReasoningDecision.APPROVE and not final_verdict.veto_applied:
            
            # --- TASK C: PORTFOLIO LEVEL CHECK ---
            correlation_risk_ok = True
            if self.broker and self.broker.is_connected():
                current_positions = self.broker.get_positions()
                if not self.portfolio_manager.check_correlation_risk(symbol, current_positions):
                    correlation_risk_ok = False
            
            if not correlation_risk_ok:
                logger.warning(f"⚠️ [EXECUTION] REJECTED: High Correlation Risk for {symbol}")
                return TradeDecision(
                    symbol=symbol,
                    decision="REJECT",
                    stage="portfolio_risk",
                    reason="Portfolio Correlation limit exceeded (>0.8)",
                    forecast_output=forecast_output,
                    trust_evaluation=trust_result,
                    llm_response=llm_decision,
                    final_verdict=final_verdict,
                    news_digest=news_digest,
                    memory_narrative=memory_narrative
                )

            processing_time = time.time() - start_time
            
            # Determine Size
            quantity = 0.0001 if "-USD" in symbol else 1
            
            logger.info(f"🟢 [EXECUTION] APPROVED! Sending BUY for {quantity} {symbol}...")
            
            if self.broker and self.broker.is_connected():
                if self.settings.live_trading_enabled:
                    order = self.broker.execute_trade("BUY", symbol, quantity)
                    if order:
                        logger.info(f"🚀 Order Placed: Order ID {order.orderId}")
                    else:
                        logger.error("❌ Order Placement Failed")
                else:
                    logger.warning(f"🛑 Live Trading DISABLED. Skipping execution for {quantity} {symbol}.")
            else:
                logger.warning("⚠️ Broker not connected. Trade skipped.")
            
            # Return TradeDecision for backward compatibility
            return TradeDecision(
                symbol=symbol,
                decision="APPROVE",
                stage="execution",
                reason=f"Policy approved with final confidence {final_verdict.confidence:.2f} (LLM: {llm_decision.confidence:.2f})",
                forecast_output=forecast_output,
                trust_evaluation=trust_result,
                llm_response=llm_decision,
                execution_order={"action": "BUY", "symbol": symbol, "price": current_price, "quantity": quantity},
                final_verdict=final_verdict,
                news_digest=news_digest,
                memory_narrative=memory_narrative
            )
        else:
            # Rejected by policy or LLM
            reject_reason = "VETOED by Risk Policy" if final_verdict.veto_applied else f"LLM {llm_decision.decision.value}"
            logger.info(f"⚠️ [EXECUTION] REJECTED: {reject_reason}. Logged to memory.")
            
            # Return TradeDecision even when rejected (for backward compatibility)
            return TradeDecision(
                symbol=symbol,
                decision=final_verdict.decision.value,
                stage="execution",
                reason=f"{reject_reason}: {final_verdict.override_reason}",
                forecast_output=forecast_output,
                trust_evaluation=trust_result,
                llm_response=llm_decision,
                final_verdict=final_verdict,
                news_digest=news_digest,
                memory_narrative=memory_narrative
            )

    def shutdown(self):
        if self.broker:
            self.broker.disconnect()
            logger.info("Broker disconnected.")
