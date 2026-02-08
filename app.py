#!/usr/bin/env python3
"""
Flask API for Alloy Composition Suggestion

A simple web API that wraps the constrain_and_suggest functionality
for easy testing via a web interface.
"""

import io
import json
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from scipy.optimize import differential_evolution

warnings.filterwarnings('ignore')

# Flask app (API only - frontend is separate React app)
app = Flask(__name__)
# Configure CORS to allow requests from Vercel frontend and custom domain
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://alloydesign.org",             # Production domain
            "https://www.alloydesign.org",         # Production domain (www)
            "https://alloy-app-frontend.vercel.app",  # Vercel preview
            "http://localhost:5173",               # Local development (Vite)
            "http://localhost:5000"                # Local development (Flask)
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
BASE_DIR = Path(__file__).parent

# Hugging Face model URL
# Hugging Face model URL (use resolve to get the actual binary, not the Git LFS pointer)
HUGGINGFACE_MODEL_URL = "https://huggingface.co/enwin/alloy_v1/resolve/main/gp_YS_exploration_balanced.pkl"

# Element indices (must match feature order in training)
ELEMENT_INDICES = {
    'Al': 0, 'Si': 1, 'Fe': 2, 'Cu': 3, 'Mn': 4, 'Mg': 5,
    'Cr': 6, 'Ni': 7, 'Zn': 8, 'Ti': 9, 'Zr': 10, 'Sc': 11, 'Other': 12
}

# Practical composition limits (wt%)
COMPOSITION_LIMITS = {
    'Al': (85.0, 99.5),
    'Si': (0.0, 1.5),
    'Fe': (0.0, 0.5),
    'Cu': (0.0, 5.0),
    'Mn': (0.0, 1.5),
    'Mg': (0.0, 6.0),
    'Cr': (0.0, 0.35),
    'Ni': (0.0, 0.1),
    'Zn': (0.0, 8.0),
    'Ti': (0.0, 0.2),
    'Zr': (0.0, 0.25),
    'Sc': (0.0, 0.5),
    'Other': (0.0, 0.15),
}

# Processing parameter typical ranges
PROCESSING_LIMITS = {
    'homog_temp_max_C': (400, 580),
    'homog_time_total_s': (3600, 72000),
    'recryst_temp_max_C': (300, 550),
    'recryst_time_total_s': (60, 36000),
    'Cold rolling reduction (percentage)': (0, 90),
    'Hot rolling reduction (percentage)': (0, 99),
}

# Alloy series info
ALLOY_SERIES = {
    '2xxx': {'Cu': (2.0, 5.0), 'Mg': (0.0, 2.0), 'name': 'Cu-based (aerospace)'},
    '5xxx': {'Mg': (2.0, 6.0), 'Cu': (0.0, 0.5), 'name': 'Mg-based (marine)'},
    '6xxx': {'Mg': (0.5, 1.5), 'Si': (0.5, 1.5), 'name': 'Mg-Si (extrusions)'},
    '7xxx': {'Zn': (4.0, 8.0), 'Mg': (1.0, 3.0), 'name': 'Zn-based (aerospace)'},
}

# Cache for loaded models
_model_cache = {}


# =============================================================================
# MODEL FUNCTIONS
# =============================================================================

def load_model(target_name, mode='balanced'):
    """Load trained GP model from Hugging Face cache or download."""
    cache_key = f"{target_name}_{mode}"
    
    # Check cache first
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    def _download_model_bytes(url: str) -> bytes:
        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": "alloy-gp-backend/1.0",
        }
        resp = requests.get(url, timeout=60, allow_redirects=True, headers=headers)
        resp.raise_for_status()
        content = resp.content

        # Basic sanity checks to avoid trying to unpickle HTML/text
        if not content or len(content) < 32:
            raise ValueError("Downloaded model is unexpectedly small; check the URL or permissions.")
        if not content.startswith(b"\x80"):
            preview = content[:32]
            raise ValueError(
                f"Downloaded content is not a pickle (starts with {preview!r}); verify the Hugging Face URL and that the repo/file is public."
            )
        return content

    # Download from Hugging Face
    try:
        print(f"Downloading model for {target_name} ({mode}) from Hugging Face...")
        model_bytes = _download_model_bytes(HUGGINGFACE_MODEL_URL)

        # Load model from downloaded bytes
        results = pickle.load(io.BytesIO(model_bytes))
        
        # Cache the model
        _model_cache[cache_key] = results
        print("Model loaded successfully and cached.")
        
        return results
        
    except requests.RequestException as e:
        raise FileNotFoundError(f"Failed to download model from Hugging Face: {str(e)}")
    except pickle.UnpicklingError as e:
        raise ValueError(f"Failed to load model file: {str(e)}")


def predict_property(model, scaler, composition_vector):
    """Predict property from composition vector."""
    X_scaled = scaler.transform(composition_vector.reshape(1, -1))
    return model.predict(X_scaled)[0]


def objective_function(x, model, scaler, target_value, feature_names):
    """Objective: minimize difference from target property value."""
    try:
        predicted = predict_property(model, scaler, x)
        return (predicted - target_value) ** 2
    except:
        return 1e10


def apply_composition_constraints(x, feature_names):
    """Check if composition satisfies all constraints."""
    violations = []
    
    # Check element limits
    for elem, idx in ELEMENT_INDICES.items():
        if elem in feature_names:
            feat_idx = feature_names.index(elem) if elem in feature_names else -1
            if feat_idx >= 0 and feat_idx < len(x):
                val = x[feat_idx]
                lo, hi = COMPOSITION_LIMITS.get(elem, (0, 100))
                if val < lo or val > hi:
                    violations.append(f"{elem}={val:.2f}% outside [{lo}, {hi}]%")
    
    # Check sum approximately 100%
    comp_sum = sum(x[feature_names.index(e)] for e in ELEMENT_INDICES.keys() 
                   if e in feature_names and feature_names.index(e) < len(x))
    if abs(comp_sum - 100) > 1.0:
        violations.append(f"Composition sum={comp_sum:.1f}%, should be ~100%")
    
    # Check total alloying < 15%
    alloying_elements = ['Cu', 'Mg', 'Zn', 'Mn', 'Si']
    total_alloying = sum(x[feature_names.index(e)] for e in alloying_elements 
                         if e in feature_names and feature_names.index(e) < len(x))
    if total_alloying > 15:
        violations.append(f"Total alloying={total_alloying:.1f}% > 15%")
    
    return len(violations) == 0, violations


def identify_alloy_series(comp_dict):
    """Identify which alloy series a composition might belong to."""
    matches = []
    
    for series, constraints in ALLOY_SERIES.items():
        match = True
        for elem, value in constraints.items():
            if elem == 'name':
                continue
            lo, hi = value  # Unpack tuple separately
            val = comp_dict.get(elem, 0)
            if val < lo or val > hi:
                match = False
                break
        if match:
            matches.append(f"{series} ({constraints.get('name', '')})")
    
    return matches if matches else ['Custom/Novel']


def normalize_composition(x, feature_names):
    """
    Normalize composition so elements sum to 100% by adjusting Al.
    
    Al is the base element in aluminum alloys, so we adjust it to balance.
    This ensures physically valid compositions.
    """
    x_normalized = x.copy()
    
    # Find Al index
    if 'Al' not in feature_names:
        return x_normalized
    
    al_idx = feature_names.index('Al')
    
    # Calculate sum of all composition elements (excluding processing params)
    comp_elements = ['Al', 'Si', 'Fe', 'Cu', 'Mn', 'Mg', 'Cr', 'Ni', 'Zn', 'Ti', 'Zr', 'Sc', 'Other']
    
    # Sum of non-Al elements
    non_al_sum = 0
    for elem in comp_elements:
        if elem == 'Al':
            continue
        if elem in feature_names:
            idx = feature_names.index(elem)
            if idx < len(x_normalized):
                non_al_sum += x_normalized[idx]
    
    # Set Al to make total = 100%
    target_al = 100.0 - non_al_sum
    
    # Clamp Al to valid range
    al_lo, al_hi = COMPOSITION_LIMITS.get('Al', (85.0, 99.5))
    target_al = max(al_lo, min(al_hi, target_al))
    
    x_normalized[al_idx] = target_al
    
    # If still not 100%, scale down alloying elements proportionally
    current_sum = target_al + non_al_sum
    if abs(current_sum - 100) > 0.5 and non_al_sum > 0:
        # Need to scale down non-Al elements
        scale_factor = (100.0 - target_al) / non_al_sum if non_al_sum > 0 else 1.0
        for elem in comp_elements:
            if elem == 'Al':
                continue
            if elem in feature_names:
                idx = feature_names.index(elem)
                if idx < len(x_normalized):
                    x_normalized[idx] *= scale_factor
    
    return x_normalized


def suggest_compositions(target_name, target_value, model_results, 
                        n_suggestions=10, tolerance=0.1):
    """
    Suggest compositions that achieve target property value.
    EXACT copy of CLI constrain_and_suggest.py behavior.
    """
    model = model_results['best_model']
    scaler = model_results['scaler']
    feature_names = model_results['feature_names']
    
    target_lo = target_value * (1 - tolerance)
    target_hi = target_value * (1 + tolerance)
    
    candidates = []
    
    # Set up bounds for optimization
    bounds = []
    for feat in feature_names:
        if feat in COMPOSITION_LIMITS:
            bounds.append(COMPOSITION_LIMITS[feat])
        elif feat in PROCESSING_LIMITS:
            bounds.append(PROCESSING_LIMITS[feat])
        else:
            bounds.append((0, 1))
    
    # ==========================================================================
    # STRATEGY 1: Search training data for close matches (EXACT CLI behavior)
    # ==========================================================================
    try:
        # Map target name to column
        target_col = 'YS (MPa)' if target_name == 'YS' else 'UTS (MPa)'
        
        # Try to load training data from various locations
        possible_paths = [
            BASE_DIR.parent / 'Alloy_GP' / 'synth_out' / target_name / 'mixup.csv',
            BASE_DIR.parent / 'Alloy_GP - Copy' / 'synth_out' / target_name / 'mixup.csv',
            BASE_DIR / 'data' / f'{target_name}_mixup.csv',
        ]
        
        df = None
        for data_path in possible_paths:
            if data_path.exists():
                df = pd.read_csv(data_path)
                break
        
        if df is not None and target_col in df.columns:
            # Find rows with target values in range
            mask = (df[target_col] >= target_lo) & (df[target_col] <= target_hi)
            close_rows = df[mask]
            
            if len(close_rows) > 0:
                for idx, row in close_rows.head(min(10, len(close_rows))).iterrows():
                    x = np.array([row[f] if f in row else 0 for f in feature_names])
                    predicted = predict_property(model, scaler, x)
                    actual = row[target_col]
                    
                    is_valid, violations = apply_composition_constraints(x, feature_names)
                    comp_dict = {feat: float(x[i]) for i, feat in enumerate(feature_names)}
                    
                    candidate = {
                        'composition': comp_dict,
                        'predicted_value': float(predicted),
                        'actual_value': float(actual),
                        'error': float(abs(predicted - target_value)),
                        'error_pct': float(abs(predicted - target_value) / target_value * 100),
                        'is_valid': is_valid,
                        'violations': violations,
                        'source': 'training_data',
                        'alloy_series': identify_alloy_series(comp_dict)
                    }
                    candidates.append(candidate)
    except Exception:
        pass  # Skip if training data not available
    
    # ==========================================================================
    # STRATEGY 2: Random scan (EXACT CLI behavior - 500 samples, seed 42)
    # ==========================================================================
    np.random.seed(42)
    n_samples = 500
    predictions = []
    sample_points = []
    
    for _ in range(n_samples):
        x = np.array([np.random.uniform(lo, hi) for lo, hi in bounds])
        try:
            pred = predict_property(model, scaler, x)
            predictions.append(pred)
            sample_points.append(x)
        except:
            pass
    
    # Get model stats
    model_stats = {}
    if predictions:
        model_stats = {
            'pred_min': float(min(predictions)),
            'pred_max': float(max(predictions)),
            'pred_mean': float(np.mean(predictions)),
            'in_range': target_lo <= float(np.mean(predictions)) <= target_hi or 
                       any(target_lo <= p <= target_hi for p in predictions)
        }
        
        # Find samples close to target
        for pred, x in zip(predictions, sample_points):
            if target_lo <= pred <= target_hi:
                is_valid, violations = apply_composition_constraints(x, feature_names)
                comp_dict = {feat: float(x[i]) for i, feat in enumerate(feature_names)}
                
                candidate = {
                    'composition': comp_dict,
                    'predicted_value': float(pred),
                    'error': float(abs(pred - target_value)),
                    'error_pct': float(abs(pred - target_value) / target_value * 100),
                    'is_valid': is_valid,
                    'violations': violations,
                    'source': 'random_scan',
                    'alloy_series': identify_alloy_series(comp_dict)
                }
                candidates.append(candidate)
    
    # ==========================================================================
    # STRATEGY 3: Optimization (EXACT CLI behavior)
    # ==========================================================================
    n_opt_attempts = max(30, n_suggestions * 3)
    
    for attempt in range(n_opt_attempts):
        if len(candidates) >= n_suggestions * 2:
            break
        
        try:
            result = differential_evolution(
                objective_function,
                bounds,
                args=(model, scaler, target_value, feature_names),
                maxiter=200,
                seed=42 + attempt,
                disp=False,
                tol=0.001,
                mutation=(0.5, 1.5),
                recombination=0.7,
                polish=True
            )
            
            if result.success or result.fun < (target_value * tolerance) ** 2:
                x = result.x
                predicted = predict_property(model, scaler, x)
                
                if abs(predicted - target_value) / target_value <= tolerance * 1.5:
                    is_valid, violations = apply_composition_constraints(x, feature_names)
                    comp_dict = {feat: float(x[i]) for i, feat in enumerate(feature_names)}
                    
                    candidate = {
                        'composition': comp_dict,
                        'predicted_value': float(predicted),
                        'error': float(abs(predicted - target_value)),
                        'error_pct': float(abs(predicted - target_value) / target_value * 100),
                        'is_valid': is_valid,
                        'violations': violations,
                        'source': 'optimization',
                        'alloy_series': identify_alloy_series(comp_dict)
                    }
                    candidates.append(candidate)
        except Exception:
            pass
    
    # ==========================================================================
    # Deduplicate and sort (EXACT CLI behavior)
    # ==========================================================================
    unique_candidates = []
    for cand in candidates:
        is_dup = False
        for existing in unique_candidates:
            diff = sum(abs(cand['composition'].get(f, 0) - existing['composition'].get(f, 0)) 
                      for f in feature_names[:13])
            if diff < 1.0:
                is_dup = True
                break
        if not is_dup:
            unique_candidates.append(cand)
    
    # Sort by validity, then by error
    unique_candidates.sort(key=lambda c: (not c['is_valid'], c['error']))
    
    return {
        'candidates': unique_candidates[:n_suggestions],
        'model_stats': model_stats,
        'target_range': {'low': target_lo, 'high': target_hi}
    }


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def root():
    """API root - returns basic info."""
    return jsonify({
        'name': 'Alloy Composition Predictor API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health',
            'suggest': '/api/suggest (POST)',
            'predict': '/api/predict (POST)'
        },
        'frontend': 'Deployed separately on Vercel',
        'docs': 'See README.md for API documentation'
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/suggest', methods=['POST'])
def suggest():
    """
    Main API endpoint: suggest compositions for a target property value.
    
    Request body:
        {
            "target": "YS" or "UTS",
            "value": float (in MPa),
            "tolerance": float (default 0.1 = 10%),
            "n_suggestions": int (default 10),
            "mode": str (default "balanced")
        }
    """
    try:
        data = request.get_json()
        
        target = data.get('target', 'YS')
        value = float(data.get('value', 200))
        tolerance = float(data.get('tolerance', 0.1))
        n_suggestions = int(data.get('n_suggestions', 10))
        mode = data.get('mode', 'balanced')
        
        # Validate inputs
        if target not in ['YS', 'UTS']:
            return jsonify({'error': 'Target must be YS or UTS'}), 400
        
        if value <= 0 or value > 1000:
            return jsonify({'error': 'Value must be between 0 and 1000 MPa'}), 400
        
        # Load model
        try:
            model_results = load_model(target, mode)
        except FileNotFoundError as e:
            return jsonify({'error': f'Model not found: {str(e)}'}), 404
        
        # Get suggestions
        results = suggest_compositions(
            target, value, model_results,
            n_suggestions=n_suggestions,
            tolerance=tolerance
        )
        
        return jsonify({
            'success': True,
            'target': target,
            'target_value': value,
            'tolerance': tolerance,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Predict property value for a given composition.
    
    Request body:
        {
            "target": "YS" or "UTS",
            "composition": {
                "Al": 95.0,
                "Mg": 3.0,
                ...
            },
            "mode": str (default "balanced")
        }
    """
    try:
        data = request.get_json()
        
        target = data.get('target', 'YS')
        composition = data.get('composition', {}) or {}
        processing = data.get('processing', {}) or {}
        mode = data.get('mode', 'balanced')
        
        # Load model
        model_results = load_model(target, mode)
        model = model_results['best_model']
        scaler = model_results['scaler']
        feature_names = model_results['feature_names']
        
        # Merge composition and processing inputs
        inputs = {**processing, **composition}

        # Build feature vector matching training order
        x = np.array([float(inputs.get(f, 0.0)) for f in feature_names])
        
        # Predict
        predicted = predict_property(model, scaler, x)
        
        # Check constraints
        is_valid, violations = apply_composition_constraints(x, feature_names)
        
        return jsonify({
            'success': True,
            'target': target,
            'predicted_value': float(predicted),
            'is_valid': is_valid,
            'violations': violations,
            'alloy_series': identify_alloy_series(composition),
            'inputs': {
                'composition': composition,
                'processing': processing
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'], endpoint='health_monitor')
def health_monitor():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'alloy-api'
    }), 200


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    import os
    
    print("\n" + "="*60)
    print("ALLOY COMPOSITION SUGGESTION API")
    print("="*60)
    print(f"\nModel directory: {HUGGINGFACE_MODEL_URL}")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    
    # Use environment PORT for Render deployment
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') != 'production'
    
    print(f"\nStarting server on port {port}")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
