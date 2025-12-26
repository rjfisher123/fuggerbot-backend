# 🚀 FuggerBot Unified Launcher

**Single-command system startup for all FuggerBot v2.5 components**

---

## 📋 **What It Does**

The unified launcher starts all FuggerBot systems in one command:

1. **Main Dashboard** (port 8501) - Trade analysis & War Games results
2. **Macro Dashboard** (port 8502) - Global market context & correlations
3. **Optimization Scheduler** (daemon mode) - Weekly meta-optimization loop
4. **Live Trading Bot** (continuous mode) - Executes trades based on signals

---

## 🚀 **Quick Start**

```bash
# Start everything
python launcher.py
```

**Output:**
```
==================================================
   🚀 FUGGERBOT V2.5 - UNIFIED LAUNCHER
==================================================
13:18:00 - [LAUNCHER] - ✅ Started Dashboard (PID: 3443) -> Logs: logs/dashboard.log
13:18:00 - [LAUNCHER] - ✅ Started Macro Dashboard (PID: 3444) -> Logs: logs/macro_dashboard.log
13:18:00 - [LAUNCHER] - ✅ Started Optimization Scheduler (PID: 3445) -> Logs: logs/scheduler.log
13:18:00 - [LAUNCHER] - ✅ Started Trading Bot (PID: 3446) -> Logs: logs/bot.log

✅ SYSTEM OPERATIONAL
📊 Main Dashboard:  http://localhost:8501
🌍 Macro Dashboard: http://localhost:8502
📝 Logs located in /logs directory
Press Ctrl+C to stop all services.
```

---

## 🛑 **Stopping**

Press **Ctrl+C** to gracefully terminate all services:

```
🛑 Shutdown signal received. Terminating all systems...
   Terminating PID 3443...
   Terminating PID 3444...
   Terminating PID 3445...
   Terminating PID 3446...
👋 All systems offline.
```

---

## 📁 **Log Files**

All service logs are written to the `logs/` directory:

- `logs/dashboard.log` - Main dashboard output
- `logs/macro_dashboard.log` - Macro dashboard output
- `logs/scheduler.log` - Optimization scheduler output
- `logs/bot.log` - Trading bot output

**View logs in real-time:**
```bash
# View all logs
tail -f logs/*.log

# View specific service
tail -f logs/bot.log
```

---

## 🔧 **Configuration**

### **Disable Specific Services**

Edit `launcher.py` and comment out services you don't need:

```python
# 1. Start Dashboard (Streamlit)
start_process(
    ["streamlit", "run", "tools/dashboard.py", ...],
    "Dashboard",
    f"{LOG_DIR}/dashboard.log"
)

# 2. DISABLE Macro Dashboard (comment out)
# start_process(
#     ["streamlit", "run", "ui/diagnostics/macro_dashboard.py", ...],
#     "Macro Dashboard",
#     f"{LOG_DIR}/macro_dashboard.log"
# )

# 3. Start Optimization Scheduler
# ...
```

### **Change Ports**

Modify the Streamlit port arguments:

```python
start_process(
    ["streamlit", "run", "tools/dashboard.py", "--server.port", "9000", ...],
    "Dashboard",
    f"{LOG_DIR}/dashboard.log"
)
```

### **Change Trading Interval**

Modify the bot interval argument (default: 60 seconds):

```python
start_process(
    ["python", "run_bot.py", "--continuous", "--interval", "300"],  # 5 minutes
    "Trading Bot",
    f"{LOG_DIR}/bot.log"
)
```

---

## 🧪 **Testing**

### **Test Individual Services**

Before using the launcher, test each service manually:

```bash
# Test Dashboard
streamlit run tools/dashboard.py --server.port 8501

# Test Macro Dashboard
streamlit run ui/diagnostics/macro_dashboard.py --server.port 8502

# Test Scheduler (once mode)
python daemon/optimization_scheduler.py --mode once

# Test Bot (single run)
python run_bot.py
```

### **Verify Launcher**

Start and immediately stop:

```bash
python launcher.py &
LAUNCHER_PID=$!
sleep 5
kill -SIGINT $LAUNCHER_PID
```

---

## 🔄 **Process Monitoring**

The launcher automatically monitors all processes and logs warnings if any service crashes:

```
⚠️ Process 3446 died unexpectedly (exit code: 1). Check logs.
```

**Auto-Restart (Optional):**
Add restart logic in the monitoring loop (search for "Optional: Logic to auto-restart"):

```python
for i, p in enumerate(processes):
    if p.poll() is not None:
        exit_code = p.poll()
        logger.warning(f"⚠️ Process {p.pid} died unexpectedly (exit code: {exit_code}). Check logs.")
        
        # Auto-restart logic (example)
        if exit_code != 0:
            logger.info(f"   Restarting process...")
            # Restart the process here
```

---

## 🐳 **Running as Background Service**

### **Using nohup (Simple)**

```bash
nohup python launcher.py > /dev/null 2>&1 &
echo $! > launcher.pid

# Stop later
kill $(cat launcher.pid)
```

### **Using systemd (Linux)**

Create `/etc/systemd/system/fuggerbot.service`:

```ini
[Unit]
Description=FuggerBot v2.5 Unified System
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/fuggerbot
ExecStart=/usr/bin/python3 /path/to/fuggerbot/launcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable fuggerbot
sudo systemctl start fuggerbot

# Check status
sudo systemctl status fuggerbot

# View logs
sudo journalctl -u fuggerbot -f
```

---

## 📊 **Architecture**

```
launcher.py (PID: 1234)
    │
    ├─ streamlit (PID: 1235) → Dashboard (port 8501)
    ├─ streamlit (PID: 1236) → Macro Dashboard (port 8502)
    ├─ python (PID: 1237) → Optimization Scheduler (daemon)
    └─ python (PID: 1238) → Trading Bot (continuous)
```

**Process Isolation:**
- Each service runs in a separate subprocess
- Logs are redirected to individual files
- Failures are isolated (one service crash doesn't affect others)
- Graceful shutdown terminates all children

---

## 🛡️ **Safety Features**

1. **Graceful Shutdown:** Ctrl+C sends SIGTERM to all processes (5s timeout)
2. **Forceful Kill:** Processes that don't terminate gracefully are killed
3. **Log Isolation:** Each service has its own log file
4. **Process Monitoring:** Detects unexpected crashes
5. **Port Management:** Services use dedicated ports to avoid conflicts

---

## 🎯 **Use Cases**

### **Development**
```bash
# Start everything for testing
python launcher.py

# Make changes to code
# Ctrl+C to stop
# Restart to reload changes
python launcher.py
```

### **Production**
```bash
# Run as background service
nohup python launcher.py > /dev/null 2>&1 &

# Monitor health
tail -f logs/*.log
```

### **Staging**
```bash
# Start only dashboards (no trading)
# Comment out bot in launcher.py
python launcher.py
```

---

## 📝 **Troubleshooting**

### **Port Already in Use**
```
Error: Address already in use
```
**Solution:** Kill existing processes on those ports:
```bash
lsof -ti:8501 | xargs kill -9
lsof -ti:8502 | xargs kill -9
```

### **Process Won't Start**
Check the log file for the specific service:
```bash
cat logs/dashboard.log
cat logs/bot.log
```

### **Service Crashes Immediately**
Run the service manually to see the error:
```bash
streamlit run tools/dashboard.py --server.port 8501
python run_bot.py --continuous --interval 60
```

### **Launcher Won't Stop**
Forcefully kill:
```bash
pkill -f launcher.py
pkill -f streamlit
pkill -f run_bot.py
```

---

## 🏆 **Benefits**

✅ **Single Command Startup** - No manual service orchestration  
✅ **Unified Logging** - All logs in one directory  
✅ **Graceful Shutdown** - Clean termination of all services  
✅ **Process Monitoring** - Automatic crash detection  
✅ **Production Ready** - Can run as systemd service  

---

## 📚 **Related Files**

- `launcher.py` - Main launcher script
- `daemon/optimization_scheduler.py` - Optimization scheduler
- `tools/dashboard.py` - Main dashboard
- `ui/diagnostics/macro_dashboard.py` - Macro dashboard
- `run_bot.py` - Trading bot

---

**Status:** ✅ **PRODUCTION READY**  
**Version:** v2.5 - Operation Autopilot  
**Last Updated:** December 11, 2025






