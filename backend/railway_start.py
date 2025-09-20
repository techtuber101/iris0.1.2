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
import threading
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_system_info():
    """Log system information for debugging."""
    logger.info("=== SYSTEM INFO ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Environment variables:")
    for key in ['PORT', 'REDIS_URL', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD']:
        value = os.getenv(key)
        if key == 'REDIS_PASSWORD' and value:
            logger.info(f"  {key}: {'*' * len(value)}")
        else:
            logger.info(f"  {key}: {value}")
    logger.info(f"Available processes: {psutil.cpu_count()}")
    logger.info("==================")

def check_process_health(process_name, process_obj):
    """Check if a process is still running."""
    if process_obj and process_obj.is_alive():
        logger.info(f"✅ {process_name} process is running (PID: {process_obj.pid})")
        return True
    else:
        logger.error(f"❌ {process_name} process is not running")
        return False

def monitor_processes(worker_process, stop_event):
    """Monitor process health in a separate thread."""
    while not stop_event.is_set():
        try:
            check_process_health("Worker", worker_process)
            time.sleep(10)  # Check every 10 seconds
        except Exception as e:
            logger.error(f"Error monitoring processes: {e}")
            time.sleep(5)

def run_api():
    """Run the FastAPI server."""
    logger.info("🚀 Starting FastAPI server...")
    try:
        # Use the same command as railway.json
        cmd = [
            "uv", "run", "python", "-m", "uvicorn", 
            "api:app", 
            "--host", "0.0.0.0", 
            "--port", os.getenv("PORT", "8000"),
            "--timeout-keep-alive", "75",
            "--proxy-headers",
            "--forwarded-allow-ips", "*"
        ]
        logger.info(f"FastAPI command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FastAPI server failed: {e}")
        logger.error(f"Return code: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 FastAPI server stopped")
    except Exception as e:
        logger.error(f"❌ Unexpected error in FastAPI server: {e}")
        sys.exit(1)

def run_worker():
    """Run the Dramatiq worker."""
    logger.info("🔧 Starting Dramatiq worker...")
    try:
        cmd = [
            "uv", "run", "dramatiq", 
            "--skip-logging", 
            "--processes", "4", 
            "--threads", "4", 
            "run_agent_background"
        ]
        logger.info(f"Worker command: {' '.join(cmd)}")
        
        # Check if the worker module exists
        worker_file = "run_agent_background.py"
        if not os.path.exists(worker_file):
            logger.error(f"❌ Worker file not found: {worker_file}")
            logger.error(f"Current directory contents: {os.listdir('.')}")
            sys.exit(1)
        
        logger.info(f"✅ Worker file exists: {worker_file}")
        
        # Run the worker
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✅ Worker started successfully")
        logger.info(f"Worker stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Worker stderr: {result.stderr}")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Dramatiq worker failed: {e}")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Dramatiq worker stopped")
    except Exception as e:
        logger.error(f"❌ Unexpected error in Dramatiq worker: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"🛑 Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main function to start both processes."""
    logger.info("🎯 Starting Suna API and Worker services...")
    
    # Log system information
    log_system_info()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start worker process
    logger.info("🔧 Starting worker process...")
    worker_process = Process(target=run_worker)
    worker_process.start()
    
    # Give worker a moment to start
    logger.info("⏳ Waiting for worker to initialize...")
    time.sleep(5)
    
    # Check if worker started successfully
    if not check_process_health("Worker", worker_process):
        logger.error("❌ Worker failed to start, exiting...")
        sys.exit(1)
    
    # Start process monitoring
    stop_monitoring = threading.Event()
    monitor_thread = threading.Thread(target=monitor_processes, args=(worker_process, stop_monitoring))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        # Run API in main process (for Railway health checks)
        logger.info("🚀 Starting API process...")
        run_api()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        # Stop monitoring
        stop_monitoring.set()
        monitor_thread.join(timeout=5)
        
        # Terminate worker process
        if worker_process.is_alive():
            logger.info("🛑 Terminating worker process...")
            worker_process.terminate()
            worker_process.join(timeout=10)
            if worker_process.is_alive():
                logger.warning("⚠️ Force killing worker process...")
                worker_process.kill()
                worker_process.join(timeout=5)
        
        logger.info("✅ Shutdown complete")

if __name__ == "__main__":
    main()
