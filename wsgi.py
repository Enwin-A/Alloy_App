#!/usr/bin/env python3
"""
WSGI entry point for production deployment with Gunicorn.
This file is used by Gunicorn to run the Flask application.
"""

from app import app

if __name__ == "__main__":
    app.run()
