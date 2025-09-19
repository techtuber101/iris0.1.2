# 🚀 Upstash Redis Setup Guide

## 📋 Why Upstash Redis?

✅ **Serverless Redis** - No server management  
✅ **Auto-scaling** - Scales with your traffic  
✅ **Global edge locations** - Fast worldwide access  
✅ **Free tier available** - 10,000 requests/day  
✅ **Easy integration** - Simple connection strings  
✅ **Built for serverless** - Perfect for Railway/Vercel  

---

## 🚀 **STEP 1: Create Upstash Account**

### **1.1 Sign Up**
1. Go to [upstash.com](https://upstash.com)
2. Click **"Sign Up"**
3. Sign up with GitHub (recommended)
4. Verify your email

### **1.2 Choose Plan**
- **Free Tier**: 10,000 requests/day, 256MB storage
- **Pro Tier**: $0.2 per 100K requests, 1GB storage

---

## 🗄️ **STEP 2: Create Redis Database**

### **2.1 Create Database**
1. In Upstash dashboard, click **"Create Database"**
2. **Database Name**: `iris-production-redis`
3. **Region**: Choose closest to your Railway region (Singapore)
4. **Type**: `Regional` (recommended for production)

### **2.2 Database Settings**
- **Name**: `iris-production-redis`
- **Region**: `ap-southeast-1` (Singapore)
- **Type**: `Regional`
- **TLS**: `Enabled` (required for SSL)

---

## 🔐 **STEP 3: Get Connection Details**

### **3.1 Copy Connection String**
After creating the database, you'll see:

```bash
# Redis URL (for REDIS_HOST)
redis-12345.upstash.io

# Redis Password (for REDIS_PASSWORD)
your-redis-password-here

# Redis Port
6379
```

### **3.2 Connection Details Format**
```bash
REDIS_HOST=redis-12345.upstash.io
REDIS_PORT=6379
REDIS_SSL=true
REDIS_PASSWORD=your-redis-password-here
```

---

## ⚙️ **STEP 4: Update Railway Environment Variables**

### **4.1 Go to Railway Variables**
1. In your Railway service
2. Click **"Variables"** tab
3. Add/update these Redis variables:

```bash
# Redis Configuration
REDIS_HOST=redis-12345.upstash.io
REDIS_PORT=6379
REDIS_SSL=true
REDIS_PASSWORD=your-redis-password-here
```

### **4.2 Complete Environment Variables for Railway**

```bash
# Core Configuration
ENV_MODE=production
PYTHON_VERSION=3.11
PORT=$PORT

# Supabase Configuration
SUPABASE_URL=https://lhjchjuzgxbjoldducpb.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMzMzODksImV4cCI6MjA3MzcwOTM4OX0.hfsz9St68K5R5y88qg4RGLoO0dWbgdg9Xv2frk-IdT0
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODEzMzM4OSwiZXhwIjoyMDczNzA5Mzg5fQ.vGlzdvL4iS51fG25UlwGBHIB0Rj_u4pXqrIVas5nQuY
SUPABASE_JWT_SECRET=owo6C+5Y4colzYa2VTl1wj8LbEzOSHWaPi8if3+bwMfEaX6p57Jp5QMjH+EtDrc+eIp94n0qZQrRf327HLYW1g==

# Upstash Redis Configuration
REDIS_HOST=redis-12345.upstash.io
REDIS_PORT=6379
REDIS_SSL=true
REDIS_PASSWORD=your-redis-password-here

# API Keys
GEMINI_API_KEY=AIzaSyDNlUaZTo8TMjXOjklzqD93jmCuxqha8Dk
OPENAI_API_KEY=your-openai-api-key
MORPH_API_KEY=sk-OxFElWyezl63liWv56EjAeZmA6oMjyk5_7vNGcMJ5qWNamBU
TAVILY_API_KEY=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
FIRECRAWL_API_KEY=fc-5459fb5f14894354b80fa228d05d52e4
FIRECRAWL_URL=https://api.firecrawl.dev

# Webhook Configuration
WEBHOOK_BASE_URL=https://api.irisvision.ai
TRIGGER_WEBHOOK_SECRET=3ef2dd9c81c1c844c475950eee341df963992976a68d4f3db3fc46783e09bd23

# Security Keys
MCP_CREDENTIAL_ENCRYPTION_KEY=HJdK2yShSP3pVuIhahxmA3MsQ8qZOBnFXVQfEwueMr4=
ENCRYPTION_KEY=54kwtziETg6SW7uZMNOuZpy7rkDxxXSm20/8GMJpCKE=
KORTIX_ADMIN_API_KEY=1d35d7b10d1a6cae42440d2c118bc85f35ac2c7a305eb4caacc290411daa1732

# External Services
COMPOSIO_API_KEY=ak_YxlKVhme16qZrNHBMxJ2
COMPOSIO_WEBHOOK_SECRET=fde83f85fda27f703779172b34560d57a7b6defd80691fc07ce413d47b2bcbab
DAYTONA_API_KEY=dtn_98222fe59a1e985bc8cab94bf382500f04220a48c7056f22747ce1e56304733b
DAYTONA_SERVER_URL=https://app.daytona.io/api
DAYTONA_TARGET=us

# Frontend URL
NEXT_PUBLIC_URL=https://irisvision.ai
```

---

## 🧪 **STEP 5: Test Redis Connection**

### **5.1 Test from Railway**
After deployment, check your Railway logs for Redis connection success.

### **5.2 Test from Upstash Console**
1. Go to your Upstash database
2. Click **"Console"**
3. Run: `PING`
4. Should return: `PONG`

### **5.3 Test from Your App**
Add a simple Redis test endpoint to verify connection.

---

## 📊 **STEP 6: Monitor Usage**

### **6.1 Upstash Dashboard**
- Monitor request count
- Check memory usage
- View response times
- Set up alerts

### **6.2 Free Tier Limits**
- **Requests**: 10,000/day
- **Storage**: 256MB
- **Bandwidth**: 10GB/month

---

## 🔧 **STEP 7: Local Development**

### **7.1 For Local Development**
Keep using local Redis for development:

```bash
# Local development
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_SSL=false
REDIS_PASSWORD=
```

### **7.2 Environment Switching**
Your `switch-env.sh` script handles this automatically:
- **Local**: Uses Docker Redis
- **Production**: Uses Upstash Redis

---

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Connection Refused:**
- Check `REDIS_HOST` is correct
- Verify `REDIS_SSL=true`
- Ensure password is correct

#### **SSL Errors:**
- Make sure `REDIS_SSL=true`
- Check Upstash TLS is enabled

#### **Authentication Failed:**
- Verify `REDIS_PASSWORD` is correct
- Check password hasn't expired

#### **Region Issues:**
- Choose region closest to Railway
- Singapore region for Railway Singapore

---

## 💰 **Cost Optimization**

### **Free Tier Usage:**
- **10,000 requests/day** = ~300K requests/month
- **256MB storage** = plenty for caching
- **10GB bandwidth** = sufficient for most apps

### **When to Upgrade:**
- More than 10K requests/day
- Need more than 256MB storage
- Require higher bandwidth

---

## ✅ **Benefits of Upstash Redis**

✅ **No server management**  
✅ **Auto-scaling**  
✅ **Global edge locations**  
✅ **Built-in monitoring**  
✅ **Easy integration**  
✅ **Free tier available**  
✅ **Perfect for serverless**  

---

## 🎯 **Quick Setup Checklist**

- [ ] **Create Upstash account**
- [ ] **Create Redis database**
- [ ] **Copy connection details**
- [ ] **Update Railway variables**
- [ ] **Test connection**
- [ ] **Monitor usage**

**Your Redis setup is now serverless and scalable!** 🚀
