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
from backend.api.pause_resume_routes import pause_resume_api
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
    app.register_blueprint(pause_resume_api, url_prefix='/api')

    # Serve frontend (Vite build)
    frontend_dist = os.path.join(base_dir, 'frontend', 'dist')

    @app.route('/')
    def index():
        """Serve main HTML page from Vite build."""
        if os.path.exists(frontend_dist):
            return send_from_directory(frontend_dist, 'index.html')
        else:
            return """
            <html>
            <body>
                <h1>Development Mode</h1>
                <p>The frontend hasn't been built yet. To run in development mode:</p>
                <ol>
                    <li>Install dependencies: <code>npm install</code></li>
                    <li>Run Vite dev server: <code>npm run dev</code></li>
                    <li>Open browser to: <a href="http://localhost:3000">http://localhost:3000</a></li>
                </ol>
                <p>To run in production mode:</p>
                <ol>
                    <li>Build frontend: <code>npm run build</code></li>
                    <li>Restart Flask server</li>
                    <li>Access at: <a href="http://localhost:5000">http://localhost:5000</a></li>
                </ol>
            </body>
            </html>
            """, 200

    @app.route('/assets/<path:path>')
    def serve_assets(path):
        """Serve Vite-built assets (JS, CSS, images)."""
        assets_dir = os.path.join(frontend_dist, 'assets')
        return send_from_directory(assets_dir, path)

    @app.route('/<path:path>')
    def serve_spa(path):
        """
        Catch-all route for client-side routing.
        Serve index.html for any non-API, non-asset routes.
        """
        # Check if it's a file that exists (like favicon.ico)
        file_path = os.path.join(frontend_dist, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(frontend_dist, path)

        # Otherwise serve index.html for client-side routing
        if os.path.exists(frontend_dist):
            return send_from_directory(frontend_dist, 'index.html')
        else:
            return "Frontend not built. Run 'npm run build' first.", 404

    return app


# Create application instance for direct running
app = create_app()

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
