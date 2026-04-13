# Troubleshooting Android App Connection Issues

## Problem: "не могу подключиться к серверу" (Cannot connect to server)

### Quick Checklist

1. **Server is Running**
   ```bash
   # On GCP VM, check if Docker container is running:
   docker ps | grep automuvie

   # Check if port 8080 is listening:
   sudo netstat -tlnp | grep 8080
   # or
   sudo ss -tlnp | grep 8080
   ```

2. **Firewall Rules on GCP**
   - Open Google Cloud Console
   - Navigate to **VPC Network** → **Firewall Rules**
   - Ensure there's a rule allowing ingress on port **8080**:
     - **Source IP ranges**: `0.0.0.0/0` (or your specific IP)
     - **Protocols and ports**: `tcp:8080`

3. **Admin Token Match**
   - Check your `.env` file on GCP VM:
     ```bash
     cat .env | grep ADMIN_WEB_TOKEN
     ```
   - This token must match exactly what you enter in the Android app

4. **Test Server Locally on GCP VM**
   ```bash
   # From inside the VM:
   curl http://localhost:8080/ping
   # Should return: {"ok":true,"pong":true,"port":8080}

   # Test with admin token:
   curl -H "X-Admin-Token: YOUR_TOKEN_HERE" http://localhost:8080/api/status
   ```

5. **Test Server from Your Phone's Network**
   ```bash
   # Get your GCP VM's external IP:
   gcloud compute instances describe YOUR_INSTANCE_NAME \
     --zone=YOUR_ZONE \
     --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

   # Test from your local machine (simulating phone):
   curl http://YOUR_EXTERNAL_IP:8080/ping
   ```

### Common Issues & Solutions

#### Issue 1: Server Not Accessible from Internet

**Symptom**: curl works on VM but fails from outside

**Solution**:
```bash
# 1. Check GCP firewall
gcloud compute firewall-rules list | grep 8080

# 2. If no rule exists, create one:
gcloud compute firewall-rules create allow-admin-panel \
  --allow tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow BlackBugsAI Admin Panel"
```

#### Issue 2: Admin Token Mismatch

**Symptom**: Connection test fails with 401 Unauthorized

**Solution**:
```bash
# Check current token in .env:
cat .env | grep ADMIN_WEB_TOKEN

# If it's "changeme_secret_token", generate a new one:
echo "ADMIN_WEB_TOKEN=$(openssl rand -hex 32)" >> .env

# Restart Docker container:
docker-compose down && docker-compose up -d

# Use this new token in Android app
```

#### Issue 3: Docker Container Not Running

**Symptom**: Connection refused

**Solution**:
```bash
# Check container status:
docker ps -a | grep automuvie

# If not running, start it:
cd /path/to/Black-WhiteAI
docker-compose up -d

# Check logs:
docker-compose logs -f --tail=50
```

#### Issue 4: Port 8080 Already in Use

**Symptom**: Container fails to start, "port already allocated"

**Solution**:
```bash
# Find what's using port 8080:
sudo lsof -i :8080

# Option 1: Kill the process
sudo kill -9 PID_NUMBER

# Option 2: Change port in docker-compose.yml:
# Change "8080:8080" to "8081:8080"
# Then in Android app use port 8081
```

#### Issue 5: HTTPS vs HTTP Confusion

**Symptom**: Connection times out or SSL errors

**Solution**:
- By default, server runs on **HTTP** (not HTTPS)
- In Android app setup screen, ensure "USE HTTPS" toggle is **OFF**
- If you need HTTPS, you must set up a reverse proxy (nginx/caddy) with SSL certificate

### Android App Configuration

**Correct Setup**:
```
GCP SERVER IP: 34.XX.XX.XX (your GCP VM external IP)
SSH PORT: 22
DOCKER PORT: 8080
SSH USERNAME: ubuntu (or your username)
ADMIN TOKEN: <your ADMIN_WEB_TOKEN from .env>
USE HTTPS: OFF (unless you configured SSL)
```

### Testing Connection Step-by-Step

1. **Get GCP VM External IP**:
   ```bash
   curl ifconfig.me
   # or
   gcloud compute instances list
   ```

2. **From VM, verify server responds**:
   ```bash
   curl http://localhost:8080/ping
   ```

3. **From VM, verify admin endpoint**:
   ```bash
   TOKEN=$(cat .env | grep ADMIN_WEB_TOKEN | cut -d'=' -f2)
   curl -H "X-Admin-Token: $TOKEN" http://localhost:8080/api/status
   ```

4. **From your local machine**:
   ```bash
   # Replace with your actual IP and token
   curl http://34.XX.XX.XX:8080/ping
   curl -H "X-Admin-Token: YOUR_TOKEN" http://34.XX.XX.XX:8080/api/status
   ```

5. **From Android app**:
   - Enter the external IP
   - Enter port 8080
   - Enter your admin token
   - Turn OFF "USE HTTPS"
   - Click "ТЕСТ" button

### Network Security Group (GCP Firewall) Example

```bash
# Create firewall rule via gcloud:
gcloud compute firewall-rules create blackbugsai-admin \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8080,tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --description="Allow SSH and Admin Panel for BlackBugsAI"
```

### Docker Compose Verification

Ensure your `docker-compose.yml` has:
```yaml
services:
  bot:
    ports:
      - "8080:8080"  # Expose admin panel
    environment:
      - ADMIN_WEB_TOKEN=${ADMIN_WEB_TOKEN:-changeme_secret_token}
      - ADMIN_WEB_PORT=8080
```

### Logs to Check

```bash
# Docker container logs:
docker-compose logs -f

# Check for these lines on startup:
# "🌐 Admin Panel: http://0.0.0.0:8080/panel"
# "🔑 Token: xxxxxxxx..."

# System logs:
journalctl -u docker -f
```

### Advanced Debugging

**Enable verbose logging**:
```bash
# Add to .env:
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env

docker-compose restart
```

**Test with curl from Android device**:
- Install Termux on Android
- Run:
  ```bash
  pkg install curl
  curl -v http://YOUR_IP:8080/ping
  ```

### Still Not Working?

1. **Check GCP Console Logs**:
   - Go to **Logging** → **Logs Explorer**
   - Filter by your VM instance
   - Look for connection errors

2. **Verify network connectivity**:
   ```bash
   # From VM, check if you can reach internet:
   ping -c 3 8.8.8.8

   # Check DNS:
   nslookup google.com
   ```

3. **Check Docker network**:
   ```bash
   docker network inspect bridge
   ```

4. **Restart everything**:
   ```bash
   docker-compose down
   docker-compose up -d
   # Wait 30 seconds
   curl http://localhost:8080/ping
   ```

### Security Notes

⚠️ **Important**:
- Opening port 8080 to `0.0.0.0/0` allows anyone to access your admin panel
- **ALWAYS** use a strong `ADMIN_WEB_TOKEN` (32+ characters)
- Consider restricting firewall to your IP only:
  ```bash
  gcloud compute firewall-rules create blackbugsai-admin-restricted \
    --allow tcp:8080 \
    --source-ranges YOUR_HOME_IP/32
  ```

### Quick Fix Command Sequence

Run this on your GCP VM:
```bash
# Full reset and verification
cd ~/Black-WhiteAI  # or your repo path

# Stop everything
docker-compose down

# Verify .env has correct token
grep ADMIN_WEB_TOKEN .env

# Start container
docker-compose up -d

# Wait for startup
sleep 10

# Test locally
curl http://localhost:8080/ping

# Show external IP
curl -s ifconfig.me
echo ""

# Show admin token
echo "Your Admin Token:"
grep ADMIN_WEB_TOKEN .env | cut -d'=' -f2

# Check firewall
gcloud compute firewall-rules list | grep 8080
```

Then use the displayed IP and token in your Android app.
