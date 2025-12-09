# Troubleshooting Guide

## Dashboard Appears Hung

### Quick Fixes (Try in Order):

1. **Refresh the Page**
   - Press `Cmd+R` (Mac) or `Ctrl+R` (Windows/Linux)
   - Or click the browser refresh button

2. **Check the FastAPI Terminal**
   - Look at the terminal running `uvicorn main:app --reload`
   - Copy any red error messages when asking for help

3. **Restart FastAPI**
   ```bash
   pkill -f uvicorn  # or Ctrl+C
   uvicorn main:app --reload
   ```

---

## Common Issues

### Issue: "Generating forecast..." Never Completes

**Possible Causes:**
- Chronos model loading for first time (can take 10-30 seconds)
- Network timeout fetching historical data
- Memory issues with large datasets

**Solutions:**
1. **Wait 30 seconds** - First Chronos load is slow
2. **Check terminal** for error messages
3. **Try a different symbol** - Some may have data issues
4. **Reduce forecast horizon** - Try 10 days instead of 30

### Issue: Chronos Takes Too Long

**Solution:** Use mock mode (faster) or wait for first load:
```bash
# Chronos first load can take 10-30 seconds
# Subsequent forecasts are faster (cached)
```

### Issue: "Module not found" Errors

**Solution:** Install missing dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Dashboard Won't Start

**Solution:**
```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Check if port 8000 is free
lsof -ti:8000 | xargs kill -9

# Start on a different port if needed
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Performance Tips

1. **First Forecast is Slow**: Chronos model loads on first use (~10-30s)
2. **Subsequent Forecasts**: Much faster (model is cached)
3. **Use Smaller Horizon**: 10-20 days is faster than 30+ days
4. **Batch Analysis**: Can be slow with many symbols

---

## Debug Mode

- Run FastAPI with verbose logging:
  ```bash
  uvicorn main:app --reload --log-level debug
  ```
- Tail the application log:
  ```bash
  tail -f data/logs/fuggerbot.log
  ```

---

## Still Having Issues?

1. Check terminal output for errors
2. Refresh the browser page
3. Restart the FastAPI server
4. Review `data/logs/fuggerbot.log`

