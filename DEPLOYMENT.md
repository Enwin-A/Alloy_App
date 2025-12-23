# Alloy Composition Predictor - Backend API

Flask REST API for predicting aluminum alloy compositions based on target mechanical properties using GP (Genetic Programming) models.

## 🚀 Quick Start

### Local Development

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application:**
   ```bash
   python app.py
   ```

3. **Test the API:**
   The API will be available at `http://localhost:5000`

## 📦 Deployment to Render

### Prerequisites
- [Render account](https://render.com/)
- Your code pushed to GitHub

### Deployment Steps

1. **Push your code to GitHub:**
   ```bash
   cd Alloy_App
   git init
   git add .
   git commit -m "Deploy backend"
   git push origin main
   ```

2. **Create a new Web Service on Render:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** `alloy-predictor-api` (or your choice)
     - **Environment:** Python 3
     - **Region:** Choose closest to your users
     - **Branch:** main
     - **Root Directory:** `Alloy_App` (if deploying from monorepo)
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
     
3. **Add Environment Variables** (optional):
   - `FLASK_ENV=production`
   - `PORT=10000` (Render sets this automatically)

4. **Deploy:**
   - Click "Create Web Service"
   - Wait for build to complete
   - Your API will be available at `https://your-app-name.onrender.com`

## 🌐 Model Storage

**This app uses Hugging Face to host the trained model (.pkl file).**

The model is automatically downloaded from:
```
https://huggingface.co/enwin/alloy_v1/resolve/main/gp_YS_exploration_balanced.pkl
```

**Benefits:**
- ✅ No need to commit large .pkl files to your repo
- ✅ Free hosting on Hugging Face
- ✅ Model is cached in memory after first load
- ✅ Easy to update model without redeploying code

**To use your own model:**
1. Upload your .pkl file to a Hugging Face model repository
2. Update the `HUGGINGFACE_MODEL_URL` in `app.py`:
   ```python
   HUGGINGFACE_MODEL_URL = "https://huggingface.co/YOUR_USERNAME/YOUR_REPO/resolve/main/YOUR_MODEL.pkl"
   ```

**Note:** The URL format must use `/resolve/` (not `/blob/`) to download the raw file.

## 📡 API Endpoints

### POST /api/suggest
Find compositions for a target property value.

**Request:**
```json
{
    "target": "YS",
    "value": 200,
    "tolerance": 0.1,
    "n_suggestions": 10,
    "mode": "balanced"
}
```

**Response:**
```json
{
    "success": true,
    "results": {
        "candidates": [...],
        "model_stats": {...},
        "target_range": {...}
    }
}
```

### POST /api/predict
Predict property from composition and processing.

**Request:**
```json
{
    "target": "YS",
    "composition": {
        "Al": 90.5,
        "Mg": 4.5,
        "Cu": 1.5,
        ...
    },
    "processing": {
        "homog_temp_max_C": 480,
        "homog_time_total_s": 18000,
        ...
    },
    "mode": "balanced"
}
```

**Response:**
```json
{
    "success": true,
    "predicted_value": 205.3,
    "is_valid": true,
    "alloy_series": ["5xxx"]
}
```

### GET /api/health
Health check endpoint.

## 🔧 Project Structure

```
Alloy_App/
├── app.py              # Flask backend API
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .gitignore         # Git ignore rules
├── frontend/          # Legacy static frontend (not used with React)
│   └── index.html
└── models/
    └── balanced/
        └── gp_YS_exploration_balanced.pkl  # Trained GP model
```

## 🌐 CORS Configuration

The backend has CORS enabled for all origins by default. For production, restrict to your frontend domain:

```python
# In app.py
CORS(app, origins=["https://your-app.vercel.app"])
```

## 🐛 Troubleshooting

**Model not found error**: 
- Ensure `.pkl` files are in `models/balanced/` directory
- Check file paths in logs
- Verify Git LFS is working if using it

**Port already in use**: 
- Change port: `app.run(port=5001)`
- Or stop existing process

**CORS errors from frontend**:
- Verify CORS is enabled in app.py
- Check frontend is using correct API URL
- Test API directly with curl/Postman

## 📚 Model Information

The GP model was trained using the exploration framework. It uses:
- **Genetic Programming** for symbolic regression
- **Mixup data augmentation** for training
- **Physics-based constraints** for validation

## 📄 License

MIT
