import yfinance as yf
import requests

def get_stock_price(symbol: str):
    """Fetch current price for a stock or ETF."""
    try:
        data = yf.Ticker(symbol).history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None

def get_crypto_price(symbol: str):
    """Fetch current crypto price (e.g., BTC, ETH) in USD using CoinGecko."""
    try:
        sym_map = {"BTC": "bitcoin", "ETH": "ethereum"}
        coin = sym_map.get(symbol.upper(), symbol.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get(coin, {}).get("usd")
    except Exception:
        pass
    return None

def get_price(symbol: str):
    """Auto-detect whether asset is stock or crypto."""
    if symbol.upper() in ["BTC", "ETH"]:
        return get_crypto_price(symbol)
    return get_stock_price(symbol)