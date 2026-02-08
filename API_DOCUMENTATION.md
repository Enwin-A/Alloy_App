# Alloy Backend API Documentation

Complete API reference for the Alloy Composition Predictor backend.

## Base URL

- **Local Development**: `http://localhost:5000`
- **Production**: `https://api.alloydesign.org`

## Endpoints

### 1. Health Check

Check if the API is running.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-08T12:34:56.789012",
  "service": "alloy-api"
}
```

---

### 2. Forward Prediction (Predict Properties)

Predict yield strength or ultimate tensile strength for a given alloy composition.

**Endpoint**: `POST /api/predict`

**Request Body**:
```json
{
  "target": "YS",
  "composition": {
    "Al": 97.9,
    "Mg": 1.0,
    "Si": 0.6,
    "Cu": 0.28,
    "Cr": 0.2,
    "Fe": 0.0,
    "Mn": 0.0,
    "Ni": 0.0,
    "Zn": 0.0,
    "Ti": 0.0,
    "Zr": 0.0,
    "Sc": 0.0,
    "Other": 0.02
  },
  "processing": {
    "homog_temp_max_C": 480,
    "homog_time_total_s": 18000,
    "recryst_temp_max_C": 320,
    "recryst_time_total_s": 9000,
    "Cold rolling reduction (percentage)": 60,
    "Hot rolling reduction (percentage)": 70
  },
  "mode": "balanced"
}
```

**Parameters**:
- `target` (string, required): Property to predict
  - `"YS"` - Yield Strength (MPa)
  - `"UTS"` - Ultimate Tensile Strength (MPa)
- `composition` (object, required): Element percentages (wt%)
  - All elements should sum to ~100%
  - Missing elements default to 0
- `processing` (object, optional): Processing parameters
  - `homog_temp_max_C`: Homogenization temperature (°C)
  - `homog_time_total_s`: Homogenization time (seconds)
  - `recryst_temp_max_C`: Recrystallization temperature (°C)
  - `recryst_time_total_s`: Recrystallization time (seconds)
  - `Cold rolling reduction (percentage)`: Cold rolling reduction (%)
  - `Hot rolling reduction (percentage)`: Hot rolling reduction (%)
- `mode` (string, optional): Model mode
  - `"balanced"` (default)

**Success Response** (200 OK):
```json
{
  "success": true,
  "target": "YS",
  "predicted_value": 275.34,
  "is_valid": true,
  "violations": [],
  "alloy_series": ["6xxx (Mg-Si (extrusions))"],
  "inputs": {
    "composition": {
      "Al": 97.9,
      "Mg": 1.0,
      "Si": 0.6,
      ...
    },
    "processing": {
      "homog_temp_max_C": 480,
      ...
    }
  }
}
```

**Error Response** (500):
```json
{
  "error": "Error message description"
}
```

**Example cURL**:
```bash
curl -X POST https://api.alloydesign.org/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "target": "YS",
    "composition": {
      "Al": 97.9,
      "Mg": 1.0,
      "Si": 0.6,
      "Cu": 0.28,
      "Cr": 0.2
    },
    "processing": {
      "homog_temp_max_C": 480,
      "homog_time_total_s": 18000
    }
  }'
```

**Example JavaScript (Frontend)**:
```javascript
const response = await fetch(`${API_BASE}/api/predict`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target: 'YS',
    composition: {
      Al: 97.9,
      Mg: 1.0,
      Si: 0.6,
      Cu: 0.28,
      Cr: 0.2,
      Fe: 0.0,
      Mn: 0.0,
      Ni: 0.0,
      Zn: 0.0,
      Ti: 0.0,
      Zr: 0.0,
      Sc: 0.0,
      Other: 0.02
    },
    processing: {
      homog_temp_max_C: 480,
      homog_time_total_s: 18000,
      recryst_temp_max_C: 320,
      recryst_time_total_s: 9000,
      'Cold rolling reduction (percentage)': 60,
      'Hot rolling reduction (percentage)': 70
    },
    mode: 'balanced'
  })
});

const data = await response.json();
console.log('Predicted YS:', data.predicted_value, 'MPa');
```

---

### 3. Reverse Engineering (Suggest Compositions)

Find alloy compositions that achieve a target property value.

**Endpoint**: `POST /api/suggest`

**Request Body**:
```json
{
  "target": "YS",
  "value": 300,
  "tolerance": 0.1,
  "n_suggestions": 10,
  "mode": "balanced"
}
```

**Parameters**:
- `target` (string, required): Property target
  - `"YS"` - Yield Strength
  - `"UTS"` - Ultimate Tensile Strength
- `value` (number, required): Target value in MPa (0-1000)
- `tolerance` (number, optional): Tolerance as decimal (default: 0.1 = 10%)
- `n_suggestions` (number, optional): Number of suggestions to return (default: 10)
- `mode` (string, optional): Model mode (default: "balanced")

**Success Response** (200 OK):
```json
{
  "success": true,
  "target": "YS",
  "target_value": 300,
  "tolerance": 0.1,
  "results": {
    "candidates": [
      {
        "composition": {
          "Al": 92.5,
          "Mg": 4.0,
          "Cu": 1.5,
          "Zn": 1.8,
          ...
        },
        "predicted_value": 298.5,
        "error": 1.5,
        "error_pct": 0.5,
        "is_valid": true,
        "violations": [],
        "source": "optimization",
        "alloy_series": ["7xxx (Zn-based (aerospace))"]
      },
      ...
    ],
    "model_stats": {
      "pred_min": 120.5,
      "pred_max": 450.2,
      "pred_mean": 285.3,
      "in_range": true
    },
    "target_range": {
      "low": 270,
      "high": 330
    }
  },
  "timestamp": "2026-02-08T12:34:56.789012"
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Target must be YS or UTS"
}
```

**Error Response** (404 Not Found):
```json
{
  "error": "Model not found: ..."
}
```

**Error Response** (500 Internal Server Error):
```json
{
  "error": "Error message description"
}
```

**Example cURL**:
```bash
curl -X POST https://api.alloydesign.org/api/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "target": "YS",
    "value": 300,
    "tolerance": 0.1,
    "n_suggestions": 10
  }'
```

**Example JavaScript (Frontend)**:
```javascript
const response = await fetch(`${API_BASE}/api/suggest`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target: 'YS',
    value: 300,
    tolerance: 0.1,
    n_suggestions: 10,
    mode: 'balanced'
  })
});

const data = await response.json();
if (data.success) {
  const candidates = data.results.candidates;
  console.log(`Found ${candidates.length} compositions`);
  candidates.forEach((cand, i) => {
    console.log(`${i+1}. Predicted: ${cand.predicted_value} MPa`);
  });
}
```

---

## Data Types

### Composition Object
All element percentages in weight percent (wt%). Must sum to ~100%.

```typescript
interface Composition {
  Al: number;   // Aluminum (base element, 85-99.5%)
  Mg: number;   // Magnesium (0-6%)
  Si: number;   // Silicon (0-1.5%)
  Cu: number;   // Copper (0-5%)
  Mn: number;   // Manganese (0-1.5%)
  Fe: number;   // Iron (0-0.5%)
  Cr: number;   // Chromium (0-0.35%)
  Ni: number;   // Nickel (0-0.1%)
  Zn: number;   // Zinc (0-8%)
  Ti: number;   // Titanium (0-0.2%)
  Zr: number;   // Zirconium (0-0.25%)
  Sc: number;   // Scandium (0-0.5%)
  Other: number;  // Other elements (0-0.15%)
}
```

### Processing Object
Optional processing parameters.

```typescript
interface Processing {
  homog_temp_max_C: number;  // 400-580°C
  homog_time_total_s: number;  // 3600-72000s (1-20 hours)
  recryst_temp_max_C: number;  // 300-550°C
  recryst_time_total_s: number;  // 60-36000s (1min-10 hours)
  'Cold rolling reduction (percentage)': number;  // 0-90%
  'Hot rolling reduction (percentage)': number;  // 0-99%
}
```

### Candidate Object
A suggested composition from reverse engineering.

```typescript
interface Candidate {
  composition: Composition;
  predicted_value: number;  // Predicted property value (MPa)
  error: number;  // Absolute error from target (MPa)
  error_pct: number;  // Percentage error
  is_valid: boolean;  // Passes all constraints
  violations: string[];  // List of constraint violations
  source: 'training_data' | 'random_scan' | 'optimization';
  alloy_series: string[];  // e.g., ["6xxx (Mg-Si (extrusions))"]
  actual_value?: number;  // Actual value if from training data
}
```

---

## Common Use Cases

### Use Case 1: Design a High-Strength Aerospace Alloy

Goal: Find compositions with YS > 400 MPa.

```javascript
const response = await fetch(`${API_BASE}/api/suggest`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target: 'YS',
    value: 400,
    tolerance: 0.05,  // ±5%
    n_suggestions: 20
  })
});

const data = await response.json();
const validCandidates = data.results.candidates.filter(c => c.is_valid);
console.log(`Found ${validCandidates.length} valid high-strength compositions`);
```

### Use Case 2: Predict Properties of Known Alloy (6061)

Goal: Predict YS of 6061-T6 aluminum.

```javascript
const response = await fetch(`${API_BASE}/api/predict`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target: 'YS',
    composition: {
      Al: 97.9,
      Mg: 1.0,
      Si: 0.6,
      Cu: 0.28,
      Cr: 0.2,
      Fe: 0.0,
      Mn: 0.0,
      Ni: 0.0,
      Zn: 0.0,
      Ti: 0.0,
      Zr: 0.0,
      Sc: 0.0,
      Other: 0.02
    },
    processing: {
      homog_temp_max_C: 480,
      homog_time_total_s: 18000
    }
  })
});

const data = await response.json();
console.log(`Predicted YS: ${data.predicted_value} MPa`);
// Expected: ~275 MPa (6061-T6 actual: ~276 MPa)
```

---

## Error Handling

All endpoints return JSON. Check the `success` field or HTTP status code.

### Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Model not found
- `500 Internal Server Error` - Server error

### Example Error Handling

```javascript
try {
  const response = await fetch(`${API_BASE}/api/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  
  if (!response.ok || data.error || data.success === false) {
    throw new Error(data.error || 'Request failed');
  }

  // Success - use data
  console.log('Result:', data);
  
} catch (error) {
  console.error('API Error:', error.message);
}
```

---

## CORS Configuration

The API allows requests from:
- `https://alloydesign.org` (production frontend)
- `https://www.alloydesign.org` (production frontend www)
- `http://localhost:5173` (local Vite development)
- `http://localhost:5000` (local Flask development)

If deploying to a different origin, update the CORS configuration in `app.py`.

---

## Rate Limiting

Currently no rate limiting is enforced. For production, consider:
- Cloudflare rate limiting (if using Cloudflare proxy)
- Flask-Limiter extension
- Nginx rate limiting

---

## Testing

Use the included test script:

```bash
# Test locally
python test_api.py

# Test production
# Edit test_api.py and change API_BASE to https://api.alloydesign.org
python test_api.py
```

Or test with cURL:

```bash
# Health check
curl https://api.alloydesign.org/health

# Predict
curl -X POST https://api.alloydesign.org/api/predict \
  -H "Content-Type: application/json" \
  -d '{"target":"YS","composition":{"Al":97.9,"Mg":1.0,"Si":0.6}}'

# Suggest
curl -X POST https://api.alloydesign.org/api/suggest \
  -H "Content-Type: application/json" \
  -d '{"target":"YS","value":300,"tolerance":0.1}'
```

---

## Model Information

The API uses Gaussian Process models trained on aluminum alloy datasets:
- **Model Storage**: HuggingFace (`enwin/alloy_v1`)
- **Features**: 13 composition elements + 6 processing parameters
- **Targets**: YS (Yield Strength) and UTS (Ultimate Tensile Strength)
- **Uncertainty**: Models provide prediction uncertainties (not exposed in API yet)

---

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u alloy-backend -f`
2. Review nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Test API locally before production
4. Ensure models are downloaded from HuggingFace

---

Last updated: February 8, 2026
