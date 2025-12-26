# IBKR Connection Fix Guide

## 🔴 Problem Identified

**Status:** TWS is running on port 7497, but API connections are timing out.

**Root Cause:** TWS API is not enabled or not configured correctly.

---

## ✅ Solution: Enable TWS API

### Step 1: Open TWS API Settings

1. **In TWS**, go to the menu bar
2. Click: **File → Global Configuration → API → Settings**

### Step 2: Enable API Access

Check the following settings:

✅ **Enable ActiveX and Socket Clients** (MUST be checked)

✅ **Socket port:** `7497` (for Paper Trading) or `7496` (for Live Trading)

✅ **Trusted IP addresses:** Add `127.0.0.1`
   - Click the "+" button
   - Enter: `127.0.0.1`
   - Click OK

✅ **Master API client ID:** Leave as default (usually 0)

✅ **Read-Only API:** Uncheck this (unless you only want read access)

### Step 3: Apply Settings

1. Click **OK** to save settings
2. **Wait 10-15 seconds** for TWS to apply the changes
3. You may see a message about API being enabled

### Step 4: Verify Connection

Run the test script:

```bash
cd /Users/ryanfisher/fuggerbot
python scripts/test_ibkr_simple.py
```

**Expected output:**
```
✅ CONNECTION SUCCESSFUL!
Managed Accounts: ['DU123456']
Server Time: 2025-12-22 14:30:00
```

---

## 🔧 Alternative: Restart TWS

If the above doesn't work:

1. **Close TWS completely**
2. **Reopen TWS**
3. **Log in** and wait for it to fully load
4. **Re-check API settings** (Step 1-3 above)
5. **Run test again**

---

## 📋 Common Issues

### Issue 1: "Connection Timeout"
**Cause:** API not enabled  
**Fix:** Follow Step 2 above, ensure "Enable ActiveX and Socket Clients" is checked

### Issue 2: "Connection Refused"
**Cause:** Wrong port or TWS not running  
**Fix:** 
- Paper Trading: Port 7497
- Live Trading: Port 7496
- Check TWS is running

### Issue 3: "Client ID Conflict"
**Cause:** Another application using the same client ID  
**Fix:** Close other trading apps or change client ID in FuggerBot

### Issue 4: "IP Not Trusted"
**Cause:** 127.0.0.1 not in trusted IPs  
**Fix:** Add 127.0.0.1 to trusted IP addresses (Step 2)

---

## 🎯 Quick Checklist

Before running FuggerBot, verify:

- [ ] TWS is running and fully loaded
- [ ] API is enabled (File → Global Configuration → API → Settings)
- [ ] "Enable ActiveX and Socket Clients" is checked
- [ ] Socket port is 7497 (paper) or 7496 (live)
- [ ] 127.0.0.1 is in trusted IP addresses
- [ ] Test script passes: `python scripts/test_ibkr_simple.py`

---

## 🚀 Once Connected

After fixing the connection, you can:

1. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

2. **Test IBKR connection via API:**
   ```bash
   curl http://localhost:8000/api/ibkr/status
   ```

3. **Connect via API:**
   ```bash
   curl -X POST http://localhost:8000/api/ibkr/connect \
     -H "Content-Type: application/json" \
     -d '{"port": 7497}'
   ```

---

## 📞 Still Not Working?

If you've followed all steps and it's still not connecting:

1. **Check TWS logs:**
   - TWS → Help → About Trader Workstation → View Logs

2. **Check firewall:**
   - Make sure macOS firewall isn't blocking TWS

3. **Try IB Gateway instead of TWS:**
   - IB Gateway is lighter and sometimes more reliable
   - Download from IBKR website
   - Use port 4001 (paper) or 4002 (live)

4. **Run diagnostic:**
   ```bash
   python scripts/diagnose_ibkr_connection.py
   ```

---

## 📚 Reference

- **TWS API Documentation:** https://interactivebrokers.github.io/tws-api/
- **ib_insync Documentation:** https://ib-insync.readthedocs.io/
- **FuggerBot IBKR Setup:** See `IBKR_SETUP.md`

---

**Last Updated:** December 22, 2025  
**Tested With:** TWS Paper Trading, Port 7497

