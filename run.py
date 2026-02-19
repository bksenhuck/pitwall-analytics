"""
Unified development server launcher.

This script makes it easy to run both backend and frontend together.
In production, these would run as separate services.

Backend: FastAPI (ASGI) with Uvicorn
Frontend: Dash with built-in server

Usage:
    python run.py both    # Run both backend and frontend (default)
    python run.py backend # Run only backend
    python run.py frontend # Run only frontend
"""
import sys
import subprocess
import time
from pathlib import Path


def run_backend():
    """Start the backend FastAPI server with Uvicorn"""
    print("🏁 Starting Backend API (FastAPI + Uvicorn)...")
    subprocess.Popen(
        [sys.executable, "-m", "backend.app"],
        cwd=Path(__file__).parent
    )


def run_frontend():
    """Start the frontend Dash application"""
    print("🎨 Starting Frontend Dash App...")
    subprocess.Popen(
        [sys.executable, "-m", "frontend.app"],
        cwd=Path(__file__).parent
    )


def main():
    """Main entry point"""
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    
    print("""
╔═══════════════════════════════════════╗
║   🏁 Pitwall Analytics Launcher 🏁   ║
║        FastAPI + Dash                 ║
╚═══════════════════════════════════════╝
""")
    
    if mode == "backend":
        run_backend()
        print("\n✅ Backend started on http://127.0.0.1:5000")
        print("📡 API endpoints: http://127.0.0.1:5000/api/health")
        print("📚 API docs: http://127.0.0.1:5000/docs")
    
    elif mode == "frontend":
        run_frontend()
        print("\n✅ Frontend started on http://127.0.0.1:8050")
        print("🌐 Open in browser: http://127.0.0.1:8050")
    
    elif mode == "both":
        run_backend()
        time.sleep(3)  # Give backend time to start
        run_frontend()
        
        print("\n✅ Both services started!")
        print("📡 Backend API: http://127.0.0.1:5000/api")
        print("📚 API Docs: http://127.0.0.1:5000/docs (Swagger UI)")
        print("🌐 Frontend UI: http://127.0.0.1:8050")
        print("\n💡 Tip: Open http://127.0.0.1:8050 in your browser")
        print("💡 Explore API: http://127.0.0.1:5000/docs")
    
    else:
        print(f"❌ Unknown mode: {mode}")
        print("Usage: python run.py [backend|frontend|both]")
        return
    
    print("\n⏸️  Press Ctrl+C to stop all services")
    
    # Keep script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")


if __name__ == "__main__":
    main()
