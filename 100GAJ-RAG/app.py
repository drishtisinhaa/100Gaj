# This is your new app.py file, formerly run_flask.py

import logging
import atexit
from flask import Flask, jsonify
from flask_cors import CORS

from app.api.v1.endpoints.chat_flask import chat_bp
from app.core.engine import get_chat_engine
from app.core.tools.api_property_search import _fetch_all_data
from app.core.async_worker import async_worker

# Recommended change: Using __name__ is standard practice for Flask.
app = Flask(__name__)

# --- REQUIREMENT #1: CORS Handling ---
# This is where CORS is handled using the Flask-Cors library.
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Register the API routes from our chat_flask.py file
app.register_blueprint(chat_bp, url_prefix='/api/v1')

# --- REQUIREMENT #2: JSON with jsonify ---
# This health-check route demonstrates returning JSON with jsonify.
@app.route("/", methods=["GET"])
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return jsonify({
        "status": "ok",
        "message": "100Gaj Flask API is running"
    })

# Logic to pre-load models and data on server startup
with app.app_context():
    logging.info("Application starting up...")
    get_chat_engine()
    _fetch_all_data()
    logging.info("Startup complete. Models and data are loaded.")

# Gracefully stop the background worker thread on exit
atexit.register(lambda: async_worker.stop())

# Main entry point to run the server
if __name__ == '__main__':
    # The new command to run your server is: python app.py
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)