# Quick Deployment Checklist

## Current Status
- ✅ Nginx installed
- ✅ Firewall configured (OpenSSH, Nginx Full)
- ✅ Backend cloned to `/root/alloy-app-backend`
- ✅ Python and pip installed
- ✅ Dependencies installed with pip
- ⏩ Need to set up virtual environment properly
- ⏩ Need to configure systemd service
- ⏩ Need to configure nginx reverse proxy

## Commands to Run Now

### 1. Set up Virtual Environment (5 minutes)
```bash
cd /root/alloy-app-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 2. Copy Service File (1 minute)
```bash
sudo cp /root/alloy-app-backend/alloy-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable alloy-backend
sudo systemctl start alloy-backend
sudo systemctl status alloy-backend
```

### 3. Get Your Server IP
```bash
curl ifconfig.me
# Note down this IP address
```

### 4. Configure Nginx (3 minutes)
```bash
# Edit the config and replace YOUR_SERVER_IP_OR_DOMAIN with your actual IP
sudo nano /root/alloy-app-backend/nginx-alloy-backend.conf

# Then:
sudo cp /root/alloy-app-backend/nginx-alloy-backend.conf /etc/nginx/sites-available/alloy-backend
sudo ln -s /etc/nginx/sites-available/alloy-backend /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Test Your API
```bash
# Replace YOUR_IP with your actual server IP
curl http://YOUR_IP/health
```

### 6. Update Vercel Environment Variable
- Go to Vercel Dashboard → Your Project → Settings → Environment Variables
- Add: `VITE_API_BASE` = `http://YOUR_SERVER_IP`
- Redeploy the frontend

## Verification Steps

1. Backend service running:
   ```bash
   sudo systemctl status alloy-backend
   ```
   Should show "active (running)"

2. Nginx running:
   ```bash
   sudo systemctl status nginx
   ```
   Should show "active (running)"

3. API responding:
   ```bash
   curl http://YOUR_IP/health
   ```
   Should return: `{"status":"healthy",...}`

4. Frontend can connect:
   - Open https://alloy-app-frontend.vercel.app
   - Try making a prediction
   - Check browser console for errors

## If Something Goes Wrong

View logs:
```bash
# Backend logs
sudo journalctl -u alloy-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

Restart services:
```bash
sudo systemctl restart alloy-backend
sudo systemctl restart nginx
```

## Files Created

1. `wsgi.py` - Entry point for Gunicorn
2. `alloy-backend.service` - Systemd service configuration
3. `nginx-alloy-backend.conf` - Nginx reverse proxy configuration
4. `HETZNER_DEPLOYMENT.md` - Full deployment guide

## Total Time: ~10-15 minutes
