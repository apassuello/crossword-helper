"""
Flask application launcher script.

This script starts the development server for the Crossword Construction Helper
web application on localhost:5000 with debug mode enabled.
"""

from backend.app import app

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
