import os
import logging
import zipfile
import json
import io
import numpy as np
import pandas as pd
import pickle
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from data_processor import DataProcessor
import joblib

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

with open("model1.pkl", "rb") as f:
    full_pipeline = pickle.load(f)

# Load feature names used during training
with open("feature_names.json") as f:
    feature_names = json.load(f)


# Initialize data processor
data_processor = DataProcessor()

# Market demand adjustment
demand_multipliers = {
    'delhi': 1.08,
    'gurgaon': 1.12,
    'noida': 1.05,
    'ghaziabad': 1.03
}

# ------------------------- Location APIs -------------------------
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running"}), 200

@app.route('/api/search', methods=['GET'])
def search_locations():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    try:
        results = data_processor.search_locations(query)
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/location/<location_name>', methods=['GET'])
def get_location_details(location_name):
    try:
        location_data = data_processor.get_location_details(location_name)
        if not location_data:
            return jsonify({'error': 'Location not found'}), 404
        return jsonify(location_data)
    except Exception as e:
        app.logger.error(f"Location details error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve location data'}), 500

@app.route('/api/locations', methods=['GET'])
def get_all_locations():
    try:
        locations = data_processor.get_all_locations()
        return jsonify(locations)
    except Exception as e:
        app.logger.error(f"Get all locations error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

@app.route('/download', methods=['GET'])
def download_project():
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            files_to_include = [
                'app.py',
                'main.py',
                'data_processor.py',
                'data/delhi_locations.csv'
            ]
            for file_path in files_to_include:
                if os.path.exists(file_path):
                    zip_file.write(file_path, file_path)
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='delhi_area_analyzer_backend.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

# ------------------------- ROI & Resale Prediction APIs -------------------------
@app.route('/api/predict-resale', methods=['POST'])
def predict_resale():
    try:
        data = request.get_json()

        # Convert input to DataFrame
        input_df = pd.DataFrame([data])

        # Ensure all required columns are present and ordered
        for col in feature_names:
            if col not in input_df.columns:
                input_df[col] = np.nan  # fill missing columns with NaN

        input_df = input_df[feature_names]

        # Predict resale value
        resale_value = full_pipeline.predict(input_df)[0]

        return jsonify({"resale_value": round(resale_value, 2)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict-roi', methods=['POST'])
def predict_roi():
    try:
        data = request.get_json()

        # Convert to DataFrame
        input_df = pd.DataFrame([data])

        # Reorder and filter columns to match training
        input_df = input_df[feature_names]
        input_df = input_df.reindex(columns=feature_names)

        # Predict resale value
        resale_value = full_pipeline.predict(input_df)[0]

        # ROI calculations (optional for your use-case)
        purchase_price = float(data["purchase_price"])
        renovation_cost = float(data["renovation_cost"])
        monthly_rent = float(data["monthly_rent"])
        city = data.get("city", "").lower()
        adjusted_rent = monthly_rent * demand_multipliers.get(city, 1.0)
        annual_rent = adjusted_rent * 12
        total_investment = purchase_price + renovation_cost
        roi = ((resale_value - purchase_price - renovation_cost + annual_rent) / total_investment) * 100

        return jsonify({
            "resale_value": round(resale_value, 2),
            "adjusted_monthly_rent": round(adjusted_rent, 2),
            "passive_income": round(annual_rent, 2),
            "roi_percent": round(roi, 2),
            "city": city.capitalize()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ------------------------- Error Handlers -------------------------
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ------------------------- Main Entry -------------------------
if __name__ == '__main__':
     app.run(host='0.0.0.0', port=5003, debug=True)
