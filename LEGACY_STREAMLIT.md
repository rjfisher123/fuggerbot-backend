# Legacy Streamlit UI

The Streamlit dashboard (`dash/streamlit_app.py`) powered the original FuggerBot UI.  
FastAPI now replaces it with `/forecast`, `/backtest`, `/triggers`, `/trades`, and `/portfolio`.

## When to use Streamlit
- Historical reference for the old UI
- Visual experiments that haven’t been migrated yet

## How to launch (optional)
```bash
pip install streamlit plotly
streamlit run dash/streamlit_app.py
```

> ⚠️ Streamlit is no longer maintained or required for day-to-day usage.  
> Use the FastAPI dashboard (`uvicorn main:app --reload`) for production workflows.





