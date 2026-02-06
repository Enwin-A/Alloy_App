# Hetzner VPS Deployment Guide for Alloy Backend

This guide will walk you through deploying your Flask backend on a Hetzner VPS with Ubuntu and nginx.

## Prerequisites

- Hetzner VPS running Ubuntu
- Nginx installed ✓
- Firewall configured ✓
- Backend code cloned ✓
- Python and dependencies installed ✓

## Step-by-Step Deployment

### 1. Set Up Python Virtual Environment

```bash
cd /root/alloy-app-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

#do this and we did
sudo apt install python3 python3-pip python3-venv
python3 -m venv ~/env/alloy
source ~/env/alloy/bin/activate


# Install dependencies
pip install -r requirements.txt

# Verify gunicorn is installed
gunicorn --version
```

### 2. Test the Application Locally

```bash
# Still in virtual environment
python3 wsgi.py

# In another terminal, test the API
curl http://localhost:5000/health
```

If successful, press Ctrl+C to stop the test server.

### 3. Configure the Systemd Service

```bash
# Copy the service file to systemd directory
sudo cp /root/alloy-app-backend/alloy-backend.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable alloy-backend

# Start the service
sudo systemctl start alloy-backend

# Check service status
sudo systemctl status alloy-backend
```

Expected output should show "active (running)" in green.

### 4. Configure Nginx

```bash
# Edit the nginx config file with your server IP
sudo nano /root/alloy-app-backend/nginx-alloy-backend.conf

# Replace "YOUR_SERVER_IP_OR_DOMAIN" with your actual Hetzner VPS IP address
# Example: server_name 123.45.67.89;

# Copy nginx config to sites-available
sudo cp /root/alloy-app-backend/nginx-alloy-backend.conf /etc/nginx/sites-available/alloy-backend

# Create symbolic link to sites-enabled
sudo ln -s /etc/nginx/sites-available/alloy-backend /etc/nginx/sites-enabled/

# Remove default nginx site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# If test is successful, reload nginx
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx
```

### 5. Update Frontend Environment Variable

In your Vercel frontend project, set the environment variable:

**On Vercel Dashboard:**
1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add a new variable:
   - **Name:** `VITE_API_BASE`
   - **Value:** `http://YOUR_HETZNER_VPS_IP` (e.g., `http://123.45.67.89`)
4. Redeploy your frontend

**Alternative - Update .env locally and push:**
```bash
# In Alloy_App_frontend directory
echo "VITE_API_BASE=http://YOUR_HETZNER_VPS_IP" > .env.production
git add .env.production
git commit -m "Add production API URL"
git push
```

### 6. Verify Deployment

Test the API endpoints:

```bash
# Health check
curl http://YOUR_HETZNER_VPS_IP/health

# Test forward prediction
curl -X POST http://YOUR_HETZNER_VPS_IP/forward_predict \
  -H "Content-Type: application/json" \
  -d '{
    "composition": {
      "Mg": 4.0,
      "Cu": 1.5,
      "Zn": 3.0,
      "Mn": 0.5,
      "Si": 0.8,
      "Fe": 0.2,
      "Al": 89.9
    },
    "processing": {
      "homog_temp_max_C": 480,
      "homog_time_total_s": 18000,
      "recryst_temp_max_C": 320,
      "recryst_time_total_s": 9000,
      "Cold rolling reduction (percentage)": 60,
      "Hot rolling reduction (percentage)": 70
    }
  }'
```

### 7. Useful Commands for Management

```bash
# Check service logs
sudo journalctl -u alloy-backend -f

# Restart the backend service
sudo systemctl restart alloy-backend

# Stop the backend service
sudo systemctl stop alloy-backend

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

### 8. Update Backend Code (Future Updates)

```bash
# Navigate to backend directory
cd /root/alloy-app-backend

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies if needed
pip install -r requirements.txt

# Restart the service
sudo systemctl restart alloy-backend

# Check status
sudo systemctl status alloy-backend
```

## Troubleshooting

### Service won't start
```bash
# Check detailed logs
sudo journalctl -u alloy-backend -n 50 --no-pager

# Check if port 5000 is already in use
sudo netstat -tulpn | grep 5000

# Verify Python path and permissions
ls -la /root/alloy-app-backend/venv/bin/
```

### Nginx errors
```bash
# Check nginx configuration syntax
sudo nginx -t

# View error logs
sudo tail -50 /var/log/nginx/error.log

# Ensure nginx is running
sudo systemctl status nginx
```

### CORS errors on frontend
1. Verify the CORS configuration in [app.py](Alloy_App/app.py)
2. Check nginx CORS headers in the config file
3. Ensure Vercel frontend URL matches exactly (no trailing slash)

### Connection refused
```bash
# Check if firewall allows HTTP traffic
sudo ufw status

# Ensure the backend service is running
sudo systemctl status alloy-backend

# Check if nginx is forwarding correctly
curl http://localhost:5000/health
```

## Security Recommendations (Optional but Recommended)

### 1. Set Up SSL/HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Certbot will automatically update nginx config
```

### 2. Set Up a Non-Root User

```bash
# Create new user
sudo adduser alloyuser

# Update service file to use new user
sudo nano /etc/systemd/system/alloy-backend.service
# Change: User=alloyuser

# Move project files
sudo mv /root/alloy-app-backend /home/alloyuser/
sudo chown -R alloyuser:alloyuser /home/alloyuser/alloy-app-backend

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart alloy-backend
```

## Architecture Overview

```
┌─────────────────┐
│  Vercel Frontend │  (React + Vite)
│  Port: 443/HTTPS │  https://alloy-app-frontend.vercel.app
└────────┬────────┘
         │ HTTPS Requests
         ▼
┌─────────────────┐
│  Hetzner VPS    │
│  ┌───────────┐  │
│  │  Nginx    │  │  Reverse Proxy
│  │  Port: 80 │  │  (Handles CORS, SSL)
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Gunicorn  │  │  WSGI Server
│  │ Port: 5000│  │  (3 workers)
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │Flask App  │  │  API Logic
│  │ + ML Model│  │  (Prediction Engine)
│  └───────────┘  │
└─────────────────┘
```

## Next Steps

1. ✅ Complete basic deployment
2. ⏩ Set up domain name (optional)
3. ⏩ Enable HTTPS with SSL certificate
4. ⏩ Set up monitoring and logging
5. ⏩ Configure automatic backups

## Support

If you encounter issues:
1. Check service logs: `sudo journalctl -u alloy-backend -f`
2. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify firewall settings: `sudo ufw status`
4. Test API locally: `curl http://localhost:5000/health`
