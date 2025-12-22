"""
Historical Macro Regime Library.

A database of historical macroeconomic regimes and their characteristics.
Used to provide context for trading decisions and market analysis.
"""
from datetime import datetime
from typing import List

from context.schemas import MacroRegime, RegimeType


# Historical Macro Regimes Database
HISTORICAL_REGIMES: List[MacroRegime] = [
    # Entry 1: Fed QE4 2020
    MacroRegime(
        id="FED_QE4_2020",
        name="Fed QE4 - COVID Response",
        regime_type=RegimeType.MONETARY_POLICY,
        start_date=datetime(2020, 3, 15),
        end_date=datetime(2022, 3, 15),
        description=(
            "Federal Reserve launched unprecedented quantitative easing program (QE4) "
            "in response to COVID-19 pandemic. Zero interest rate policy (ZIRP) maintained, "
            "massive asset purchases, and emergency lending facilities. "
            "Unprecedented fiscal stimulus combined with monetary accommodation created "
            "liquidity-driven market rally."
        ),
        trigger_events=[
            "COVID-19 declared global pandemic (March 2020)",
            "Fed cuts rates to 0-0.25% (March 15, 2020)",
            "Fed announces unlimited QE (March 23, 2020)",
            "CARES Act passed ($2.2T fiscal stimulus)",
            "Fed balance sheet expands from $4T to $9T"
        ],
        macro_conditions={
            "fed_funds_rate": 0.0,
            "inflation": 1.4,  # Initially low, then rising
            "unemployment": 14.8,  # Peak in April 2020
            "gdp_growth": -3.4,  # 2020 annual
            "fed_balance_sheet": 9000000000000,  # ~$9T
            "money_supply_m2_growth": 25.0,  # Massive expansion
            "real_rates": -2.0  # Deeply negative
        },
        market_behavior=[
            "Risk assets rallied sharply (S&P 500 +68% from March 2020 low)",
            "Growth stocks massively outperformed value",
            "Tech stocks led the rally (FAANG, cloud, SaaS)",
            "Bond yields collapsed to historic lows",
            "Gold and Bitcoin surged as inflation hedge",
            "Dollar weakened initially, then recovered",
            "Volatility spiked then normalized",
            "IPO and SPAC boom",
            "Meme stock phenomenon emerged"
        ],
        embedding_hint=(
            "Period of extreme monetary and fiscal accommodation. Zero rates, massive QE, "
            "unprecedented liquidity. Growth stocks, tech, and risk assets soared. "
            "Negative real rates drove asset price inflation. High correlation between "
            "liquidity and market performance."
        )
    ),
    
    # Entry 2: Inflation Shock 2022
    MacroRegime(
        id="INFLATION_SHOCK_2022",
        name="Inflation Shock & Fed Hiking Cycle",
        regime_type=RegimeType.MONETARY_POLICY,
        start_date=datetime(2022, 3, 16),
        end_date=datetime(2023, 10, 31),
        description=(
            "Aggressive Federal Reserve rate hiking cycle to combat persistent inflation. "
            "Fed funds rate increased from 0% to 5.25% in fastest hiking cycle since 1980s. "
            "Inflation peaked at 9.1% (June 2022), driven by supply chain disruptions, "
            "energy shocks, and excess demand from previous stimulus. "
            "Quantitative tightening (QT) began, reversing years of QE."
        ),
        trigger_events=[
            "Fed raises rates 0.25% (March 16, 2022) - first hike since 2018",
            "Inflation reaches 8.5% (March 2022)",
            "Fed signals aggressive tightening path",
            "Inflation peaks at 9.1% (June 2022)",
            "Fed implements 75bp hikes (June, July, September, November 2022)",
            "QT begins (June 2022) - $95B/month runoff",
            "Fed funds rate reaches 5.25% (July 2023)"
        ],
        macro_conditions={
            "fed_funds_rate": 5.25,  # Peak
            "inflation": 9.1,  # Peak (June 2022)
            "core_inflation": 6.6,  # Peak
            "unemployment": 3.5,  # Very low
            "gdp_growth": 2.1,  # Slowing
            "real_rates": 2.0,  # Positive and rising
            "dollar_index": 114.0,  # Strong dollar
            "oil_price": 120.0,  # High energy prices
            "fed_balance_sheet": 8000000000000  # Shrinking via QT
        },
        market_behavior=[
            "Cash is king, high duration assets crushed",
            "Bonds experienced worst year since 1970s",
            "Growth stocks collapsed (ARKK -67% peak to trough)",
            "Value stocks outperformed growth",
            "Dollar surged to 20-year highs",
            "Commodities initially rallied then corrected",
            "Real estate and REITs underperformed",
            "Crypto crashed (Bitcoin -77% from peak)",
            "Volatility increased across all asset classes",
            "Defensive sectors (utilities, staples) held up better",
            "International markets underperformed (strong dollar)",
            "High yield credit spreads widened"
        ],
        embedding_hint=(
            "Period of aggressive monetary tightening with high inflation. "
            "Rapid rate hikes from 0% to 5.25%. Cash and short-duration assets outperformed. "
            "Long-duration assets (bonds, growth stocks) crushed. Strong dollar environment. "
            "Value outperformed growth. High volatility, defensive positioning favored."
        )
    ),
    
    # Entry 3: AI Boom 2023
    MacroRegime(
        id="AI_BOOM_2023",
        name="AI Boom & Tech Capex Surge",
        regime_type=RegimeType.BOOM,
        start_date=datetime(2023, 11, 1),
        end_date=None,  # Ongoing
        description=(
            "Nvidia breakout and massive capital expenditure surge in Technology sector. "
            "Generative AI revolution drives unprecedented demand for compute infrastructure. "
            "Semiconductor and AI-related stocks experience explosive growth. "
            "Market becomes highly concentrated in a narrow set of mega-cap tech stocks. "
            "AI infrastructure buildout creates massive capex cycle."
        ),
        trigger_events=[
            "ChatGPT launch (November 2022) - AI awareness explosion",
            "Nvidia Q4 2023 earnings beat expectations massively",
            "Nvidia breaks $1T market cap (May 2023)",
            "Major tech companies announce massive AI capex plans",
            "OpenAI, Anthropic raise billions in funding",
            "Enterprise AI adoption accelerates",
            "Semiconductor equipment orders surge",
            "Data center demand explodes"
        ],
        macro_conditions={
            "fed_funds_rate": 5.25,  # Elevated but stable
            "inflation": 3.2,  # Moderating
            "unemployment": 3.7,  # Low but rising slightly
            "gdp_growth": 2.5,  # Solid growth
            "tech_capex_growth": 40.0,  # Massive increase
            "semiconductor_demand": "extreme",
            "ai_investment": "unprecedented",
            "market_concentration": "high"  # Top 7 stocks = 30%+ of S&P 500
        },
        market_behavior=[
            "Narrow breadth, high concentration in Semi/AI",
            "Nvidia, AMD, Broadcom, TSMC lead the rally",
            "Mega-cap tech (MSFT, GOOGL, META, AMZN) surge on AI theme",
            "S&P 500 driven by top 7 stocks",
            "Small caps and value underperform",
            "International markets lag (US tech dominance)",
            "Semiconductor equipment stocks soar",
            "Cloud infrastructure stocks rally",
            "AI application stocks experience volatility",
            "Traditional sectors (energy, financials) lag",
            "Market breadth deteriorates",
            "High correlation within tech sector"
        ],
        embedding_hint=(
            "AI-driven boom with massive tech capex cycle. Nvidia and semiconductor stocks "
            "leading. Narrow market breadth, extreme concentration in AI/semi names. "
            "Mega-cap tech benefiting from AI infrastructure demand. Traditional sectors "
            "underperforming. High valuations in AI-related stocks. Market driven by "
            "expectations of AI transformation across industries."
        )
    )
]


def get_active_regimes(date: datetime = None) -> List[MacroRegime]:
    """
    Get all regimes that are active at the given date.
    
    Args:
        date: Date to check (defaults to current date/time)
        
    Returns:
        List of active MacroRegime objects
    """
    if date is None:
        date = datetime.now()
    
    return [regime for regime in HISTORICAL_REGIMES if regime.is_active(date)]


def get_regime_by_id(regime_id: str) -> MacroRegime:
    """
    Get a regime by its ID.
    
    Args:
        regime_id: The regime ID to look up
        
    Returns:
        MacroRegime object if found
        
    Raises:
        ValueError: If regime ID not found
    """
    for regime in HISTORICAL_REGIMES:
        if regime.id == regime_id:
            return regime
    
    raise ValueError(f"Regime with ID '{regime_id}' not found")


def get_regimes_by_type(regime_type: RegimeType) -> List[MacroRegime]:
    """
    Get all regimes of a specific type.
    
    Args:
        regime_type: The RegimeType to filter by
        
    Returns:
        List of MacroRegime objects matching the type
    """
    return [regime for regime in HISTORICAL_REGIMES if regime.regime_type == regime_type]







