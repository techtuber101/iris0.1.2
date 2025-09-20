#!/usr/bin/env python3
"""
Railway startup script that runs both API and worker processes.
This allows Railway to run both services in a single deployment.
"""

import subprocess
import sys
import os
import signal
import time
from multiprocessing import Process
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_api():
    """Run the FastAPI server."""
    logger.info("Starting FastAPI server...")
    try:
        # Use the same command as railway.json
        cmd = [
            "uv", "run", "python", "-m", "uvicorn", 
            "core.run:app", 
            "--host", "0.0.0.0", 
            "--port", os.getenv("PORT", "8000"),
            "--timeout-keep-alive", "75",
            "--proxy-headers",
            "--forwarded-allow-ips", "*"
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FastAPI server failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("FastAPI server stopped")

def run_worker():
    """Run the Dramatiq worker."""
    logger.info("Starting Dramatiq worker...")
    try:
        cmd = [
            "uv", "run", "dramatiq", 
            "--skip-logging", 
            "--processes", "4", 
            "--threads", "4", 
            "run_agent_background"
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Dramatiq worker failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Dramatiq worker stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main function to start both processes."""
    logger.info("Starting Suna API and Worker services...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start worker process
    worker_process = Process(target=run_worker)
    worker_process.start()
    
    # Give worker a moment to start
    time.sleep(2)
    
    try:
        # Run API in main process (for Railway health checks)
        run_api()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Terminate worker process
        if worker_process.is_alive():
            logger.info("Terminating worker process...")
            worker_process.terminate()
            worker_process.join(timeout=10)
            if worker_process.is_alive():
                logger.warning("Force killing worker process...")
                worker_process.kill()

if __name__ == "__main__":
    main()
