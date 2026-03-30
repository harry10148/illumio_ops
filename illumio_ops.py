#!/usr/bin/env python3
"""
Illumio PCE Ops — Entry Point.
Usage:
    python illumio_ops.py                  # Interactive CLI menu
    python illumio_ops.py --monitor        # Headless daemon mode
    python illumio_ops.py --monitor -i 5   # Daemon with 5-min interval
    python illumio_ops.py --gui            # Launch tkinter GUI
"""
import sys

try:
    from src.main import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"Error importing src package: {e}")
    print("Ensure you are running this script from the project root directory.")
    sys.exit(1)
