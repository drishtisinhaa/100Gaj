# <<<<<<< LOAN-EMI-CALC
# app.py
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# API Response helper function
def api_response(data=None, message="Success", status_code=200, error=None):
    """Standardized API response format"""
    response = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "success" if status_code < 400 else "error",
        "message": message,
        "data": data
    }
    if error:
        response["error"] = error
    return jsonify(response), status_code

# Input validation helper
def validate_input(data, required_fields, field_types=None):
    """Validate input data"""
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            errors.append(f"'{field}' is required")
    
    # Check field types and convert
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                try:
                    if expected_type == float:
                        data[field] = float(data[field])
                        if data[field] < 0:
                            errors.append(f"'{field}' must be a positive number")
                    elif expected_type == int:
                        data[field] = int(data[field])
                        if data[field] < 0:
                            errors.append(f"'{field}' must be a positive integer")
                except (ValueError, TypeError):
                    errors.append(f"'{field}' must be a valid {expected_type.__name__}")
    
    return errors

# Web Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate/<calc_type>', methods=['POST'])
def calculate(calc_type):
    """Legacy endpoint for web interface"""
    try:
        data = request.json
        
        if calc_type == 'emi':
            return calculate_emi_legacy(data)
        elif calc_type == 'affordability':
            return calculate_affordability_legacy(data)
        elif calc_type == 'dti':
            return calculate_dti_legacy(data)
        elif calc_type == 'gratuity':
            return calculate_gratuity_legacy(data)
        elif calc_type == 'retirement':
            return calculate_retirement_legacy(data)
        else:
            return jsonify({'error': 'Invalid calculator type'})
    except Exception as e:
        return jsonify({'error': str(e)})

# API Routes
@app.route('/api/v1/emi', methods=['POST'])
def api_calculate_emi():
    """
    Calculate EMI for home loan
    ---
    Request Body:
    {
        "property_value": 5000000,  // Optional if loan_amount provided
        "down_payment": 1000000,    // Optional if loan_amount provided  
        "loan_amount": 4000000,     // Optional if property_value and down_payment provided
        "rate": 8.5,                // Annual interest rate %
        "tenure": 240               // Loan tenure in months
    }
    """
    try:
        data = request.json
        if not data:
            return api_response(error="Request body is required", status_code=400)
        
        # Validate required fields
        required_fields = ['rate', 'tenure']
        field_types = {
            'property_value': float,
            'down_payment': float,
            'loan_amount': float,
            'rate': float,
            'tenure': int
        }
        
        errors = validate_input(data, required_fields, field_types)
        
        # Validate loan amount calculation
        property_value = data.get('property_value', 0)
        down_payment = data.get('down_payment', 0)
        loan_amount = data.get('loan_amount', 0)
        
        if not loan_amount and not (property_value and down_payment):
            errors.append("Either 'loan_amount' or both 'property_value' and 'down_payment' are required")
        
        if errors:
            return api_response(error="Validation errors", message="Invalid input", status_code=400, data={"errors": errors})
        
        # Calculate principal
        if property_value and down_payment:
            principal = property_value - down_payment
        else:
            principal = loan_amount
            
        if principal <= 0:
            return api_response(error="Principal amount must be positive", status_code=400)
        
        # EMI Calculation
        monthly_rate = data['rate'] / (12 * 100)
        tenure = data['tenure']
        
        if monthly_rate == 0:
            emi = principal / tenure
        else:
            emi = (principal * monthly_rate * (1 + monthly_rate) ** tenure) / ((1 + monthly_rate) ** tenure - 1)
        
        total_payment = emi * tenure
        total_interest = total_payment - principal
        
        result = {
            'principal': round(principal, 2),
            'emi': round(emi, 2),
            'total_payment': round(total_payment, 2),
            'total_interest': round(total_interest, 2),
            'monthly_rate': round(monthly_rate * 100, 4),
            'tenure_years': round(tenure / 12, 1)
        }
        
        return api_response(data=result, message="EMI calculated successfully")
        
    except Exception as e:
        return api_response(error=str(e), status_code=500)

@app.route('/api/v1/affordability', methods=['POST'])
def api_calculate_affordability():
    """
    Calculate home loan affordability
    ---
    Request Body:
    {
        "income": 100000,           // Monthly income
        "expenses": 40000,          // Monthly expenses
        "existing_emis": 10000,     // Existing EMI obligations
        "down_payment": 1000000,    // Available down payment
        "debt_ratio": 0.4           // Optional, default 40% of disposable income
    }
    """
    try:
        data = request.json
        if not data:
            return api_response(error="Request body is required", status_code=400)
        
        required_fields = ['income', 'expenses', 'existing_emis']
        field_types = {
            'income': float,
            'expenses': float,
            'existing_emis': float,
            'down_payment': float,
            'debt_ratio': float
        }
        
        errors = validate_input(data, required_fields, field_types)
        if errors:
            return api_response(error="Validation errors", message="Invalid input", status_code=400, data={"errors": errors})
        
        income = data['income']
        expenses = data['expenses']
        existing_emis = data['existing_emis']
        down_payment = data.get('down_payment', 0)
        debt_ratio = data.get('debt_ratio', 0.4)  # Default 40%
        
        disposable_income = income - expenses
        max_emi = disposable_income * debt_ratio - existing_emis
        
        if max_emi <= 0:
            return api_response(
                data={"max_emi": 0, "affordable_loan": 0, "affordable_property": down_payment},
                message="No affordable loan amount with current income and expenses"
            )
        
        # Rough estimate: 60 months tenure for affordability calculation
        affordable_loan = max_emi * 60
        affordable_property = affordable_loan + down_payment
        
        result = {
            'income': round(income, 2),
            'expenses': round(expenses, 2),
            'existing_emis': round(existing_emis, 2),
            'down_payment': round(down_payment, 2),
            'disposable_income': round(disposable_income, 2),
            'max_emi': round(max_emi, 2),
            'affordable_loan': round(affordable_loan, 2),
            'affordable_property': round(affordable_property, 2),
            'remaining_income': round(disposable_income - max_emi, 2)
        }
        
        return api_response(data=result, message="Affordability calculated successfully")
        
    except Exception as e:
        return api_response(error=str(e), status_code=500)

@app.route('/api/v1/dti', methods=['POST'])
def api_calculate_dti():
    """
    Calculate Debt-to-Income ratio
    ---
    Request Body:
    {
        "debt": 25000,              // Total monthly debt payments
        "income": 100000            // Monthly gross income
    }
    """
    try:
        data = request.json
        if not data:
            return api_response(error="Request body is required", status_code=400)
        
        required_fields = ['debt', 'income']
        field_types = {'debt': float, 'income': float}
        
        errors = validate_input(data, required_fields, field_types)
        if errors:
            return api_response(error="Validation errors", message="Invalid input", status_code=400, data={"errors": errors})
        
        debt = data['debt']
        income = data['income']
        
        if income <= 0:
            return api_response(error="Income must be greater than 0", status_code=400)
        
        dti_ratio = (debt / income) * 100
        remaining_income = income - debt
        
        # Risk assessment
        if dti_ratio <= 20:
            risk_level = "Low"
            risk_description = "Excellent debt management"
        elif dti_ratio <= 40:
            risk_level = "Moderate"
            risk_description = "Manageable debt level"
        else:
            risk_level = "High"
            risk_description = "High debt burden, consider debt reduction"
        
        result = {
            'income': round(income, 2),
            'debt': round(debt, 2),
            'dti_ratio': round(dti_ratio, 2),
            'remaining_income': round(remaining_income, 2),
            'risk_level': risk_level,
            'risk_description': risk_description
        }
        
        return api_response(data=result, message="DTI ratio calculated successfully")
        
    except Exception as e:
        return api_response(error=str(e), status_code=500)

@app.route('/api/v1/gratuity', methods=['POST'])
def api_calculate_gratuity():
    """
    Calculate gratuity amount
    ---
    Request Body:
    {
        "salary": 50000,            // Last drawn salary
        "years": 10                 // Years of service
    }
    """
    try:
        data = request.json
        if not data:
            return api_response(error="Request body is required", status_code=400)
        
        required_fields = ['salary', 'years']
        field_types = {'salary': float, 'years': int}
        
        errors = validate_input(data, required_fields, field_types)
        if errors:
            return api_response(error="Validation errors", message="Invalid input", status_code=400, data={"errors": errors})
        
        salary = data['salary']
        years = data['years']
        
        if years < 5:
            return api_response(
                data={"gratuity": 0, "eligible": False},
                message="Minimum 5 years of service required for gratuity"
            )
        
        # Standard gratuity calculation: (Salary × 15 × Years) / 26
        gratuity = (salary * 15 * years) / 26
        
        result = {
            'salary': round(salary, 2),
            'years': years,
            'gratuity': round(gratuity, 2),
            'eligible': True,
            'calculation_method': 'Standard formula: (Salary × 15 × Years) / 26'
        }
        
        return api_response(data=result, message="Gratuity calculated successfully")
        
    except Exception as e:
        return api_response(error=str(e), status_code=500)

@app.route('/api/v1/retirement', methods=['POST'])
def api_calculate_retirement():
    """
    Calculate retirement corpus
    ---
    Request Body:
    {
        "age": 30,                  // Current age
        "retire_age": 60,           // Retirement age
        "saving": 10000,            // Monthly saving amount
        "roi": 12,                  // Expected annual return %
        "expenses": 50000           // Expected monthly expenses after retirement
    }
    """
    try:
        data = request.json
        if not data:
            return api_response(error="Request body is required", status_code=400)
        
        required_fields = ['age', 'retire_age', 'saving', 'roi', 'expenses']
        field_types = {
            'age': int,
            'retire_age': int,
            'saving': float,
            'roi': float,
            'expenses': float
        }
        
        errors = validate_input(data, required_fields, field_types)
        
        # Additional validations
        if data.get('age', 0) >= data.get('retire_age', 0):
            errors.append("Retirement age must be greater than current age")
        
        if errors:
            return api_response(error="Validation errors", message="Invalid input", status_code=400, data={"errors": errors})
        
        age = data['age']
        retire_age = data['retire_age']
        monthly_saving = data['saving']
        annual_roi = data['roi']
        future_expenses = data['expenses']
        
        # Calculate corpus using compound interest
        years_to_retirement = retire_age - age
        months_to_retirement = years_to_retirement * 12
        monthly_roi = annual_roi / 100 / 12
        
        if monthly_roi == 0:
            corpus = monthly_saving * months_to_retirement
        else:
            corpus = monthly_saving * (((1 + monthly_roi) ** months_to_retirement - 1) / monthly_roi) * (1 + monthly_roi)
        
        # Assume 20 years post-retirement life
        post_retirement_years = 20
        required_corpus = future_expenses * 12 * post_retirement_years
        
        status = 'Sufficient' if corpus >= required_corpus else 'Insufficient'
        shortfall = max(0, required_corpus - corpus)
        
        result = {
            'current_age': age,
            'retirement_age': retire_age,
            'years_to_retirement': years_to_retirement,
            'monthly_saving': round(monthly_saving, 2),
            'annual_roi': annual_roi,
            'expected_corpus': round(corpus, 2),
            'required_corpus': round(required_corpus, 2),
            'status': status,
            'shortfall': round(shortfall, 2) if shortfall > 0 else 0,
            'monthly_expenses_post_retirement': round(future_expenses, 2),
            'assumptions': {
                'post_retirement_years': post_retirement_years,
                'inflation_not_considered': True
            }
        }
        
        return api_response(data=result, message="Retirement planning calculated successfully")
        
    except Exception as e:
        return api_response(error=str(e), status_code=500)

# API Documentation endpoint
@app.route('/api/v1/docs')
def api_docs():
    """API Documentation"""
    docs = {
        "title": "Financial Calculator API",
        "version": "1.0.0",
        "description": "REST API for various financial calculations",
        "base_url": request.host_url + "api/v1",
        "endpoints": {
            "POST /api/v1/emi": "Calculate EMI for home loans",
            "POST /api/v1/affordability": "Calculate loan affordability",
            "POST /api/v1/dti": "Calculate debt-to-income ratio",
            "POST /api/v1/gratuity": "Calculate gratuity amount",
            "POST /api/v1/retirement": "Calculate retirement corpus"
        },
        "response_format": {
            "timestamp": "ISO 8601 timestamp",
            "status": "success|error",
            "message": "Response message",
            "data": "Response data object",
            "error": "Error message (only on error)"
        }
    }
    return api_response(data=docs, message="API documentation")

# Legacy calculation functions (for web interface compatibility)
def calculate_emi_legacy(data):
    property_value = float(data.get('property_value', 0))
    down_payment = float(data.get('down_payment', 0))
    if property_value and down_payment:
        principal = property_value - down_payment
    else:
        principal = float(data.get('loan_amount', 0))
    rate = float(data['rate']) / (12 * 100)
    tenure = int(data['tenure'])
    emi = (principal * rate * (1 + rate) ** tenure) / ((1 + rate) ** tenure - 1)
    total_payment = emi * tenure
    total_interest = total_payment - principal
    return jsonify({
        'emi': round(emi, 2),
        'total_payment': round(total_payment, 2),
        'total_interest': round(total_interest, 2),
        'principal': round(principal, 2)
    })

def calculate_affordability_legacy(data):
    income = float(data['income'])
    expenses = float(data['expenses'])
    existing_emis = float(data['existing_emis'])
    down_payment = float(data.get('down_payment', 0))
    max_emi = (income - expenses) * 0.4 - existing_emis
    affordable_loan = max_emi * 60
    affordable_property = affordable_loan + down_payment
    return jsonify({
        'max_emi': round(max_emi, 2),
        'affordable_loan': round(affordable_loan, 2),
        'affordable_property': round(affordable_property, 2),
        'income': round(income, 2),
        'expenses': round(expenses, 2),
        'existing_emis': round(existing_emis, 2),
        'down_payment': round(down_payment, 2),
        'remaining_income': round(income - expenses - existing_emis, 2)
    })

def calculate_dti_legacy(data):
    total_debt = float(data['debt'])
    income = float(data['income'])
    remaining_income = income - total_debt
    dti_ratio = (total_debt / income) * 100
    return jsonify({
        'dti_ratio': round(dti_ratio, 2),
        'risk_level': 'High' if dti_ratio > 40 else 'Moderate' if dti_ratio > 20 else 'Low',
        'income': round(income, 2),
        'debt': round(total_debt, 2),
        'remaining_income': round(remaining_income, 2)
    })

def calculate_gratuity_legacy(data):
    salary = float(data['salary'])
    years = int(data['years'])
    gratuity = (salary * 15 * years) / 26
    return jsonify({'gratuity': round(gratuity, 2)})

def calculate_retirement_legacy(data):
    age = int(data['age'])
    retire_age = int(data['retire_age'])
    monthly_saving = float(data['saving'])
    roi = float(data['roi']) / 100 / 12
    future_expenses = float(data['expenses'])
    
    months = (retire_age - age) * 12
    corpus = monthly_saving * (((1 + roi) ** months - 1) / roi) * (1 + roi)
    
    required_corpus = future_expenses * 12 * 20
    status = 'Sufficient' if corpus >= required_corpus else 'Insufficient'
    
    return jsonify({
        'corpus': round(corpus, 2),
        'required_corpus': round(required_corpus, 2),
        'status': status
    })

# Health check endpoint
@app.route('/api/v1/health')
def health_check():
    return api_response(data={"status": "healthy"}, message="Service is running")



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

