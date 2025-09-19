# Redis Setup Guide for Self-Hosted Servers

## 🚀 Redis Installation & Configuration

### **Step 1: Install Redis on Your Server**

#### **Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install Redis
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server
```

#### **CentOS/RHEL:**
```bash
# Install EPEL repository
sudo yum install epel-release

# Install Redis
sudo yum install redis

# Start Redis service
sudo systemctl start redis

# Enable Redis to start on boot
sudo systemctl enable redis
```

### **Step 2: Configure Redis for Production**

#### **Edit Redis Configuration:**
```bash
sudo nano /etc/redis/redis.conf
```

#### **Key Settings to Update:**
```conf
# Bind to all interfaces (or specific IP)
bind 0.0.0.0

# Set a password for security
requirepass your-redis-password

# Set max memory (adjust based on your server)
maxmemory 2gb
maxmemory-policy allkeys-lru

# Enable persistence
save 900 1
save 300 10
save 60 10000

# Log level
loglevel notice

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
```

### **Step 3: Secure Redis**

#### **Firewall Configuration:**
```bash
# Allow Redis port only from your application servers
sudo ufw allow from YOUR_APP_SERVER_IP to any port 6379

# Or if using iptables
sudo iptables -A INPUT -p tcp --dport 6379 -s YOUR_APP_SERVER_IP -j ACCEPT
```

#### **Redis Authentication:**
```bash
# Test Redis connection with password
redis-cli -a your-redis-password ping
```

### **Step 4: Update Your Environment Files**

#### **For Staging:**
```bash
# In backend/.env.staging
REDIS_HOST=redis-staging.irisvision.ai
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_SSL=false
```

#### **For Production:**
```bash
# In backend/.env.production
REDIS_HOST=redis.irisvision.ai
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_SSL=false
```

### **Step 5: DNS Configuration**

#### **Add DNS Records:**
```
# Staging Redis
redis-staging.irisvision.ai → YOUR_STAGING_SERVER_IP

# Production Redis  
redis.irisvision.ai → YOUR_PRODUCTION_SERVER_IP
```

### **Step 6: Test Redis Connection**

#### **From Your Application Server:**
```bash
# Test connection
redis-cli -h redis.irisvision.ai -p 6379 -a your-redis-password ping

# Should return: PONG
```

## 🔧 Docker Alternative (Recommended)

If you prefer Docker (easier management):

### **Create Redis Docker Compose:**
```yaml
# docker-compose.redis.yml
version: '3.8'
services:
  redis:
    image: redis:8-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    command: redis-server /usr/local/etc/redis/redis.conf --requirepass your-redis-password
    networks:
      - redis-network

volumes:
  redis_data:

networks:
  redis-network:
    driver: bridge
```

### **Start Redis with Docker:**
```bash
# Start Redis
docker-compose -f docker-compose.redis.yml up -d

# Check status
docker-compose -f docker-compose.redis.yml ps
```

## 📊 Monitoring & Maintenance

### **Redis Monitoring:**
```bash
# Check Redis status
sudo systemctl status redis-server

# Monitor Redis in real-time
redis-cli -a your-redis-password monitor

# Check memory usage
redis-cli -a your-redis-password info memory

# Check connected clients
redis-cli -a your-redis-password info clients
```

### **Backup Strategy:**
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
redis-cli -a your-redis-password --rdb /backup/redis_backup_$DATE.rdb

# Add to crontab for daily backups
0 2 * * * /path/to/backup_script.sh
```

## 🚨 Security Best Practices

1. **✅ Use strong passwords**
2. **✅ Bind to specific IPs only**
3. **✅ Use firewall rules**
4. **✅ Disable dangerous commands**
5. **✅ Regular backups**
6. **✅ Monitor access logs**

## 🎯 Benefits of Self-Hosted Redis

- ✅ **Unlimited storage** (your server's disk)
- ✅ **No bandwidth limits**
- ✅ **No connection limits**
- ✅ **Full control**
- ✅ **No external dependencies**
- ✅ **Cost-effective**
- ✅ **Better performance** (no network latency)

## 📋 Quick Setup Checklist

- [ ] Install Redis on server
- [ ] Configure Redis with password
- [ ] Set up firewall rules
- [ ] Update DNS records
- [ ] Test connection from app server
- [ ] Update environment files
- [ ] Set up monitoring
- [ ] Configure backups

Your Redis setup is now ready for production! 🚀
