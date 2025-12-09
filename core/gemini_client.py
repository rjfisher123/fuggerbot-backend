"""Google Gemini AI client for FuggerBot."""
import os
import json
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from .logger import logger

# Lazy import for google-generativeai
GEMINI_AVAILABLE = False
_gemini_imported = False

def _import_gemini():
    """Lazy import of google-generativeai."""
    global GEMINI_AVAILABLE, _gemini_imported
    if _gemini_imported:
        return GEMINI_AVAILABLE
    
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
        _gemini_imported = True
        return True
    except ImportError:
        GEMINI_AVAILABLE = False
        _gemini_imported = True
        logger.warning("google-generativeai not installed. Install with: pip install google-generativeai")
        return False

# Load environment variables
load_dotenv()


class GeminiClient:
    """Client for interacting with Google Gemini AI."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-pro"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (default: "gemini-pro")
        """
        if not _import_gemini():
            raise ImportError("google-generativeai is not installed. Install with: pip install google-generativeai")
        
        import google.generativeai as genai
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it in your .env file or pass it as a parameter.")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini client initialized with model: {model_name}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: The prompt to send to Gemini
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Generated text response
        """
        try:
            response = self.model.generate_content(prompt, **kwargs)
            return response.text
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            raise
    
    def analyze_trade_opportunity(
        self, 
        symbol: str, 
        current_price: float, 
        trigger_price: float,
        market_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze a trade opportunity using Gemini AI.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            trigger_price: Trigger price from config
            market_data: Optional additional market data
        
        Returns:
            Analysis dictionary with recommendation and reasoning
        """
        prompt = f"""Analyze this trade opportunity:

Symbol: {symbol}
Current Price: ${current_price:.2f}
Trigger Price: ${trigger_price:.2f}
Price Difference: {((current_price - trigger_price) / trigger_price * 100):.2f}%

"""
        if market_data:
            prompt += f"Additional Market Data: {market_data}\n\n"
        
        prompt += """Provide a brief analysis:
1. Is this a good entry point? (Yes/No/Maybe)
2. Brief reasoning (1-2 sentences)
3. Risk level (Low/Medium/High)
4. Recommended action (Buy/Pass/Wait)

Format your response as:
RECOMMENDATION: [Yes/No/Maybe]
REASONING: [your reasoning]
RISK: [Low/Medium/High]
ACTION: [Buy/Pass/Wait]
"""
        
        try:
            response_text = self.generate_text(prompt, temperature=0.7)
            
            # Parse response
            analysis = {
                "symbol": symbol,
                "current_price": current_price,
                "trigger_price": trigger_price,
                "raw_response": response_text,
                "recommendation": "Unknown",
                "reasoning": "",
                "risk": "Unknown",
                "action": "Unknown"
            }
            
            # Simple parsing (can be improved)
            lines = response_text.split("\n")
            for line in lines:
                if "RECOMMENDATION:" in line.upper():
                    analysis["recommendation"] = line.split(":", 1)[1].strip()
                elif "REASONING:" in line.upper():
                    analysis["reasoning"] = line.split(":", 1)[1].strip()
                elif "RISK:" in line.upper():
                    analysis["risk"] = line.split(":", 1)[1].strip()
                elif "ACTION:" in line.upper():
                    analysis["action"] = line.split(":", 1)[1].strip()
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing trade opportunity: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "recommendation": "Error",
                "action": "Pass"
            }
    
    def generate_trade_summary(self, trade_details: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of a trade using AI.
        
        Args:
            trade_details: Dictionary with trade information
        
        Returns:
            Formatted trade summary
        """
        prompt = f"""Create a concise, professional trade summary for this transaction:

Trade Details:
{json.dumps(trade_details, indent=2)}

Generate a 2-3 sentence summary that explains:
- What trade was executed
- Why it was triggered
- Key details (symbol, quantity, price)

Keep it professional and concise.
"""
        
        try:
            return self.generate_text(prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Error generating trade summary: {e}")
            return f"Trade executed: {trade_details.get('symbol', 'N/A')} {trade_details.get('action', 'N/A')} {trade_details.get('quantity', 0)} shares"


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client(api_key: Optional[str] = None, model_name: str = "gemini-pro") -> GeminiClient:
    """
    Get or create a singleton Gemini client instance.
    
    Args:
        api_key: Optional API key (uses env var if not provided)
        model_name: Model to use (default: "gemini-pro")
    
    Returns:
        GeminiClient instance
    """
    global _gemini_client
    
    if _gemini_client is None:
        _gemini_client = GeminiClient(api_key=api_key, model_name=model_name)
    
    return _gemini_client

