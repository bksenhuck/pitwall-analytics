"""
Development entry point for Dash frontend.

This file maintains backward compatibility while using the new frontend/ structure.
For production, use main.py instead.
"""
from frontend.app import create_app, run_app

# Create app instance
app = create_app()
server = app.server

if __name__ == "__main__":
    run_app(app)
