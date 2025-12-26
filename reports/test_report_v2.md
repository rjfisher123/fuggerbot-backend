# FuggerBot Research Report: test_report_v2

## Metadata

- **Report ID**: test_report_v2
- **Strategy Version**: 1.0.0
- **Research Loop Version**: 2.0
- **Simulator Commit Hash**: unknown
- **Data Fingerprint**: 09edd5ed592f59b3
- **Generated At**: 2025-12-24T11:05:32.507843
- **Total Insights**: 1
- **Total Scenarios**: 36

## Executive Summary

This report analyzes 36 scenarios with an average return of 0.18% (range: -4.34% to 5.58%). Analysis identified 1 total insights, including 1 high-confidence findings. Regime coverage analysis shows 3 of 3 regime combinations have been tested.

## Performance Overview

- **Total Scenarios**: 36
- **Average Return**: 0.18%
- **Return Range**: -4.34% to 5.58%
- **Average Sharpe Ratio**: -1.14
- **Average Max Drawdown**: 1.07%
- **Average Win Rate**: 39.71%

## Confirmed Insights

### Strong Insights (Confidence ≥ 0.7)

**winning_pattern_1766564060.275516** (winning_pattern, Confidence: 0.75)

Trust threshold >0.65 improves drawdown in volatile regimes

- Supporting scenarios: 1


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

## Recommended Experiments

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

### 4. Unexplored Regime: low_up_stressed_tightening

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, up trend, stressed liquidity, tightening macro

**Reasoning**: Regime low_up_stressed_tightening has not been tested yet - high information value

### 5. Unexplored Regime: low_up_stressed_neutral

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, up trend, stressed liquidity, neutral macro

**Reasoning**: Regime low_up_stressed_neutral has not been tested yet - high information value

### 6. Unexplored Regime: low_sideways_normal_easing

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, sideways trend, normal liquidity, easing macro

**Reasoning**: Regime low_sideways_normal_easing has not been tested yet - high information value

### 7. Unexplored Regime: low_sideways_normal_tightening

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, sideways trend, normal liquidity, tightening macro

**Reasoning**: Regime low_sideways_normal_tightening has not been tested yet - high information value

### 8. Unexplored Regime: low_sideways_normal_neutral

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, sideways trend, normal liquidity, neutral macro

**Reasoning**: Regime low_sideways_normal_neutral has not been tested yet - high information value

### 9. Unexplored Regime: low_sideways_stressed_easing

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, sideways trend, stressed liquidity, easing macro

**Reasoning**: Regime low_sideways_stressed_easing has not been tested yet - high information value

### 10. Unexplored Regime: low_sideways_stressed_tightening

**Type**: regime_test  
**Expected Info Gain**: 0.80  
**Priority**: 7/10

Test in unexplored regime: low vol, sideways trend, stressed liquidity, tightening macro

**Reasoning**: Regime low_sideways_stressed_tightening has not been tested yet - high information value

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
