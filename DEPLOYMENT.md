# Deployment Guide

Quick deployment guide for the Padel Court Booking System.

## Prerequisites

- Docker and Docker Compose installed
- Estelle Manor account credentials
- Discord webhook URL
- Server with internet access (if deploying remotely)

## Quick Deployment (Recommended)

### 1. Clone/Copy Project

```bash
cd /home/cogito/dev/gc-estelle
```

### 2. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required settings:**
```ini
ESTELLE_USERNAME=your.email@example.com
ESTELLE_PASSWORD=your_password_here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE

# Start in dry-run mode for testing
DRY_RUN=true
LOG_LEVEL=INFO
PRE_LOGIN_MINUTES=10
```

### 3. Quick Start

```bash
# Make script executable
chmod +x quick_start.sh

# Run quick start
./quick_start.sh
```

This will:
- Build the Docker image
- Start the container
- Check health
- Show you how to upload bookings

### 4. Upload Bookings

```bash
# Edit example_bookings.csv with your desired dates/times
nano example_bookings.csv

# Upload
curl -X POST http://localhost:8000/bookings/upload \
  -F "file=@example_bookings.csv"
```

### 5. Verify

```bash
# Check bookings
curl http://localhost:8000/bookings

# View logs
docker-compose logs -f
```

### 6. Test Notification

```bash
curl -X POST http://localhost:8000/test/notification
```

Check your Discord channel for the test message.

### 7. Go Live

Once testing is complete:

```bash
# Edit .env
DRY_RUN=false

# Restart
docker-compose restart

# Upload your real bookings
curl -X POST http://localhost:8000/bookings/upload \
  -F "file=@my_bookings.csv"
```

## Manual Deployment

### Build Image

```bash
docker-compose build
```

### Start Services

```bash
# Start in foreground (for testing)
docker-compose up

# Start in background (production)
docker-compose up -d
```

### View Logs

```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f padel-booking
```

### Stop Services

```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Remote Deployment

### Option 1: Copy to Remote Server

```bash
# From local machine
scp -r /home/cogito/dev/gc-estelle user@server:/path/to/deploy

# On remote server
cd /path/to/deploy
./quick_start.sh
```

### Option 2: Git Clone

```bash
# On remote server
git clone <your-repo-url>
cd gc-estelle
cp .env.example .env
nano .env
./quick_start.sh
```

## Production Configuration

### Systemd Service (Optional)

If you want the container to start on boot:

```bash
# Enable Docker service
sudo systemctl enable docker

# Create systemd service
sudo nano /etc/systemd/system/padel-booking.service
```

```ini
[Unit]
Description=Padel Booking System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/cogito/dev/gc-estelle
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable padel-booking
sudo systemctl start padel-booking

# Check status
sudo systemctl status padel-booking
```

### Reverse Proxy (Optional)

If you want to expose the API externally:

**Nginx:**
```nginx
server {
    listen 80;
    server_name booking.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Caddy:**
```
booking.yourdomain.com {
    reverse_proxy localhost:8000
}
```

### Firewall (If exposed externally)

```bash
# Allow only from specific IP
sudo ufw allow from YOUR_IP to any port 8000

# Or allow from anywhere (less secure)
sudo ufw allow 8000
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ESTELLE_USERNAME` | Yes | - | Estelle Manor username |
| `ESTELLE_PASSWORD` | Yes | - | Estelle Manor password |
| `DISCORD_WEBHOOK_URL` | Yes | - | Discord webhook for notifications |
| `DRY_RUN` | No | false | Test mode (no actual bookings) |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DATABASE_PATH` | No | ./data/estelle.db | SQLite database path |
| `BROWSER_STATE_PATH` | No | ./data/browser_state.json | Browser session file |
| `PRE_LOGIN_MINUTES` | No | 10 | Minutes before midnight to login |
| `API_HOST` | No | 0.0.0.0 | API bind address |
| `API_PORT` | No | 8000 | API port |

## Data Persistence

The following directories are mounted as volumes:

- `./data/` - Database and browser session
- `./logs/` - Application logs

**Backup important data:**
```bash
# Backup database
cp data/estelle.db data/estelle.db.backup

# Archive screenshots
tar -czf screenshots-$(date +%Y%m%d).tar.gz data/screenshots/
```

## Upgrading

```bash
# Pull latest code
git pull  # or copy new files

# Rebuild image
docker-compose build

# Restart with new image
docker-compose down
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Check Docker status
docker ps -a

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Permission issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/ logs/
chmod -R 755 data/ logs/
```

### Port already in use
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Change port in .env
API_PORT=8001

# Restart
docker-compose down
docker-compose up -d
```

### Database locked
```bash
# Stop container
docker-compose down

# Remove database lock
rm -f data/estelle.db-wal data/estelle.db-shm

# Restart
docker-compose up -d
```

## Monitoring

### Health Checks

```bash
# Manual check
curl http://localhost:8000/health

# Automated monitoring (add to crontab)
*/5 * * * * curl -sf http://localhost:8000/health || echo "Booking system down!" | mail -s "Alert" you@email.com
```

### Log Rotation

Docker handles log rotation, but you can configure it:

```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Resource Usage

```bash
# Check resource usage
docker stats padel-booking

# Set resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 1G
```

## Security Recommendations

1. **Never commit .env file**
   - Add to .gitignore
   - Use environment-specific configs

2. **Secure Discord webhook**
   - Rotate webhook URL periodically
   - Monitor for unauthorized use

3. **Restrict API access**
   - Use firewall rules
   - Consider API authentication
   - Use reverse proxy with SSL

4. **Keep dependencies updated**
   - Regularly rebuild Docker image
   - Update base Python image

5. **Backup data**
   - Regular database backups
   - Archive screenshots periodically

## Support

Check these resources in order:

1. **Logs**: `docker-compose logs -f`
2. **Health endpoint**: `curl http://localhost:8000/health`
3. **Database**: `sqlite3 data/estelle.db`
4. **Screenshots**: `ls -lh data/screenshots/`
5. **Testing Guide**: `TESTING_GUIDE.md`

## Uninstall

```bash
# Stop and remove containers
docker-compose down

# Remove volumes
docker volume rm gc-estelle_data

# Remove images
docker rmi gc-estelle-padel-booking

# Remove project directory
cd ..
rm -rf gc-estelle
```
