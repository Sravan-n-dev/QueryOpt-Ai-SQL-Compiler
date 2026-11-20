"""
QueryOpt AI — Application Entry Point
=====================================
Starts the QueryOpt AI Streamlit web application.
Run via:
    streamlit run app.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.database_config import initialize_database
from ui.app_main import main

if __name__ == "__main__":
    initialize_database()
    main()
