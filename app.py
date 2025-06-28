import os
import logging
import zipfile
import json
import io
import numpy as np
import pandas as pd
import cloudpickle
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

# Load rent model
with open("RENTM.pkl", "rb") as f:
    rent_model = cloudpickle.load(f)

# Load rent preprocessor
with open("RENTP.pkl", "rb") as f:
    rent_preprocessor = cloudpickle.load(f)

# Load resale model
with open("RESALEM.pkl", "rb") as f:
    resale_model = cloudpickle.load(f)

# Load resale preprocessor
with open("RESALEP.pkl", "rb") as f:
    resale_preprocessor = cloudpickle.load(f)

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
        original_df = pd.DataFrame([user_input])

        # Clean & Map fields to match model input
        column_mapping = {
            "city": "city",
            "cityName": "city",
            "location": "sublocation",
            "localityName": "sublocation",
            "suburbName": "sublocation",
            "name": "name",
            "rate_per_sqft": "rate_per_sqft",
            "bhk": "bedroom",
            "bedrooms": "bedroom",
            "status": "status",
            "transaction": "transaction",
            "carpet_area_sqft": "carpet_area_sqft",
            "total_area": "total_area"
        }

        # Rename columns
        cleaned_df = original_df.rename(columns=column_mapping)

        # Keep only expected columns
        expected_features = [
            "city", "sublocation", "name", "rate_per_sqft", "bedroom",
            "status", "transaction", "carpet_area_sqft", "total_area"
        ]
        cleaned_df = cleaned_df[expected_features]

        # Fill missing values
        cleaned_df = cleaned_df.fillna({
            "rate_per_sqft": 0,
            "bedroom": 2,
            "carpet_area_sqft": 0,
            "total_area": 0,
            "city": "Unknown",
            "sublocation": "Unknown",
            "name": "Unknown",
            "status": "ready_to_move",
            "transaction": "resale"
        })

        # ✅ This is the ONLY DataFrame we pass to the preprocessor!
        X_resale = resale_preprocessor.transform(cleaned_df)
        resale_price = np.expm1(resale_model.predict(X_resale)[0])

        X_rent = rent_preprocessor.transform(cleaned_df)
        rent_price = rent_model.predict(X_rent)[0]

        purchase_price = float(user_input.get("purchase_price", 0))
        renovation_cost = float(user_input.get("renovation_cost", 0))
        city = user_input.get("city", "").lower()

        adjusted_rent = rent_price * DEMAND_MULTIPLIERS.get(city, 1.0)
        years = int(user_input.get("years_held", 5))

        total_rent = adjusted_rent * 12 * years
        total_gain = (resale_price - purchase_price - renovation_cost) + total_rent
        roi = (total_gain / (purchase_price + renovation_cost)) * 100

        return jsonify({
            "predicted_resale_price": round(resale_price),
            "predicted_monthly_rent": round(rent_price),
            "adjusted_monthly_rent": round(adjusted_rent),
            "estimated_purchase_price": round(purchase_price),
            "roi_percent": round(roi, 2),
            "total_rent_income": round(total_rent, 2),
            "total_gain": round(total_gain, 2)
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
