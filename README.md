# Alloy Composition Predictor Web Application

A simple web interface for predicting aluminum alloy compositions based on target mechanical properties using GP (Genetic Programming) models.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**


## Usage

1. Select the target property (YS or UTS)
2. Enter your target value in MPa (e.g., 200)
3. Select tolerance (how much deviation is acceptable)
4. Click "Find Compositions"
5. Review the suggested compositions

### Advanced Options

- **Number of Results**: How many candidate compositions to return

## API Endpoints

### POST /api/suggest
Find compositions for a target property value.

```json
{
    "target": "YS",
    "value": 200,
    "tolerance": 0.1,
    "n_suggestions": 10,
    "mode": "balanced"
}
```



### GET /api/health
Health check endpoint.

## Project Structure

```
webapplication/
├── app.py              # Flask backend API
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── frontend/
│   └── index.html     # Web interface
└── models/
    └── balanced/
        └── gp_YS_exploration_balanced.pkl  # Trained GP model
```

## Model Information

The GP model was trained using the exploration framework in `experiments/06_exploration/`. It uses:

- **Genetic Programming** for symbolic regression
- **Mixup data augmentation** for training
- **Physics-based constraints** for validation


## Troubleshooting

**Model not found error**: Ensure the `.pkl` files are in the `models/` or `models/balanced/` directory.

**Port already in use**: Change the port in `app.py` or stop the existing process.
