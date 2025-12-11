# Gemini AI Integration Setup

This guide will help you connect Google Gemini AI to FuggerBot for AI-powered trade analysis and decision making.

## Step 1: Get a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey) or [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Create a new API key:
   - In Google AI Studio: Click "Get API Key" → "Create API Key"
   - In Google Cloud: Navigate to "APIs & Services" → "Credentials" → "Create Credentials" → "API Key"
4. Copy your API key (it will look like: `AIza...`)

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `google-generativeai`, which is the Python SDK for Gemini.

## Step 3: Configure Environment Variables

Add your Gemini API key to your `.env` file:

```bash
# Google Gemini AI
GEMINI_API_KEY=your_actual_api_key_here
```

Replace `your_actual_api_key_here` with the API key you obtained in Step 1.

## Step 4: Test the Connection

You can test the Gemini connection in Python:

```python
from core.gemini_client import get_gemini_client

# Initialize client (uses GEMINI_API_KEY from .env)
client = get_gemini_client()

# Test with a simple prompt
response = client.generate_text("Hello, Gemini!")
print(response)
```

Or use it in your code:

```python
from core import get_gemini_client

# Analyze a trade opportunity
client = get_gemini_client()
analysis = client.analyze_trade_opportunity(
    symbol="AAPL",
    current_price=150.00,
    trigger_price=145.00
)

print(f"Recommendation: {analysis['recommendation']}")
print(f"Action: {analysis['action']}")
print(f"Reasoning: {analysis['reasoning']}")
```

## Available Features

The Gemini client provides:

1. **`generate_text(prompt)`** - General text generation
2. **`analyze_trade_opportunity(symbol, current_price, trigger_price)`** - AI-powered trade analysis
3. **`generate_trade_summary(trade_details)`** - Generate human-readable trade summaries

## Model Options

By default, the client uses `gemini-pro`. You can specify a different model:

```python
client = get_gemini_client(model_name="gemini-pro-vision")  # For image analysis
```

Available models:
- `gemini-pro` - General purpose (default)
- `gemini-pro-vision` - For image and text analysis

## Troubleshooting

**Error: "GEMINI_API_KEY not found"**
- Make sure you've created a `.env` file in the project root
- Verify the API key is set correctly: `GEMINI_API_KEY=your_key_here`
- Restart your application after adding the key

**Error: "google-generativeai not installed"**
- Run: `pip install google-generativeai`
- Or: `pip install -r requirements.txt`

**Error: "API key invalid"**
- Verify your API key is correct
- Check if Gemini API is enabled in your Google Cloud project
- Make sure you haven't exceeded API quotas

## Security Notes

- **Never commit your `.env` file** to version control
- Keep your API key secret
- Consider using environment-specific keys for development vs production
- Monitor your API usage in Google Cloud Console






