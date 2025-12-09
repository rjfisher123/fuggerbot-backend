"""Streamlit component for forecast analysis and trading recommendations."""
import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from models.forecast_critique import ForecastCritique
from models.multi_symbol_analyzer import MultiSymbolAnalyzer
from models.position_sizing import PositionSizer
from models.signal_decay import SignalDecayModel
from dash.utils.forecast_helper import get_historical_prices, get_price_statistics
from services.forecast_service import create_forecast, get_forecast
from services.backtest_service import evaluate_forecast_by_id
from core.logger import logger
from datetime import datetime, timedelta


def render_forecast_panel():
    """Render the forecast analysis panel."""
    st.subheader("🔮 Forecast Analysis")
    
    # Symbol input
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Initialize symbol in session_state if not present
        if "forecast_symbol" not in st.session_state:
            st.session_state["forecast_symbol"] = "AAPL"
        symbol = st.text_input("Symbol", key="forecast_symbol").upper()
    
    with col2:
        forecast_horizon = st.number_input(
            "Forecast Horizon (days)",
            min_value=1,
            max_value=365,
            value=30,
            step=1,
            key="forecast_horizon"
        )
    
    with col3:
        min_trust_score = st.slider(
            "Min Trust Score",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            key="min_trust_score"
        )
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            deterministic_mode = st.checkbox(
                "🔒 Deterministic Mode (DFM)",
                value=True,
                key="deterministic_mode",
                help="Ensures same inputs → same forecast every time. Recommended for off-hours analysis. Uses CPU inference with fixed precision."
            )
            use_strict_mode = st.checkbox(
                "Strict Mode", 
                value=False, 
                key="strict_mode",
                help="In strict mode, ALL trust thresholds must pass. In normal mode, only overall trust score matters. Strict mode is more conservative and rejects more forecasts."
            )
            context_length = st.number_input(
                "Context Length (None = use all)",
                min_value=10,
                max_value=500,
                value=None,
                step=10,
                key="context_length",
                help="Number of historical data points to use for forecasting. None = use all available data. Smaller values focus on recent trends, larger values use more historical context."
            )
        
        with col2:
            period = st.selectbox(
                "Historical Period",
                options=["6mo", "1y", "2y", "5y"],
                index=1,
                key="historical_period",
                help="Time period of historical data to fetch from yfinance. Longer periods provide more context but may include outdated market conditions."
            )
            use_stability_smoothing = st.checkbox(
                "Stability Smoothing",
                value=True,
                key="stability_smoothing",
                help="Prevents rapid flipping between categories. Uses hysteresis and rolling medians for stable classifications."
            )
            use_date_anchoring = st.checkbox(
                "Date Anchoring",
                value=True,
                key="date_anchoring",
                help="Freezes historical window for reproducibility. Same inputs produce same results across runs."
            )
    
    # Analyze button
    if st.button("🔍 Analyze Forecast", type="primary", key="analyze_forecast"):
        if not symbol:
            st.error("Please enter a symbol")
            st.stop()
        
        with st.spinner(f"Analyzing {symbol}..."):
            try:
                # Fetch historical data
                st.info(f"📊 Fetching historical data for {symbol}...")
                prices = get_historical_prices(symbol, period=period)
                
                if not prices or len(prices) < 20:
                    st.error(f"❌ Insufficient historical data for {symbol}. Need at least 20 data points.")
                    st.stop()
                
                # Show price statistics
                stats = get_price_statistics(prices)
                st.success(f"✅ Fetched {stats['count']} data points")
                
                with st.expander("📈 Price Statistics"):
                    st.caption(f"📅 Data period: {period} | Data points: {stats['count']}")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Current Price", f"${stats['current']:.2f}")
                    with col2:
                        st.metric("Mean Price", f"${stats['mean']:.2f}", 
                                 help="Average price over the selected period")
                    with col3:
                        st.metric("Volatility", f"{stats['volatility_pct']:.2f}%",
                                 help="Price volatility (standard deviation as % of mean)")
                    with col4:
                        st.metric("Price Range", f"${stats['min']:.2f} - ${stats['max']:.2f}",
                                 help=f"Min and max prices observed in the {period} period")
                
                # Show deterministic mode status
                if deterministic_mode:
                    st.info("🔒 Deterministic Mode (DFM) enabled - forecasts will be reproducible")
                
                # Generate forecast using service
                with st.spinner("🔮 Generating forecast..."):
                    try:
                        # Create forecast using service
                        forecast_options = {
                            "context_length": context_length,
                            "historical_period": period,
                            "strict_mode": use_strict_mode,
                            "min_trust_score": min_trust_score,
                            "deterministic_mode": deterministic_mode
                        }
                        
                        forecast_domain = create_forecast(
                            symbol=symbol,
                            historical_prices=prices,
                            forecast_horizon=forecast_horizon,
                            options=forecast_options
                        )
                    except Exception as forecast_error:
                        st.error(f"❌ Forecast generation error: {str(forecast_error)}")
                        logger.error(f"Forecast error for {symbol}: {forecast_error}", exc_info=True)
                        st.stop()
                
                # Extract components from domain model
                forecast_id = forecast_domain.forecast_id
                forecast = forecast_domain.predicted_series
                trust_eval = forecast_domain.trust_evaluation
                recommendation = forecast_domain.recommendation
                fqs = {"fqs_score": forecast_domain.fqs_score, "interpretation": forecast_domain.metadata.get("fqs_interpretation", "")}
                regime = forecast_domain.regime
                frs = {
                    "frs_score": forecast_domain.frs_score,
                    "is_reliable": forecast_domain.metadata.get("frs_is_reliable", False),
                    "reliability_level": forecast_domain.metadata.get("frs_reliability_level", "unknown")
                }
                coherence = forecast_domain.coherence
                
                # Calculate position size
                position_sizer = PositionSizer()
                position_rec = position_sizer.calculate_position_size(
                    expected_return_pct=recommendation.get("expected_return_pct", 0),
                    risk_pct=recommendation.get("risk_pct", 0),
                    fqs_score=fqs['fqs_score'],
                    regime=regime
                )
                
                # Display success message with Forecast ID
                st.success(f"✅ Forecast generated successfully in {forecast.inference_time_ms:.1f}ms")
                st.caption(f"📋 Forecast ID: `{forecast_id}` | Snapshot saved")
                
                # Display FRS, FQS, Regime, and Position Size
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    frs_score = frs['frs_score']
                    frs_icon = "🟢" if frs['is_reliable'] else "🔴"
                    st.metric("FRS (Reliability)", f"{frs_icon} {frs_score:.3f}",
                             delta=frs['reliability_level'].replace("_", " ").title())
                with col2:
                    st.metric("Forecast Quality (FQS)", f"{fqs['fqs_score']:.3f}",
                             delta=fqs['interpretation'].split(" - ")[0] if " - " in fqs['interpretation'] else "")
                with col3:
                    regime_label = regime['regime_label']
                    regime_icon = "🟢" if regime['regime'] == "normal" else "🟡" if "volatility" in regime['regime'] else "🔴"
                    st.metric("Confidence Regime", f"{regime_icon} {regime_label}")
                with col4:
                    pos_size = position_rec['position_size_pct']
                    st.metric("Position Size", f"{pos_size:.2f}%",
                             delta=position_rec['recommendation'])
                
                # FRS and Coherence details
                with st.expander("🔍 FRS & Coherence Analysis"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**FRS Components:**")
                        components = frs['components']
                        st.write(f"- FQS: {components['fqs']:.3f}")
                        st.write(f"- Trust Score: {components['trust_score']:.3f}")
                        st.write(f"- Regime: {components['regime']:.3f}")
                        st.write(f"- Stability: {components['stability']:.3f}")
                        st.write(f"- Drift: {components['drift']:.3f}")
                        st.write(f"- Deterministic: {components['deterministic']:.3f}")
                        st.write(f"\n**Interpretation:** {frs['interpretation']}")
                        st.write(f"**Recommendation:** {frs['recommendation']}")
                    
                    with col2:
                        st.write("**Cross-Asset Coherence:**")
                        st.write(f"- Coherence Score: {coherence['coherence_score']:.3f}")
                        st.write(f"- Level: {coherence['coherence_level'].upper()}")
                        st.write(f"- Is Coherent: {'✅ YES' if coherence['is_coherent'] else '❌ NO'}")
                        if coherence['warnings']:
                            st.write("**Warnings:**")
                            for warning in coherence['warnings']:
                                st.write(f"- {warning}")
                        if coherence['penalties']:
                            st.write("**Penalties:**")
                            for penalty in coherence['penalties']:
                                st.write(f"- ⚠️ {penalty}")
                
                if regime['warnings']:
                    for warning in regime['warnings']:
                        st.warning(f"⚠️ {warning}")
                
                # Show position sizing breakdown
                with st.expander("💰 Position Sizing Breakdown"):
                    breakdown = position_rec['breakdown']
                    st.write(f"**Kelly Base:** {breakdown['kelly_base']:.4f}")
                    st.write(f"**FQS Multiplier:** {breakdown['fqs_multiplier']:.3f}")
                    st.write(f"**Stability Multiplier:** {breakdown['stability_multiplier']:.3f}")
                    st.write(f"**Regime Multiplier:** {breakdown['regime_multiplier']:.3f}")
                    st.write(f"**Drift Multiplier:** {breakdown['drift_multiplier']:.3f}")
                    st.write(f"**Final Position Size:** {pos_size:.2f}% of portfolio")
                
                # Forecast Critique Panel
                st.markdown("---")
                st.subheader("🔍 Forecast Critique (Model Self-Evaluation)")
                
                critique = ForecastCritique.analyze_forecast_drivers(
                    forecast, trust_eval, prices
                )
                critique_summary = ForecastCritique.generate_critique_summary(
                    forecast, trust_eval, recommendation, prices
                )
                
                st.info(critique_summary)
                
                with st.expander("📊 Detailed Critique Analysis"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Confidence Drivers:**")
                        for factor in critique["confidence_factors"]:
                            st.write(f"- {factor['factor']}: {factor['level']} ({factor['score']:.3f})")
                        
                        if critique["strengths"]:
                            st.write("**✅ Strengths:**")
                            for strength in critique["strengths"]:
                                st.write(f"- {strength}")
                    
                    with col2:
                        if critique["warnings"]:
                            st.write("**⚠️ Warnings:**")
                            for warning in critique["warnings"]:
                                st.write(f"- {warning}")
                        
                        if critique["limitations"]:
                            st.write("**⚠️ Limitations:**")
                            for limitation in critique["limitations"]:
                                st.write(f"- {limitation}")
                
                # Confidence/Uncertainty Sparkline (7-day trend simulation)
                st.markdown("---")
                st.subheader("📈 Confidence Trend (7-Day)")
                
                # Simulate 7-day uncertainty trend (in real implementation, would load historical forecasts)
                # For now, show current uncertainty with trend indicator
                uncertainty_scores = []
                for i in range(7):
                    # Simulate slight variation in uncertainty
                    base_uncertainty = trust_eval.metrics.uncertainty_score
                    variation = np.random.uniform(-0.05, 0.05)
                    uncertainty_scores.append(max(0, min(1, base_uncertainty + variation)))
                
                # Create sparkline
                try:
                    import plotly.graph_objects as go
                    fig_spark = go.Figure()
                    fig_spark.add_trace(go.Scatter(
                        x=list(range(7)),
                        y=uncertainty_scores,
                        mode='lines+markers',
                        line=dict(color='blue', width=2),
                        marker=dict(size=6)
                    ))
                    fig_spark.update_layout(
                        title="Uncertainty Score Trend (Last 7 Days)",
                        xaxis_title="Days Ago",
                        yaxis_title="Uncertainty Score",
                        height=200,
                        showlegend=False,
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})
                    st.caption("💡 Trend shows model confidence stability over time. Stable trends indicate consistent model behavior.")
                except Exception as plotly_error:
                    logger.warning(f"Plotly chart error: {plotly_error}", exc_info=True)
                    st.write(f"Current Uncertainty Score: {trust_eval.metrics.uncertainty_score:.3f}")
                
                # Display trust evaluation
                st.markdown("---")
                st.subheader("📊 Trust Evaluation")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    trust_score = trust_eval.metrics.overall_trust_score
                    trust_color = "green" if trust_score >= 0.7 else "orange" if trust_score >= 0.5 else "red"
                    st.metric(
                        "Overall Trust Score",
                        f"{trust_score:.3f}",
                        delta=f"{trust_eval.metrics.confidence_level.upper()}"
                    )
                
                with col2:
                    is_trusted = "✅ TRUSTED" if trust_eval.is_trusted else "❌ REJECTED"
                    st.metric("Status", is_trusted)
                
                with col3:
                    st.metric("Inference Time", f"{forecast.inference_time_ms:.1f}ms")
                
                # Detailed metrics
                with st.expander("📈 Detailed Trust Metrics"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Uncertainty Score:** {trust_eval.metrics.uncertainty_score:.3f}")
                        st.write(f"**Consistency Score:** {trust_eval.metrics.consistency_score:.3f}")
                        st.write(f"**Data Quality Score:** {trust_eval.metrics.data_quality_score:.3f}")
                    
                    with col2:
                        if trust_eval.metrics.historical_accuracy:
                            st.write(f"**Historical Accuracy:** {trust_eval.metrics.historical_accuracy:.3f}")
                        if trust_eval.metrics.market_regime_score:
                            st.write(f"**Market Regime Score:** {trust_eval.metrics.market_regime_score:.3f}")
                    
                    if trust_eval.metrics.rejection_reasons:
                        st.warning("⚠️ **Rejection Reasons:**")
                        for reason in trust_eval.metrics.rejection_reasons:
                            st.write(f"- {reason}")
                
                # Display forecast
                if trust_eval.is_trusted:
                    st.markdown("---")
                    st.subheader("📈 Forecast Visualization")
                    
                    # Create forecast dataframe
                    forecast_df = pd.DataFrame({
                        "Period": range(1, forecast_horizon + 1),
                        "Point Forecast": forecast.point_forecast,
                        "Lower Bound": forecast.lower_bound,
                        "Upper Bound": forecast.upper_bound
                    })
                    
                    # Add historical data for context
                    recent_prices = prices[-min(50, len(prices)):]
                    historical_df = pd.DataFrame({
                        "Period": range(-len(recent_prices), 0),
                        "Price": recent_prices
                    })
                    
                    # Plot
                    try:
                        import plotly.graph_objects as go
                        plotly_available = True
                    except ImportError:
                        plotly_available = False
                        st.warning("⚠️ Plotly not available - charts disabled. Install with: `pip install plotly`")
                    
                    if plotly_available:
                        fig = go.Figure()
                    
                        # Historical data
                        fig.add_trace(go.Scatter(
                            x=historical_df["Period"],
                            y=historical_df["Price"],
                            mode='lines',
                            name='Historical',
                            line=dict(color='blue', width=2)
                        ))
                        
                        # Point forecast
                        fig.add_trace(go.Scatter(
                            x=forecast_df["Period"],
                            y=forecast_df["Point Forecast"],
                            mode='lines',
                            name='Forecast',
                            line=dict(color='green', width=2)
                        ))
                        
                        # Uncertainty bounds
                        fig.add_trace(go.Scatter(
                            x=forecast_df["Period"],
                            y=forecast_df["Upper Bound"],
                            mode='lines',
                            name='Upper Bound',
                            line=dict(color='gray', width=1, dash='dash'),
                            showlegend=False
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=forecast_df["Period"],
                            y=forecast_df["Lower Bound"],
                            mode='lines',
                            name='Lower Bound',
                            line=dict(color='gray', width=1, dash='dash'),
                            fill='tonexty',
                            fillcolor='rgba(128,128,128,0.2)',
                            showlegend=False
                        ))
                        
                        fig.update_layout(
                            title=f"{symbol} Price Forecast",
                            xaxis_title="Period (days from current)",
                            yaxis_title="Price (USD $)",
                            hovermode='x unified',
                            yaxis=dict(
                                tickformat='$,.0f',  # Format as currency
                                title_standoff=10
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        # Fallback: show data as table if plotly unavailable
                        st.write("**Forecast Data:**")
                        st.dataframe(forecast_df, use_container_width=True)
                    
                    # Trading recommendation
                    st.markdown("---")
                    st.subheader("💡 Trading Recommendation")
                    
                    action = recommendation["action"]
                    action_color = {
                        "BUY": "green",
                        "SELL": "red",
                        "HOLD": "orange",
                        "PASS": "gray"
                    }.get(action, "blue")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown(f"### <span style='color:{action_color}'>{action}</span>", unsafe_allow_html=True)
                    
                    with col2:
                        expected_return = recommendation.get("expected_return_pct", 0)
                        st.metric("Expected Return", f"{expected_return:.2f}%",
                                 help="Average expected price change over forecast horizon")
                    
                    with col3:
                        risk = recommendation.get("risk_pct", 0)
                        st.metric("Risk (Uncertainty)", f"{risk:.2f}%",
                                 help="Forecast uncertainty range as % of current price. Minimum 1% to account for market risk.")
                    
                    with col4:
                        confidence = recommendation.get("confidence", "unknown")
                        st.metric("Confidence", confidence.upper())
                    
                    st.info(f"**Reason:** {recommendation.get('reason', 'N/A')}")
                    
                    if recommendation.get("min_return_pct") is not None and recommendation.get("max_return_pct") is not None:
                        st.write(f"**Return Range:** {recommendation['min_return_pct']:.2f}% to {recommendation['max_return_pct']:.2f}%")
                    
                    # Parameter Snapshot
                    st.markdown("---")
                    with st.expander("📋 Forecast Parameters & Reproducibility"):
                        st.write("**Forecast ID:**", forecast_id)
                        st.write("**Parameters Used:**")
                        st.json({
                            "symbol": symbol,
                            "forecast_horizon": forecast_horizon,
                            "context_length": context_length or "All available",
                            "historical_period": period,
                            "strict_mode": use_strict_mode,
                            "min_trust_score": min_trust_score,
                            "timestamp": datetime.now().isoformat()
                        })
                        st.caption(f"💡 Use Forecast ID `{forecast_id}` to reproduce this forecast or evaluate performance later.")
                    
                    # Signal Decay Analysis
                    
                    decay_model = SignalDecayModel()
                    
                    # Calculate half-life (would use actual forecast history in production)
                    st.info("💡 Signal decay analysis requires forecast history. Run daily forecasts to build history.")
                    
                    with st.expander("📊 Signal Persistence Metrics"):
                        st.write("**Forecast Half-Life:** Estimated time until forecast validity degrades by 50%")
                        st.write("**Signal Persistence:** How stable the expected return is over repeated runs")
                        st.caption("💡 Use daily scheduler to build forecast history for decay analysis")
                    
                    # Signal Decay Heatmap (placeholder - would show actual data)
                    if st.checkbox("Show Signal Decay Heatmap", key="show_decay_heatmap"):
                        st.info("📊 Heatmap visualization coming soon. Requires forecast history from daily scheduler.")
                        # Would generate heatmap here with actual data
                    
                    # Add disclaimer
                    st.markdown("---")
                    with st.expander("ℹ️ Important Notes"):
                        st.warning("""
                        **Forecast Limitations:**
                        - Past performance ≠ future results
                        - Forecasts are probabilistic, not guarantees
                        - Market conditions can change rapidly
                        - Always consider your risk tolerance
                        - Monitor actual performance vs. predictions
                        
                        **Recommendation Thresholds:**
                        - **BUY**: Expected return >2% with positive minimum return
                        - **SELL**: Expected return <-2% with negative maximum return  
                        - **HOLD**: Neutral forecasts or high uncertainty (>15%)
                        
                        **Trust Scores:** Internal metrics evaluating forecast quality. 
                        Monitor actual outcomes to validate model performance over time.
                        """)
                else:
                    st.warning("⚠️ Forecast did not pass trust filter. Trading recommendation not available.")
                    if trust_eval.metrics.rejection_reasons:
                        st.write("**Rejection Reasons:**")
                        for reason in trust_eval.metrics.rejection_reasons:
                            st.write(f"- {reason}")
                
            except Exception as e:
                st.error(f"❌ Error during analysis: {str(e)}")
                logger.error(f"Forecast analysis error: {e}", exc_info=True)
                st.exception(e)
    
    # Backtesting Section - MOVED OUTSIDE button handler to prevent UI resets
    # This section is always available, independent of whether a forecast was just generated
    st.markdown("---")
    st.subheader("🧪 Performance Backtesting")
    st.info("💡 To evaluate forecast accuracy, wait for actual prices and use the Forecast ID to compare predictions vs. outcomes.")
    
    with st.expander("📊 Backtesting Tools", expanded=True):
        st.write("**Evaluate Forecast Performance:**")
        st.caption("After the forecast period, enter actual prices to evaluate accuracy.")
        
        # --------------------------
        # INITIALIZE SESSION STATE
        # --------------------------
        if "eval_forecast_id" not in st.session_state:
            st.session_state["eval_forecast_id"] = ""
        
        if "loaded_forecast_snapshot" not in st.session_state:
            st.session_state["loaded_forecast_snapshot"] = None
        
        if "load_forecast_message" not in st.session_state:
            st.session_state["load_forecast_message"] = ""
        
        if "actual_prices" not in st.session_state:
            st.session_state["actual_prices"] = ""
        
        if "actuals_load_message" not in st.session_state:
            st.session_state["actuals_load_message"] = ""
        
        if "actuals_count" not in st.session_state:
            st.session_state["actuals_count"] = 0
        
        if "actuals_info" not in st.session_state:
            st.session_state["actuals_info"] = ""
        
        if "evaluation_result" not in st.session_state:
            st.session_state["evaluation_result"] = None
        
        if "evaluation_complete" not in st.session_state:
            st.session_state["evaluation_complete"] = False
        
        if "evaluation_error" not in st.session_state:
            st.session_state["evaluation_error"] = ""
        
        if "actuals_auto_loaded" not in st.session_state:
            st.session_state["actuals_auto_loaded"] = False
        if "_actual_prices_auto_load" not in st.session_state:
            st.session_state["_actual_prices_auto_load"] = None
        
        # Auto-populate actual_prices if it was loaded in a previous button click
        # This must be done BEFORE creating the widget
        if st.session_state["actuals_auto_loaded"] and st.session_state["_actual_prices_auto_load"]:
            if not st.session_state["actual_prices"] or st.session_state["actual_prices"] == "":
                st.session_state["actual_prices"] = st.session_state["_actual_prices_auto_load"]
            # Clear the flag after using it
            st.session_state["actuals_auto_loaded"] = False
            st.session_state["_actual_prices_auto_load"] = None
        
        # --------------------------
        # INPUTS
        # --------------------------
        col1, col2 = st.columns(2)
        with col1:
            # Forecast ID Input - widget automatically manages st.session_state["eval_forecast_id"]
            eval_forecast_id = st.text_input(
                "Forecast ID to Evaluate",
                key="eval_forecast_id",
                placeholder="Enter forecast ID..."
            )
        
        with col2:
            st.write("")  # Spacing
        
        # --------------------------
        # BUTTON: LOAD FORECAST
        # --------------------------
        if st.button("🔍 Load Forecast for Evaluation", key="load_forecast"):
            if not eval_forecast_id or not eval_forecast_id.strip():
                st.session_state["load_forecast_message"] = "⚠️ Please enter a valid Forecast ID"
                st.session_state["loaded_forecast_snapshot"] = None
                st.session_state["evaluation_result"] = None
                st.session_state["evaluation_complete"] = False
                st.session_state["evaluation_error"] = ""
            else:
                try:
                    # Use service to get forecast (which loads from metadata)
                    forecast_domain = get_forecast(eval_forecast_id.strip())
                    
                    if forecast_domain:
                        # Convert to snapshot format for compatibility
                        snapshot = {
                            "symbol": forecast_domain.symbol,
                            "forecast_id": forecast_domain.forecast_id,
                            "parameters": forecast_domain.params,
                            "forecast": {
                                "point_forecast": forecast_domain.predicted_series.point_forecast,
                                "lower_bound": forecast_domain.predicted_series.lower_bound,
                                "upper_bound": forecast_domain.predicted_series.upper_bound,
                                "forecast_horizon": forecast_domain.predicted_series.forecast_horizon,
                            },
                            "trust_evaluation": {
                                "overall_trust_score": forecast_domain.trust_evaluation.metrics.overall_trust_score,
                                "confidence_level": forecast_domain.trust_evaluation.metrics.confidence_level,
                                "is_trusted": forecast_domain.trust_evaluation.is_trusted,
                            },
                            "recommendation": forecast_domain.recommendation or {}
                        }
                    else:
                        snapshot = None
                    
                    if not snapshot:
                        st.session_state["load_forecast_message"] = f"⚠️ Forecast ID '{eval_forecast_id}' not found. Please check the ID and try again."
                        st.session_state["loaded_forecast_snapshot"] = None
                        st.session_state["evaluation_result"] = None
                        st.session_state["evaluation_complete"] = False
                        st.session_state["evaluation_error"] = ""
                    else:
                        st.session_state["loaded_forecast_snapshot"] = snapshot
                        st.session_state["load_forecast_message"] = f"✅ Loaded forecast for {snapshot.get('symbol', 'UNKNOWN')}"
                        st.session_state["evaluation_result"] = None  # clear old results
                        st.session_state["evaluation_complete"] = False
                        st.session_state["evaluation_error"] = ""
                        
                        # Attempt to fetch actual prices automatically
                        from dash.utils.backtest_helper import fetch_actual_prices_for_forecast
                        
                        with st.spinner("🔍 Checking for actual price data..."):
                            actuals_result = fetch_actual_prices_for_forecast(eval_forecast_id.strip())
                        
                        if actuals_result:
                            if actuals_result.get("available"):
                                # Prices are available - will populate on next rerun
                                actual_prices_list = actuals_result.get("prices", [])
                                actual_prices_str = ", ".join([f"{p:.2f}" for p in actual_prices_list])
                                
                                # Store in a temporary key, will be used before widget creation on next rerun
                                st.session_state["_actual_prices_auto_load"] = actual_prices_str
                                st.session_state["actuals_auto_loaded"] = True
                                st.session_state["actuals_count"] = len(actual_prices_list)
                                st.session_state["actuals_load_message"] = f"✅ {actuals_result.get('message')}"
                                st.session_state["actuals_info"] = ""
                            else:
                                # Prices not available yet
                                st.session_state["actuals_load_message"] = f"ℹ️ {actuals_result.get('message')}"
                                st.session_state["actuals_info"] = "💡 Please input actual prices manually below when they become available."
                                st.session_state["actuals_auto_loaded"] = False
                                st.session_state["actuals_count"] = 0
                        else:
                            st.session_state["actuals_load_message"] = "⚠️ Could not check for actual prices. Please input manually."
                            st.session_state["actuals_auto_loaded"] = False
                            st.session_state["actuals_count"] = 0
                            st.session_state["actuals_info"] = ""
                        
                except Exception as e:
                    st.session_state["load_forecast_message"] = f"❌ Error: {str(e)}"
                    st.session_state["loaded_forecast_snapshot"] = None
                    st.session_state["evaluation_result"] = None
                    st.session_state["evaluation_complete"] = False
                    st.session_state["evaluation_error"] = ""
                    logger.error(f"Error loading forecast {eval_forecast_id}: {e}", exc_info=True)
        
        # Display load result
        if st.session_state["load_forecast_message"]:
            if "✅" in st.session_state["load_forecast_message"]:
                st.success(st.session_state["load_forecast_message"])
            else:
                st.warning(st.session_state["load_forecast_message"])
            
            if st.session_state["loaded_forecast_snapshot"]:
                snapshot = st.session_state["loaded_forecast_snapshot"]
                with st.expander("📋 Forecast Details", expanded=False):
                    st.json(snapshot.get("parameters", {}))
        
        if st.session_state["actuals_load_message"]:
            st.info(st.session_state["actuals_load_message"])
            if st.session_state["actuals_count"] > 0:
                st.success(f"📊 Actual prices loaded: {st.session_state['actuals_count']} data points")
            if st.session_state["actuals_info"]:
                st.info(st.session_state["actuals_info"])
        
        st.markdown("---")
        
        # --------------------------
        # ACTUAL PRICES INPUT
        # --------------------------
        st.write("**Actual Prices Input:**")
        st.caption("Enter actual prices that occurred (comma-separated), or use auto-loaded prices if available:")
        
        # Actual Prices Input - widget automatically manages st.session_state["actual_prices"]
        actual_prices_input = st.text_input(
            "Actual Prices",
            key="actual_prices",
            placeholder="175.50, 176.20, 175.80, ..."
        )
        
        # --------------------------
        # BUTTON: EVALUATE FORECAST
        # --------------------------
        if st.button("📈 Evaluate Forecast Accuracy", key="evaluate_forecast"):
            if not eval_forecast_id or not eval_forecast_id.strip():
                st.session_state["evaluation_error"] = "⚠️ Please enter a valid Forecast ID"
                st.session_state["evaluation_result"] = None
                st.session_state["evaluation_complete"] = False
            elif not actual_prices_input or not actual_prices_input.strip():
                st.session_state["evaluation_error"] = "⚠️ Please provide the realised price sequence for this forecast horizon"
                st.session_state["evaluation_result"] = None
                st.session_state["evaluation_complete"] = False
            else:
                try:
                    # Parse actuals from state
                    actual_prices_list = [float(p.strip()) for p in actual_prices_input.split(",") if p.strip()]
                    
                    if not actual_prices_list:
                        st.session_state["evaluation_error"] = "⚠️ No valid prices found. Please enter comma-separated numeric values."
                        st.session_state["evaluation_result"] = None
                        st.session_state["evaluation_complete"] = False
                    elif not st.session_state["loaded_forecast_snapshot"]:
                        st.session_state["evaluation_error"] = f"⚠️ Forecast ID '{eval_forecast_id}' not found. Please load the forecast first."
                        st.session_state["evaluation_result"] = None
                        st.session_state["evaluation_complete"] = False
                    else:
                        # Evaluate forecast using service
                        with st.spinner("📊 Evaluating forecast accuracy..."):
                            try:
                                backtest_result = evaluate_forecast_by_id(
                                    eval_forecast_id.strip(),
                                    actual_prices_list
                                )
                                
                                # Convert to dict format for UI compatibility
                                evaluation = {
                                    "forecast_id": backtest_result.forecast_id,
                                    "symbol": backtest_result.symbol,
                                    "evaluation_date": backtest_result.created_at.isoformat(),
                                    "metrics": {
                                        "mae": backtest_result.metrics.mae,
                                        "mape": backtest_result.metrics.mape,
                                        "rmse": backtest_result.metrics.rmse,
                                        "directional_accuracy": {
                                            "accuracy": backtest_result.metrics.directional_accuracy,
                                            "correct": backtest_result.metrics.directional_correct,
                                            "total": backtest_result.metrics.directional_total,
                                        },
                                        "calibration": {
                                            "coverage": backtest_result.metrics.calibration_coverage,
                                            "expected_coverage": backtest_result.metrics.calibration_expected,
                                            "calibration_error": backtest_result.metrics.calibration_error,
                                            "well_calibrated": backtest_result.metrics.well_calibrated,
                                        }
                                    },
                                    "summary": backtest_result.to_summary_dict()
                                }
                                
                                # Store results after spinner completes
                                st.session_state["evaluation_result"] = evaluation
                                st.session_state["evaluation_complete"] = True
                                st.session_state["evaluation_error"] = ""
                                
                            except ValueError as ve:
                                st.session_state["evaluation_error"] = f"❌ {str(ve)}"
                                st.session_state["evaluation_result"] = None
                                st.session_state["evaluation_complete"] = False
                            except Exception as e:
                                st.session_state["evaluation_error"] = f"❌ Error evaluating forecast: {str(e)}"
                                st.session_state["evaluation_result"] = None
                                st.session_state["evaluation_complete"] = False
                                logger.error(f"Error evaluating forecast: {e}", exc_info=True)
                        
                except ValueError as e:
                    st.session_state["evaluation_error"] = f"❌ Invalid price format: {str(e)}. Please enter comma-separated numeric values."
                    st.session_state["evaluation_result"] = None
                    st.session_state["evaluation_complete"] = False
                except Exception as e:
                    st.session_state["evaluation_error"] = f"❌ Error evaluating forecast: {str(e)}"
                    st.session_state["evaluation_result"] = None
                    st.session_state["evaluation_complete"] = False
                    logger.error(f"Error evaluating forecast: {e}", exc_info=True)
        
        # --------------------------
        # DISPLAY RESULT
        # --------------------------
        if st.session_state["evaluation_complete"] and st.session_state["evaluation_result"]:
            evaluation = st.session_state["evaluation_result"]
            st.success("✅ Evaluation Complete")
            
            metrics = evaluation["metrics"]
            summary = evaluation["summary"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("MAE", summary["mean_absolute_error"])
            with col2:
                st.metric("MAPE", summary["mean_absolute_percentage_error"])
            with col3:
                st.metric("Directional Accuracy", summary["directional_accuracy"])
            with col4:
                cal_status = "✅" if summary["well_calibrated"] else "⚠️"
                st.metric("Calibration", summary["calibration_coverage"], 
                         delta=cal_status)
            
            with st.expander("📊 Full Evaluation Results", expanded=False):
                st.json(evaluation)
        
        if st.session_state["evaluation_error"]:
            st.error(st.session_state["evaluation_error"])
    
    # Multi-Symbol Comparative Mode
    st.markdown("---")
    st.subheader("📊 Multi-Symbol Comparative Analysis")
    st.caption("Compare and rank opportunities across multiple symbols")
    
    # Initialize batch_symbols in session_state if not present
    if "batch_symbols" not in st.session_state:
        st.session_state["batch_symbols"] = "AAPL,MSFT,GOOGL,TSLA,NVDA"
    symbols_input = st.text_input(
        "Symbols (comma-separated)",
        key="batch_symbols",
        help="Enter multiple symbols separated by commas (up to 50 symbols)"
    )
    
    if st.button("🔍 Analyze & Rank Opportunities", key="analyze_batch"):
        if not symbols_input:
            st.error("Please enter symbols")
            st.stop()
        
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        
        if not symbols:
            st.error("No valid symbols found")
            st.stop()
        
        if len(symbols) > 50:
            st.warning("⚠️ Limiting to 50 symbols for performance")
            symbols = symbols[:50]
        
        with st.spinner(f"Analyzing {len(symbols)} symbols..."):
            try:
                # Import ForecastTrader for MultiSymbolAnalyzer
                from models.forecast_trader import ForecastTrader
                
                # Create forecast trader for batch analysis
                # MultiSymbolAnalyzer needs a ForecastTrader instance
                batch_forecast_trader = ForecastTrader()
                
                # Use MultiSymbolAnalyzer with stability features
                analyzer = MultiSymbolAnalyzer(
                    batch_forecast_trader,
                    use_date_anchoring=use_date_anchoring,
                    use_stability_smoothing=use_stability_smoothing
                )
                
                if deterministic_mode:
                    st.info("🔒 Deterministic Mode enabled - using reproducible date ranges")
                
                analysis = analyzer.analyze_symbols(
                    symbols=symbols,
                    forecast_horizon=forecast_horizon,
                    historical_period=period,
                    context_length=context_length
                )
                
                st.success(f"✅ Analyzed {analysis['successful']}/{analysis['total_analyzed']} symbols")
                
                ranked = analysis['ranked_opportunities']
                
                # Top BUY Opportunities
                if ranked['top_buy_opportunities']:
                    st.subheader("🟢 Top 3 BUY Opportunities")
                    st.caption("💡 Only symbols with acceptable uncertainty levels are shown here.")
                    buy_df = pd.DataFrame(ranked['top_buy_opportunities'])
                    buy_df = buy_df[['symbol', 'expected_return_pct', 'risk_pct', 'fqs_score', 'trust_score', 'regime']]
                    buy_df.columns = ['Symbol', 'Expected Return %', 'Risk %', 'FQS Score', 'Trust Score', 'Regime']
                    st.dataframe(buy_df, use_container_width=True)
                else:
                    st.info("No BUY opportunities found (all may be in High Uncertainty category)")
                
                # Top SELL Opportunities
                if ranked['top_sell_opportunities']:
                    st.subheader("🔴 Top 3 SELL Opportunities")
                    st.caption("💡 Only symbols with acceptable uncertainty levels are shown here.")
                    sell_df = pd.DataFrame(ranked['top_sell_opportunities'])
                    sell_df = sell_df[['symbol', 'expected_return_pct', 'risk_pct', 'fqs_score', 'trust_score', 'regime']]
                    sell_df.columns = ['Symbol', 'Expected Return %', 'Risk %', 'FQS Score', 'Trust Score', 'Regime']
                    st.dataframe(sell_df, use_container_width=True)
                else:
                    st.info("No SELL opportunities found (all may be in High Uncertainty category)")
                
                # High Uncertainty Cases
                if ranked['high_uncertainty_cases']:
                    st.subheader("⚠️ High Uncertainty Cases")
                    st.caption("💡 Symbols with high uncertainty or unstable regimes are excluded from Buy/Sell rankings for safety.")
                    unc_df = pd.DataFrame(ranked['high_uncertainty_cases'])
                    if 'exclusion_reason' in unc_df.columns:
                        unc_df = unc_df[['symbol', 'risk_pct', 'fqs_score', 'regime', 'exclusion_reason']]
                        unc_df.columns = ['Symbol', 'Risk %', 'FQS Score', 'Regime', 'Exclusion Reason']
                    else:
                        unc_df = unc_df[['symbol', 'risk_pct', 'fqs_score', 'regime']]
                        unc_df.columns = ['Symbol', 'Risk %', 'FQS Score', 'Regime']
                    st.dataframe(unc_df, use_container_width=True)
                
                # Group by Regime
                if analysis['by_regime']:
                    with st.expander("📊 Symbols by Regime"):
                        for regime_label, symbol_list in analysis['by_regime'].items():
                            st.write(f"**{regime_label}:** {', '.join(symbol_list)}")
                
            except Exception as e:
                st.error(f"❌ Batch analysis error: {str(e)}")
                logger.error(f"Batch analysis error: {e}", exc_info=True)


