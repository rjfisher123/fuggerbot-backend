# Production Setup Guide

## Overview

The system is now configured for production use with OpenRouter API integration and centralized settings management.

## Configuration Files

### 1. `.env` File (Required)

Create a `.env` file in the project root with the following variables:

```bash
# OpenRouter / DeepSeek Configuration
OPENROUTER_API_KEY=your_actual_api_key_here
DEEPSEEK_MODEL=deepseek/deepseek-r1
ENV_STATE=prod
```

**Important:**
- The `.env` file is already in `.gitignore` and will not be committed
- Copy `env_template.txt` to `.env` and fill in your actual values
- Get your OpenRouter API key from: https://openrouter.ai/

### 2. Settings System

The application uses `config/settings.py` with pydantic-settings for:
- **Type-safe configuration** with validation
- **Clear error messages** if API key is missing
- **Environment-aware** (dev/prod modes)
- **Automatic loading** from `.env` file

## Usage

### Basic Usage

```python
from config import get_settings
from reasoning.engine import get_deepseek_engine

# Settings are automatically loaded from .env
settings = get_settings()

# Engine automatically uses settings
engine = get_deepseek_engine()

# Or explicitly override
engine = get_deepseek_engine(
    api_key="custom-key",
    model_name="deepseek/deepseek-r1"
)
```

### Testing Settings

Run the test script to verify your configuration:

```bash
python test_settings.py
```

### Running Evaluation with Real LLM

1. Set `USE_REAL_LLM = True` in `tests/evaluate_system.py`
2. Ensure your `.env` file has `OPENROUTER_API_KEY` set
3. Run the evaluation:

```bash
python tests/evaluate_system.py
```

## OpenRouter Integration

The system is configured to use OpenRouter API which provides access to DeepSeek models:

- **Base URL**: `https://openrouter.ai/api/v1`
- **Model Format**: `deepseek/deepseek-r1` (or other DeepSeek models)
- **API Key**: Your OpenRouter API key

### Supported Models

- `deepseek/deepseek-r1` (default, reasoning model)
- `deepseek/deepseek-chat` (chat model)
- Other models available on OpenRouter

## Environment States

- **`ENV_STATE=dev`**: Development mode (default)
  - More verbose logging
  - Relaxed error handling
  
- **`ENV_STATE=prod`**: Production mode
  - Optimized logging
  - Strict error handling
  - Use `settings.is_production` to check

## Error Handling

The settings system provides clear error messages:

```python
# If API key is missing:
ValueError: ❌ OPENROUTER_API_KEY is required but not set or invalid.

To fix this:
1. Create a .env file in the project root (or copy env_template.txt)
2. Add: OPENROUTER_API_KEY=your_actual_api_key_here
3. Get your API key from: https://openrouter.ai/
```

## Security Notes

- ✅ `.env` file is in `.gitignore` (never committed)
- ✅ API keys are validated (no placeholder values)
- ✅ Safe string representation (API keys never exposed in logs)
- ✅ Type-safe configuration prevents runtime errors

## Next Steps

1. ✅ Create `.env` file with your OpenRouter API key
2. ✅ Test settings: `python test_settings.py`
3. ✅ Run evaluation: `python tests/evaluate_system.py`
4. ✅ Integrate into your trading workflow

## Troubleshooting

### "API key not found" error
- Check that `.env` file exists in project root
- Verify `OPENROUTER_API_KEY` is set (not a placeholder)
- Run `python test_settings.py` to diagnose

### "Invalid model" error
- Check `DEEPSEEK_MODEL` in `.env`
- Verify model name format: `deepseek/deepseek-r1`
- Check OpenRouter docs for available models

### Settings not loading
- Ensure `pydantic-settings>=2.0.0` is installed: `pip install -r requirements.txt`
- Check that `.env` file encoding is UTF-8
- Verify file is in project root (same directory as `main.py`)








