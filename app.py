import os
import logging
import zipfile
import io
from flask import Flask, render_template, jsonify, request, send_file
from data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize data processor
data_processor = DataProcessor()

@app.route('/')
def index():
    """Main page with search interface"""
    return render_template('index.html')

@app.route('/api/search')
def search_locations():
    """API endpoint for location search with autocomplete"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])
    
    try:
        results = data_processor.search_locations(query)
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/location/<location_name>')
def get_location_details(location_name):
    """API endpoint to get detailed information about a specific location"""
    try:
        location_data = data_processor.get_location_details(location_name)
        
        if not location_data:
            return jsonify({'error': 'Location not found'}), 404
        
        return jsonify(location_data)
    except Exception as e:
        app.logger.error(f"Location details error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve location data'}), 500

@app.route('/api/locations')
def get_all_locations():
    """API endpoint to get all locations for autocomplete"""
    try:
        locations = data_processor.get_all_locations()
        return jsonify(locations)
    except Exception as e:
        app.logger.error(f"Get all locations error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

@app.route('/download')
def download_project():
    """Download complete project files as ZIP"""
    try:
        # Create a ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add application files
            files_to_include = [
                'app.py',
                'main.py',
                'data_processor.py',
                'templates/index.html',
                'templates/base.html',
                'static/js/main.js',
                'static/css/custom.css',
                'data/delhi_locations.csv'
            ]
            
            for file_path in files_to_include:
                if os.path.exists(file_path):
                    zip_file.write(file_path, file_path)
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='delhi_area_analyzer.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
