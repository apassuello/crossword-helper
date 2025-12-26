"""
Flask application factory for crossword helper API.

This module creates and configures the Flask application with all routes,
middleware, and error handlers.
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.api.routes import api
from backend.api.wordlist_routes import wordlist_api
from backend.api.progress_routes import progress_api
import os


def create_app(testing=False):
    """
    Create and configure Flask application.

    Args:
        testing: If True, configure for testing mode

    Returns:
        Configured Flask application instance
    """
    # Determine base directory (project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(__name__)

    # Configuration
    app.config['TESTING'] = testing
    app.config['JSON_SORT_KEYS'] = False  # Preserve key order in JSON responses

    # CORS (allow localhost for both Flask server and React dev server)
    CORS(app, origins=[
        'http://localhost:5000',      # Flask server
        'http://127.0.0.1:5000',
        'http://localhost:3000',      # React dev server
        'http://127.0.0.1:3000'
    ])

    # Register API blueprints
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(wordlist_api, url_prefix='/api')
    app.register_blueprint(progress_api, url_prefix='/api')

    # Serve frontend
    @app.route('/')
    def index():
        """Serve main HTML page."""
        frontend_dir = os.path.join(base_dir, 'frontend', 'templates')
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/static/<path:path>')
    def serve_static(path):
        """Serve static files (CSS, JS, images)."""
        static_dir = os.path.join(base_dir, 'frontend', 'static')
        return send_from_directory(static_dir, path)

    return app


# Create application instance for direct running
app = create_app()

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
