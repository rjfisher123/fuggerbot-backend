# FuggerBot Research Report: final_hardened

## Metadata

- **Report ID**: final_hardened
- **Strategy Version**: 1.0.0
- **Research Loop Version**: 2.0
- **Simulator Commit Hash**: unknown
- **Data Fingerprint**: 09edd5ed592f59b3
- **Generated At**: 2025-12-24T13:36:25.863266
- **Total Insights**: 1
- **Total Scenarios**: 36

## Executive Summary

This report analyzes 36 scenarios with an average return of 0.18% (median: 0.05%, range: -4.34% to 5.58%). Data covers 2021-01-01 to 2023-12-31. Best scenario: ETH-USD (5.58% return). Worst scenario: BTC-USD (-4.34% return). Analysis identified 1 total insights, including 1 high-confidence findings. Top insights: winning_patt... (conf: 0.75). Regime coverage: 3 of 3 regime combinations tested.

## Performance Overview

- **Total Scenarios**: 36
- **Average Return**: 0.18%
- **Return Range**: -4.34% to 5.58%
- **Average Sharpe Ratio**: -1.14 (valid values only)
- **Median Sharpe Ratio**: 0.00
- **Sharpe Ratio Range (p10-p90)**: -1.04 to 0.45
- **Average Max Drawdown**: 1.07%
- **Average Win Rate**: 39.71%

### Top 5 Scenarios (by Return)

| Scenario ID | Symbol | Return % | Sharpe | Drawdown % | Win Rate | Trades |
|-------------|--------|----------|--------|------------|----------|--------|
| ETH-USD_c93d... | ETH-USD | 5.58% | 0.48 | 1.30% | 62.50% | 8 |
| ETH-USD_3ac8... | ETH-USD | 3.91% | 0.59 | 0.80% | 71.43% | 7 |
| NVDA_c93db46... | NVDA | 3.24% | 0.45 | 0.85% | 71.43% | 7 |
| NVDA_3ac8e7f... | NVDA | 2.54% | 0.45 | 0.67% | 71.43% | 7 |
| ETH-USD_a923... | ETH-USD | 1.00% | 0.43 | 0.64% | 50.00% | 6 |

### Bottom 5 Scenarios (by Return)

| Scenario ID | Symbol | Return % | Sharpe | Drawdown % | Win Rate | Trades |
|-------------|--------|----------|--------|------------|----------|--------|
| BTC-USD_3ac8... | BTC-USD | -4.34% | -2.86 | 4.34% | 0.00% | 5 |
| BTC-USD_c93d... | BTC-USD | -3.02% | -0.49 | 3.40% | 33.33% | 6 |
| MSFT_c93db46... | MSFT | -1.53% | -1.04 | 1.53% | 33.33% | 3 |
| MSFT_3ac8e7f... | MSFT | -1.23% | -1.46 | 1.23% | 0.00% | 3 |
| NVDA_c93db46... | NVDA | -1.19% | -0.48 | 1.38% | 33.33% | 3 |

### Per-Symbol Summary

| Symbol | Scenarios | Avg Return % | Median Return % | Avg Drawdown % | Avg Win Rate |
|--------|-----------|--------------|-----------------|----------------|--------------|
| BTC-USD | 9.0 | -0.76% | -0.17% | 1.80% | 38.27% |
| ETH-USD | 9.0 | 1.34% | 0.66% | 1.28% | 46.16% |
| MSFT | 9.0 | -0.21% | 0.00% | 0.50% | 40.00% |
| NVDA | 9.0 | 0.33% | -0.17% | 0.69% | 34.39% |

### Per-Regime Summary (Top 10 by Scenario Count)

| Regime ID | Scenarios | Avg Return % | Median Return % | Avg Drawdown % | Avg Win Rate |
|-----------|-----------|--------------|-----------------|----------------|--------------|
| medium_up_normal_neutral... | 12.0 | 0.75% | 0.55% | 0.59% | 48.60% |
| low_up_normal_easing... | 12.0 | 0.65% | 0.10% | 0.96% | 46.81% |
| high_down_normal_tightening... | 12.0 | -0.87% | -0.17% | 1.65% | 23.71% |

## Confirmed Insights

### Preliminary Insights (Insufficient Evidence)

*Preliminary status: <3 scenarios OR <2 regime coverage (may have high confidence but lacks evidence breadth)*

**winning_pattern_1766564060.275516** (winning_pattern, Confidence: 0.75, Status: ⚠️ PRELIMINARY)

Trust threshold >0.65 improves drawdown in volatile regimes

- **Supporting scenarios**: 1
- **Regime coverage count**: 0


## Known Unknowns

- 51 regime combinations remain unexplored

## Failure Boundaries

*No failure boundaries detected.*
## Regime Coverage

| Regime ID | Description | Scenarios | Coverage % |
|-----------|-------------|-----------|------------|
| medium_up_normal_neutral | medium vol, up trend, normal liquidity, neutral ma | 12 | 33.3% |
| low_up_normal_easing | low vol, up trend, normal liquidity, easing macro | 12 | 33.3% |
| high_down_normal_tightening | high vol, down trend, normal liquidity, tightening | 12 | 33.3% |

## Recommended Experiments (Top 3)

### 1. Unexplored Regime: low_up_normal_tightening

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, up trend, normal liquidity, tightening macro

**Reasoning**: Regime low_up_normal_tightening has not been tested yet - high information value

### 2. Unexplored Regime: low_up_normal_neutral

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, up trend, normal liquidity, neutral macro

**Reasoning**: Regime low_up_normal_neutral has not been tested yet - high information value

### 3. Unexplored Regime: low_up_stressed_easing

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, up trend, stressed liquidity, easing macro

**Reasoning**: Regime low_up_stressed_easing has not been tested yet - high information value

## Experiment Backlog (Deferred)

*7 additional proposals deferred due to lower marginal information gain*

### Regime Test (7 proposals)

- **low_up_stressed_tightening** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_up_stressed_neutral** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_sideways_normal_easing** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_sideways_normal_tightening** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_sideways_normal_neutral** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_sideways_stressed_easing** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3
- **low_sideways_stressed_tightening** (Info Gain: 0.80, Priority: 7/10)
  - Reason for deferral: Lower marginal information gain compared to top 3

## Appendices

### Scenario IDs

- `BTC-USD_c93db461608a_2021-01-01_2021-12-31`
- `BTC-USD_3ac8e7f4f1bd_2021-01-01_2021-12-31`
- `BTC-USD_a92306670f74_2021-01-01_2021-12-31`
- `ETH-USD_c93db461608a_2021-01-01_2021-12-31`
- `ETH-USD_3ac8e7f4f1bd_2021-01-01_2021-12-31`
- `ETH-USD_a92306670f74_2021-01-01_2021-12-31`
- `NVDA_c93db461608a_2021-01-01_2021-12-31`
- `NVDA_3ac8e7f4f1bd_2021-01-01_2021-12-31`
- `NVDA_a92306670f74_2021-01-01_2021-12-31`
- `MSFT_c93db461608a_2021-01-01_2021-12-31`
- `MSFT_3ac8e7f4f1bd_2021-01-01_2021-12-31`
- `MSFT_a92306670f74_2021-01-01_2021-12-31`
- `BTC-USD_c93db461608a_2022-01-01_2022-12-31`
- `BTC-USD_3ac8e7f4f1bd_2022-01-01_2022-12-31`
- `BTC-USD_a92306670f74_2022-01-01_2022-12-31`
- `ETH-USD_c93db461608a_2022-01-01_2022-12-31`
- `ETH-USD_3ac8e7f4f1bd_2022-01-01_2022-12-31`
- `ETH-USD_a92306670f74_2022-01-01_2022-12-31`
- `NVDA_c93db461608a_2022-01-01_2022-12-31`
- `NVDA_3ac8e7f4f1bd_2022-01-01_2022-12-31`

*... and 16 more scenarios*

### Sensitivity Analysis Summary

### Metric Definitions

#### Sharpe Ratio

Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Standard Deviation

Calculation Details:
- Return periodicity: Daily returns
- Annualization factor: Not applied (reported as daily Sharpe)
- Risk-free rate assumption: 0% (excess return = raw return)
- Invalid values: Scenarios with zero variance (constant returns) produce invalid Sharpe ratios (NaN or ±inf) and are excluded from all statistics
- Validity check: Only finite values (not NaN, not ±inf) are included in mean, median, and percentile calculations
