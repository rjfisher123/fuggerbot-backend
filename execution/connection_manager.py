"""
IBKR Connection Manager.

A thread-safe Singleton to manage the Interactive Brokers connection lifecycle.
Designed to work compatibly with FastAPI's asyncio event loop.
"""
import asyncio
import logging
import threading
from typing import Optional
from ib_insync import IB

logger = logging.getLogger("execution.connection_manager")

class IBKRConnectionManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(IBKRConnectionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.ib = IB()
        self.host = "127.0.0.1"
        self.port = 7497
        self.client_id = 1
        self.connected = False
        self._loop = None  # The loop where connection was established

    async def connect_async(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """
        Async connection method designed for FastAPI.
        Attempts to connect to a list of common ports if standard port fails.
        """
        if self.ib.isConnected():
            logger.info("ConnectionManager: Already connected.")
            self.connected = True
            return True

        # Capture the current running loop (FastAPI's loop)
        self._loop = asyncio.get_running_loop()

        # Define explicit port list to scan
        # If user explicitly requests a port (e.g. from UI), try that first.
        # Otherwise, scan common ports.
        ports_to_try = [port]
        common_ports = [7496, 7497, 4001, 4002]
        
        # Add common ports if not already in list
        for p in common_ports:
            if p not in ports_to_try:
                ports_to_try.append(p)

        self.host = host
        self.client_id = client_id

        for target_port in ports_to_try:
            try:
                logger.info(f"ConnectionManager: Attempting connection to {host}:{target_port} (ID: {client_id})...")
                
                # We must await connectAsync
                # Note: ib_insync connects, but sometimes hangs if port is wrong?
                # We use timeout=2s for faster scanning
                await self.ib.connectAsync(host, target_port, client_id, timeout=2)
                
                # If we get here without exception and no 'not connected' error
                self.port = target_port 
                self.connected = True
                logger.info(f"ConnectionManager: ✅ Connected successfully on port {target_port}.")
                return True
                
            except Exception as e:
                logger.warning(f"ConnectionManager: ❌ Failed on port {target_port}: {e}")
                # Clean up partial state if necessary
                if self.ib.isConnected():
                    self.ib.disconnect()
                
                # Continue to next port
                continue
        
        logger.error("ConnectionManager: ❌ All connection attempts failed.")
        self.connected = False
        return False

    def disconnect(self):
        """Disconnect safely."""
        if self.ib.isConnected():
            try:
                self.ib.disconnect()
                logger.info("ConnectionManager: Disconnected.")
            except Exception as e:
                logger.error(f"ConnectionManager: Disconnect error: {e}")
        self.connected = False

    def check_health(self) -> dict:
        """Return detailed health status."""
        is_connected = self.ib.isConnected() # internal check
        self.connected = is_connected # sync state
        
        status = {
            "connected": is_connected,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "account": "N/A",
            "error": None
        }
        
        if is_connected:
            try:
                # Quick read of managed accounts
                accounts = self.ib.managedAccounts()
                if accounts:
                    status["account"] = accounts[0]
            except Exception as e:
                status["error"] = str(e)
        else:
             status["error"] = "Not connected"
                
        return status

    def get_ib(self) -> IB:
        """Return the raw IB instance."""
        return self.ib

# Global Accessor
def get_connection_manager() -> IBKRConnectionManager:
    return IBKRConnectionManager()
