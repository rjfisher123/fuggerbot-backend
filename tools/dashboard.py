import streamlit as st
import pandas as pd
import json
import os
import subprocess
import plotly.express as px
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

# Config
st.set_page_config(page_title="FuggerBot Brain Scan", layout="wide")
st.title("🧠 FuggerBot Reasoning State")

# --- SIDEBAR CONFIG ---
st.sidebar.header("Configuration")
view_mode = st.sidebar.radio(
    "Dashboard Mode:",
    ("Trade Analysis", "War Games Results"),
    index=0
)

# Only show data source selection in Trade Analysis mode
if view_mode == "Trade Analysis":
    data_source = st.sidebar.selectbox(
        "Select Memory Source:",
        ("Live Production", "War Games Simulation"),
        index=0
    )
else:
    data_source = None

# Map selection to filename (only for Trade Analysis mode)
if view_mode == "Trade Analysis":
    if data_source == "Live Production":
        MEMORY_FILE = project_root / "data" / "trade_memory.json"
    else:
        MEMORY_FILE = project_root / "data" / "test_memory_wargames.json"
    st.sidebar.info(f"Reading from: `{MEMORY_FILE}`")
else:
    MEMORY_FILE = None
    WAR_GAMES_FILE = project_root / "data" / "war_games_results.json"
    st.sidebar.info(f"War Games: `{WAR_GAMES_FILE}`")

# Add refresh button to clear cache
if st.sidebar.button("🔄 Refresh Data", help="Clear cache and reload data"):
    st.cache_data.clear()
    st.rerun()

# =============================
# ADMIN ACTIONS PANEL
# =============================

st.sidebar.markdown("---")
st.sidebar.header("⚡ Admin Actions")
st.sidebar.caption("Trigger backend processes")

def run_background_process(command_list, log_name, description):
    """
    Run a command as a background process and log output.
    
    Args:
        command_list: Command to execute as a list (e.g., ["python", "script.py"])
        log_name: Name for the log file (e.g., "miner")
        description: Human-readable description for the toast message
    """
    try:
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{log_name}.log"
        
        # Append timestamp to log
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Started at: {datetime.now().isoformat()}\n")
            f.write(f"Command: {' '.join(command_list)}\n")
            f.write(f"{'='*50}\n")
        
        # Start process in background
        with open(log_file, 'a') as f:
            process = subprocess.Popen(
                command_list,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(project_root),
                text=True
            )
        
        st.success(f"🚀 Started {description}! (PID: {process.pid})")
        st.info(f"📝 Logs: `logs/{log_name}.log`")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to start {description}: {e}")
        return False

# Admin action buttons
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("⛏️ Re-Mine", help="Extract patterns from recent market data", use_container_width=True):
        run_background_process(
            ["python", "research/miner.py"],
            "miner_manual",
            "Data Miner"
        )

with col2:
    if st.button("🎮 War Games", help="Run strategy simulations", use_container_width=True):
        run_background_process(
            ["python", "daemon/simulator/war_games_runner.py"],
            "wargames_manual",
            "War Games Simulator"
        )

col3, col4 = st.sidebar.columns(2)

with col3:
    if st.button("🧠 Optimize", help="Select best strategy parameters", use_container_width=True):
        run_background_process(
            ["python", "agents/trm/strategy_optimizer_agent.py"],
            "optimizer_manual",
            "Strategy Optimizer"
        )

with col4:
    if st.button("📝 Review", help="Generate trade post-mortems", use_container_width=True):
        run_background_process(
            ["python", "daemon/reviewer.py"],
            "reviewer_manual",
            "Trade Reviewer"
        )

st.sidebar.caption("⚠️ These processes run in background. Check logs for progress.")


@st.cache_data(ttl=5)
def load_data(filepath):
    """Load trade memory data from JSON file."""
    filepath = Path(filepath)
    if not filepath.exists():
        return pd.DataFrame()
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
    
    if not data or 'trades' not in data:
        return pd.DataFrame()
    
    trades = data.get('trades', [])
    if not trades:
        return pd.DataFrame()
    
    # Convert to DataFrame - ensure all trades have consistent structure
    # Force post_mortem column to exist even if sparse
    # Also extract post_mortem fields BEFORE creating DataFrame to ensure they're preserved
    postmortem_data = {}
    for trade in trades:
        if 'post_mortem' not in trade:
            trade['post_mortem'] = None
        else:
            # Extract post-mortem fields immediately while we have the dict
            trade_id = trade.get('trade_id')
            if trade_id and trade.get('post_mortem'):
                pm = trade.get('post_mortem')
                if isinstance(pm, dict):
                    postmortem_data[trade_id] = {
                        'outcome_category': pm.get('outcome_category'),
                        'root_cause': pm.get('root_cause'),
                        'lesson_learned': pm.get('lesson_learned'),
                        'adjusted_confidence': pm.get('adjusted_confidence'),
                        'postmortem_outcome': pm.get('actual_outcome')
                    }
    
    df = pd.DataFrame(trades)
    
    # Apply extracted post-mortem data to DataFrame
    if postmortem_data:
        df['outcome_category'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('outcome_category'))
        df['root_cause'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('root_cause'))
        df['lesson_learned'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('lesson_learned'))
        df['adjusted_confidence'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('adjusted_confidence'))
        df['postmortem_outcome'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('postmortem_outcome'))
        # Convert adjusted_confidence to numeric
        df['adjusted_confidence'] = pd.to_numeric(df['adjusted_confidence'], errors='coerce')
        st.sidebar.success(f"📊 {len(postmortem_data)} trades with post-mortem data")
    else:
        # Initialize empty columns if no post-mortems
        df['outcome_category'] = None
        df['root_cause'] = None
        df['lesson_learned'] = None
        df['adjusted_confidence'] = None
        df['postmortem_outcome'] = None
    
    # Ensure numeric columns
    if 'confidence' in df.columns:
        df['llm_confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    if 'pnl' in df.columns:
        # Convert pnl to numeric, handling None/null values
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce')
        # Replace NaN with None for proper null checking
        df['pnl'] = df['pnl'].where(pd.notna(df['pnl']), None)
    if 'forecast_confidence' in df.columns:
        df['forecast_confidence'] = pd.to_numeric(df['forecast_confidence'], errors='coerce')
    if 'trust_score' in df.columns:
        df['trust_score'] = pd.to_numeric(df['trust_score'], errors='coerce')
    
    # Extract outcome type
    if 'outcome' in df.columns:
        df['outcome_type'] = df['outcome']
    elif 'regret' in df.columns:
        df['outcome_type'] = df['regret'].apply(lambda x: 'MISSED_OP' if x == 'MISSED_OP' else 'NORMAL')
    else:
        df['outcome_type'] = None
    
    # Post-mortem fields are already extracted above, so we don't need to do it again here
    
    return df


# =============================
# MAIN DASHBOARD ROUTING
# =============================

if view_mode == "War Games Results":
    # --- WAR GAMES ANALYSIS MODE ---
    st.title("🎮 War Games Analysis")
    st.markdown("**High-speed backtesting results across multiple scenarios**")
    
    @st.cache_data(ttl=60)
    def load_war_games_data(filepath):
        """Load war games results from JSON file."""
        filepath = Path(filepath)
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            st.error(f"Error loading War Games data: {e}")
            return None
    
    war_games_data = load_war_games_data(WAR_GAMES_FILE)
    
    if war_games_data is None:
        st.warning("⚠️ No War Games results found. Run simulations first:")
        st.code("python daemon/simulator/war_games_runner.py", language="bash")
        st.stop()
    
    # Extract metadata
    run_timestamp = war_games_data.get('run_timestamp', 'Unknown')
    total_campaigns = war_games_data.get('total_campaigns', 0)
    results = war_games_data.get('results', [])
    
    if not results:
        st.error("No campaign results found in war_games_results.json")
        st.stop()
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Display metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Campaigns", total_campaigns)
    with col2:
        st.metric("Last Run", run_timestamp.split('T')[0] if 'T' in run_timestamp else run_timestamp)
    with col3:
        unique_scenarios = results_df['campaign_name'].str.split(' - ').str[0].nunique()
        st.metric("Scenarios Tested", unique_scenarios)
    
    st.markdown("---")
    
    # --- LEADERBOARD ---
    st.header("🏆 Campaign Leaderboard")
    
    # Extract key metrics for display
    leaderboard = results_df[[
        'campaign_name', 'symbol', 'total_return_pct', 'win_rate', 
        'max_drawdown_pct', 'sharpe_ratio', 'total_trades'
    ]].copy()
    
    # Parse campaign name to extract scenario and param set
    leaderboard['scenario'] = leaderboard['campaign_name'].str.split(' - ').str[0]
    leaderboard['param_set'] = leaderboard['campaign_name'].str.split(' - ').str[-1]
    
    # Highlight best performer for each scenario (before reordering)
    best_by_scenario = leaderboard.loc[
        leaderboard.groupby('scenario')['total_return_pct'].idxmax()
    ]['campaign_name'].tolist()
    
    # Reorder columns for display (keep campaign_name for reference)
    display_cols = [
        'scenario', 'symbol', 'param_set', 'total_return_pct', 
        'win_rate', 'max_drawdown_pct', 'sharpe_ratio', 'total_trades'
    ]
    
    # Format for display
    leaderboard_display = leaderboard[display_cols].copy()
    leaderboard_display['total_return_pct'] = leaderboard_display['total_return_pct'].apply(lambda x: f"{x:.1f}%")
    leaderboard_display['win_rate'] = leaderboard_display['win_rate'].apply(lambda x: f"{x:.1%}")
    leaderboard_display['max_drawdown_pct'] = leaderboard_display['max_drawdown_pct'].apply(lambda x: f"{x:.1f}%")
    leaderboard_display['sharpe_ratio'] = leaderboard_display['sharpe_ratio'].apply(lambda x: f"{x:.2f}")
    
    st.dataframe(
        leaderboard_display,
        use_container_width=True,
        height=400
    )
    
    st.caption(f"✨ Best performers: {', '.join([c.split(' - ')[-1] for c in best_by_scenario[:3]])}")
    
    st.markdown("---")
    
    # --- VISUALIZATIONS ---
    st.header("📊 Performance Analysis")
    
    # Risk/Reward Scatter
    col_scatter, col_regime = st.columns(2)
    
    with col_scatter:
        st.subheader("Risk vs. Reward")
        
        fig_scatter = px.scatter(
            leaderboard,
            x='max_drawdown_pct',
            y='total_return_pct',
            color='param_set',
            symbol='symbol',
            size='total_trades',
            hover_data=['scenario', 'win_rate', 'sharpe_ratio'],
            title="Risk/Reward Profile (Target: Top-Left Quadrant)",
            labels={
                'max_drawdown_pct': 'Max Drawdown (%)',
                'total_return_pct': 'Total Return (%)'
            }
        )
        
        # Add quadrant lines
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_scatter.add_vline(x=leaderboard['max_drawdown_pct'].median(), line_dash="dash", line_color="gray", opacity=0.5)
        
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.caption("🎯 **Ideal**: High Return, Low Drawdown (Top-Left)")
    
    with col_regime:
        st.subheader("Regime Robustness")
        
        # Average return by param set across scenarios
        regime_perf = leaderboard.groupby(['scenario', 'param_set'])['total_return_pct'].mean().reset_index()
        
        fig_regime = px.bar(
            regime_perf,
            x='scenario',
            y='total_return_pct',
            color='param_set',
            barmode='group',
            title="Return % by Scenario (Averaged across symbols)",
            labels={
                'total_return_pct': 'Avg Return (%)',
                'scenario': 'Market Scenario'
            }
        )
        
        st.plotly_chart(fig_regime, use_container_width=True)
        
        st.caption("📈 **Insight**: Which param set is most robust across regimes?")
    
    st.markdown("---")
    
    # --- DRILL DOWN ---
    st.header("🔍 Campaign Drill-Down")
    
    selected_campaign = st.selectbox(
        "Select Campaign for Detailed Analysis:",
        options=results_df['campaign_name'].tolist(),
        index=0
    )
    
    # Get selected campaign data
    campaign_data = results_df[results_df['campaign_name'] == selected_campaign].iloc[0]
    
    # Display campaign overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Return", f"{campaign_data['total_return_pct']:.1f}%")
    with col2:
        st.metric("Win Rate", f"{campaign_data['win_rate']:.1%}")
    with col3:
        st.metric("Max Drawdown", f"{campaign_data['max_drawdown_pct']:.1f}%")
    with col4:
        st.metric("Sharpe Ratio", f"{campaign_data['sharpe_ratio']:.2f}")
    
    # Additional metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", campaign_data['total_trades'])
    with col2:
        st.metric("Winning Trades", campaign_data['winning_trades'])
    with col3:
        st.metric("Avg Win", f"{campaign_data['avg_win_pct']:.1f}%")
    with col4:
        st.metric("Avg Loss", f"{campaign_data['avg_loss_pct']:.1f}%")
    
    # Trade Log
    trades = campaign_data.get('trades', [])
    if trades:
        st.subheader("📋 Trade Log")
        
        trades_df = pd.DataFrame(trades)
        
        # Select columns to display
        display_cols = ['entry_date', 'exit_date', 'entry_price', 'exit_price', 'pnl_pct', 'reason', 'trust_score', 'forecast_confidence']
        available_cols = [c for c in display_cols if c in trades_df.columns]
        
        st.dataframe(
            trades_df[available_cols],
            use_container_width=True,
            height=300
        )
        
        # Trade timeline chart
        if 'entry_date' in trades_df.columns and 'pnl_pct' in trades_df.columns:
            st.subheader("📈 Trade Performance Over Time")
            
            trades_df['cumulative_return'] = (1 + trades_df['pnl_pct'] / 100).cumprod() - 1
            trades_df['cumulative_return_pct'] = trades_df['cumulative_return'] * 100
            
            fig_timeline = px.line(
                trades_df,
                x='entry_date',
                y='cumulative_return_pct',
                title="Cumulative Return Over Campaign Period",
                labels={'cumulative_return_pct': 'Cumulative Return (%)', 'entry_date': 'Date'}
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("No trade details available for this campaign")
    
    # Show raw parameters
    with st.expander("⚙️ Campaign Parameters"):
        st.json(campaign_data.get('params', {}))

else:
    # --- TRADE ANALYSIS MODE (ORIGINAL DASHBOARD) ---
    df = load_data(MEMORY_FILE)

    if df.empty:
        st.warning(f"No data found in {MEMORY_FILE}. Run the bot to generate memory!")
        st.stop()

    # Debug info in sidebar (after df is loaded)
    with st.sidebar.expander("🔍 Debug Info"):
        st.write(f"Total trades: {len(df)}")
        if 'post_mortem' in df.columns:
            pm_count = df['post_mortem'].notna().sum()
            st.write(f"Trades with post_mortem: {pm_count}")
            if pm_count > 0:
                # Show sample
                sample_pm = df[df['post_mortem'].notna()]['post_mortem'].iloc[0]
                if isinstance(sample_pm, dict):
                    st.write(f"Sample post_mortem keys: {list(sample_pm.keys())}")
        if 'outcome_category' in df.columns:
            cat_count = df['outcome_category'].notna().sum()
            st.write(f"Trades with outcome_category: {cat_count}")
            if cat_count > 0:
                st.write("Categories:", df['outcome_category'].value_counts().to_dict())
        # Show has_postmortem check result
        has_postmortem_check = (
            ('post_mortem' in df.columns and df['post_mortem'].notna().any()) or
            ('outcome_category' in df.columns and df['outcome_category'].notna().any())
        )
        st.write(f"has_postmortem check: {has_postmortem_check}")

    # --- KPI ROW ---
    col1, col2, col3, col4 = st.columns(4)

    # Calculate Metrics
    approvals = df[df['decision'] == "APPROVE"] if 'decision' in df.columns else pd.DataFrame()
    rejections = df[df['decision'] == "REJECT"] if 'decision' in df.columns else pd.DataFrame()

    # Hit Rate (Requires PnL to be populated)
    # Check if we have any non-null PnL values
    has_pnl = 'pnl' in df.columns and df['pnl'].notna().any()

    if has_pnl:
        # Filter approvals that have PnL values
        approvals_with_pnl = approvals[approvals['pnl'].notna()]
        if not approvals_with_pnl.empty:
            hit_rate = len(approvals_with_pnl[approvals_with_pnl['pnl'] > 0]) / len(approvals_with_pnl)
            avg_pnl = approvals_with_pnl['pnl'].sum()
        else:
            hit_rate = 0
            avg_pnl = 0
    
        # Filter rejections that have PnL values (for regret tracking)
        rejections_with_pnl = rejections[rejections['pnl'].notna()]
        if not rejections_with_pnl.empty:
            regret_count = len(rejections_with_pnl[rejections_with_pnl['pnl'] > 0])
            regret_rate = regret_count / len(rejections_with_pnl)
        else:
            regret_rate = 0
    else:
        hit_rate = 0
        regret_rate = 0
        avg_pnl = 0

    col1.metric("Hit Rate (Precision)", f"{hit_rate:.1%}" if has_pnl else "N/A", delta_color="normal")
    col2.metric("Regret Rate (FOMO)", f"{regret_rate:.1%}" if has_pnl else "N/A", delta_color="inverse")
    col3.metric("Total System PnL", f"${avg_pnl:.2f}" if has_pnl else "N/A")
    col4.metric("Total Trades", len(df))

    # --- CHARTS ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Decision Boundary")
        if 'trust_score' in df.columns and 'llm_confidence' in df.columns:
            # Filter out NaN values
            plot_df = df[df['trust_score'].notna() & df['llm_confidence'].notna()].copy()
        
            if not plot_df.empty:
                # Scatter plot: Trust Score vs LLM Confidence, colored by Outcome
                fig = px.scatter(
                    plot_df, 
                    x="trust_score", 
                    y="llm_confidence", 
                    color="decision",
                    symbol="outcome_type" if 'outcome_type' in plot_df.columns and plot_df['outcome_type'].notna().any() else None,
                    hover_data=["symbol", "rationale"] if 'rationale' in plot_df.columns else ["symbol"],
                    title="Did the LLM agree with the Trust Score?",
                    color_discrete_map={"APPROVE": "green", "REJECT": "red", "WAIT": "orange"}
                )
                fig.add_hline(y=0.75, line_dash="dash", annotation_text="Confidence Threshold", line_color="gray")
                fig.add_vline(x=0.6, line_dash="dash", annotation_text="Trust Threshold", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Insufficient data for scatter plot (missing trust_score or llm_confidence).")
        else:
            st.info("Insufficient data for scatter plot.")

    with c2:
        st.subheader("Recent Activity")
        if not approvals.empty and 'llm_confidence' in approvals.columns:
            # Get recent approvals
            recent_approvals = approvals.head(20).copy()
            if 'timestamp' in recent_approvals.columns:
                recent_approvals['timestamp'] = pd.to_datetime(recent_approvals['timestamp'], errors='coerce')
                recent_approvals = recent_approvals.sort_values('timestamp', ascending=False)
        
            fig2 = px.bar(
                recent_approvals, 
                x="symbol" if 'symbol' in recent_approvals.columns else recent_approvals.index, 
                y="llm_confidence", 
                color="symbol" if 'symbol' in recent_approvals.columns else None,
                title="Recent Approved Trades Confidence",
                labels={"llm_confidence": "LLM Confidence", "symbol": "Symbol"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No approvals yet or missing confidence data.")

    # --- RAW DATA ---
    st.subheader("Reasoning Logs")
    cols_to_show = ['timestamp', 'symbol', 'decision', 'llm_confidence', 'trust_score', 'rationale']
    available_cols = [col for col in cols_to_show if col in df.columns]

    if has_pnl and 'pnl' in df.columns:
        if 'pnl' not in available_cols:
            available_cols.insert(5, 'pnl')

    # Sort by timestamp if available
    sort_col = 'timestamp' if 'timestamp' in df.columns else None
    if sort_col:
        df_display = df[available_cols].sort_values('timestamp', ascending=False)
    else:
        df_display = df[available_cols]

    st.dataframe(
        df_display,
        use_container_width=True
    )

    # --- LESSONS LEARNED SECTION ---
    # Check for post-mortem data - look for either outcome_category column or post_mortem column
    has_postmortem = (
        ('post_mortem' in df.columns and df['post_mortem'].notna().any()) or
        ('outcome_category' in df.columns and df['outcome_category'].notna().any())
    )

    if has_postmortem:
        st.header("📚 Lessons Learned")
    
        # Filter trades with post-mortem data
        if 'outcome_category' in df.columns:
            postmortem_trades = df[df['outcome_category'].notna()].copy()
        elif 'post_mortem' in df.columns:
            # Extract outcome_category from post_mortem if not already extracted
            postmortem_trades = df[df['post_mortem'].notna()].copy()
            if 'outcome_category' not in postmortem_trades.columns:
                postmortem_trades['outcome_category'] = postmortem_trades['post_mortem'].apply(
                    lambda x: x.get('outcome_category') if isinstance(x, dict) else None
                )
        else:
            postmortem_trades = pd.DataFrame()
    
        if not postmortem_trades.empty:
            # Accuracy of Conviction Metric
            st.subheader("Accuracy of Conviction")
        
            # Calculate correlation between adjusted_confidence and actual outcome
            # Convert outcome to numeric: WIN=1, LOSS=-1, BREAKEVEN=0
            def outcome_to_numeric(outcome_str):
                if pd.isna(outcome_str):
                    return None
                outcome_upper = str(outcome_str).upper()
                if 'WIN' in outcome_upper or 'PROFIT' in outcome_upper:
                    return 1.0
                elif 'LOSS' in outcome_upper:
                    return -1.0
                else:
                    return 0.0
        
            postmortem_trades['outcome_numeric'] = postmortem_trades['postmortem_outcome'].apply(outcome_to_numeric)
        
            # Filter for trades with both adjusted_confidence and outcome_numeric
            valid_for_correlation = postmortem_trades[
                postmortem_trades['adjusted_confidence'].notna() & 
                postmortem_trades['outcome_numeric'].notna()
            ]
        
            if len(valid_for_correlation) > 1:
                correlation = valid_for_correlation['adjusted_confidence'].corr(valid_for_correlation['outcome_numeric'])
                if pd.notna(correlation):
                    st.metric(
                        "Confidence-Outcome Correlation",
                        f"{correlation:.3f}",
                        help="Correlation between adjusted_confidence and actual outcome. Higher = better calibration."
                    )
                else:
                    st.info("Insufficient data to calculate correlation.")
            else:
                st.info("Need at least 2 trades with both adjusted_confidence and outcome to calculate correlation.")
        
            # Hall of Shame/Fame
            col_shame, col_fame = st.columns(2)
        
            with col_shame:
                st.subheader("🏆 Hall of Shame (Model Hallucinations)")
                hallucinations = postmortem_trades[
                    postmortem_trades['outcome_category'] == 'MODEL_HALLUCINATION'
                ].copy()
            
                if not hallucinations.empty:
                    shame_cols = ['timestamp', 'symbol', 'root_cause', 'lesson_learned', 'pnl']
                    available_shame = [c for c in shame_cols if c in hallucinations.columns]
                    st.dataframe(
                        hallucinations[available_shame].sort_values('timestamp', ascending=False) if 'timestamp' in hallucinations.columns else hallucinations[available_shame],
                        use_container_width=True,
                        height=300
                    )
                    st.caption(f"Total: {len(hallucinations)} trades")
                else:
                    st.info("No model hallucinations detected. 🎉")
        
            with col_fame:
                st.subheader("🎲 Hall of Fame (Lucky Wins)")
                lucky_wins = postmortem_trades[
                    postmortem_trades['outcome_category'] == 'LUCK'
                ].copy()
            
                if not lucky_wins.empty:
                    fame_cols = ['timestamp', 'symbol', 'root_cause', 'lesson_learned', 'pnl']
                    available_fame = [c for c in fame_cols if c in lucky_wins.columns]
                    st.dataframe(
                        lucky_wins[available_fame].sort_values('timestamp', ascending=False) if 'timestamp' in lucky_wins.columns else lucky_wins[available_fame],
                        use_container_width=True,
                        height=300
                    )
                    st.caption(f"Total: {len(lucky_wins)} trades")
                else:
                    st.info("No lucky wins detected.")
        
            # Breakdown by Outcome Category
            st.subheader("Outcome Category Breakdown")
            category_counts = postmortem_trades['outcome_category'].value_counts()
        
            if not category_counts.empty:
                fig_categories = px.bar(
                    x=category_counts.index,
                    y=category_counts.values,
                    title="Distribution of Outcome Categories",
                    labels={'x': 'Outcome Category', 'y': 'Count'}
                )
                st.plotly_chart(fig_categories, use_container_width=True)
            
                # Show summary table
                category_summary = postmortem_trades.groupby('outcome_category').agg({
                    'pnl': ['count', 'mean', 'sum'],
                    'adjusted_confidence': 'mean'
                }).round(3)
                st.dataframe(category_summary, use_container_width=True)
        else:
            st.info("No post-mortem data available. Run the reviewer daemon to generate analysis.")
    else:
        st.info("💡 Post-mortem analysis not yet available. Run `python daemon/reviewer.py` to generate lessons learned.")

