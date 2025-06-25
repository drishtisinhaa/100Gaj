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

with open("N1model.pkl", "rb") as f:
    full_pipeline = pickle.load(f)

# Load feature names used during training
with open("feature_names.json") as f:
    feature_names = json.load(f)

data_processor = DataProcessor()

# ------------------------- Location APIs (unchanged) -------------------------
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
                'delhi_locations.csv'
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

# ------------------------- Resale + ROI Route Without Enrichment -------------------------

# Load new models
resale_model = joblib.load("MODEL1.pkl")
resale_preprocessor = joblib.load("resale_preprocessor.pkl")
rent_model = joblib.load("rent_model.pkl")
rent_preprocessor = joblib.load("rent_preprocessor.pkl")

# Define demand multipliers
DEMAND_MULTIPLIERS = {
    "delhi": 1.08,
    "gurgaon": 1.12,
    "noida": 1.05,
    "ghaziabad": 1.03
}

def calculate_roi(purchase_price, resale_price, rent_per_month, years):
    total_rent = rent_per_month * 12 * years
    total_gain = (resale_price - purchase_price) + total_rent
    roi = (total_gain / purchase_price) * 100
    return round(roi, 2), round(total_rent, 2), round(total_gain, 2)

@app.route("/api/predict-roi", methods=["POST"])
def predict_roi():
    try:
        user_input = request.get_json()
        input_df = pd.DataFrame([user_input])

        # Ensure all required columns are present and ordered
        for col in resale_preprocessor.feature_names_in_:
            if col not in input_df.columns:
                return jsonify({"error": f"columns are missing: {{'{col}'}}"}), 400

        # Resale prediction
        X_resale = resale_preprocessor.transform(input_df)
        resale_price = np.expm1(resale_model.predict(X_resale)[0])

        # Rent prediction
        X_rent = rent_preprocessor.transform(input_df)
        rent_price = rent_model.predict(X_rent)[0]

        # Purchase price estimate
        purchase_price = float(user_input["purchase_price"])
        renovation_cost = float(user_input.get("renovation_cost", 0))
        city = user_input.get("city", "").lower()

        adjusted_rent = rent_price * DEMAND_MULTIPLIERS.get(city, 1.0)

        # ROI calculation
        years = int(user_input.get("years_held", 5))
        roi, total_rent, total_gain = calculate_roi(purchase_price + renovation_cost, resale_price, adjusted_rent, years)

        return jsonify({
            "predicted_resale_price": round(resale_price),
            "predicted_monthly_rent": round(rent_price),
            "adjusted_monthly_rent": round(adjusted_rent),
            "estimated_purchase_price": round(purchase_price),
            "roi_percent": roi,
            "total_rent_income": total_rent,
            "total_gain": total_gain
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
     app.run(debug=True)
