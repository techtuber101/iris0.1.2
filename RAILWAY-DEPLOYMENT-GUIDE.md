# 🚂 Railway Deployment Guide - Complete Step-by-Step

## 📋 Prerequisites

Before starting, make sure you have:
- ✅ GitHub repository pushed (we just did this)
- ✅ Railway account (free tier available)
- ✅ Your environment variables ready
- ✅ Domain ready for DNS configuration

---

## 🚀 **STEP 1: Create Railway Account**

### **1.1 Sign Up**
1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Sign up with GitHub (recommended)
4. Authorize Railway to access your repositories

### **1.2 Verify Account**
- Check your email for verification
- Complete any additional setup steps

---

## 🚂 **STEP 2: Create New Project**

### **2.1 Create Project**
1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select your repository: `techtuber101/iris0.1.2`
4. Click **"Deploy Now"**

### **2.2 Configure Service**
Railway will detect your project structure. You need to configure it for the backend:

1. **Service Name**: `iris-backend-staging` (or `iris-backend-prod`)
2. **Root Directory**: `backend`
3. **Build Command**: `uv sync`
4. **Start Command**: `uv run python -m uvicorn core.run:app --host 0.0.0.0 --port $PORT`

---

## ⚙️ **STEP 3: Configure Build Settings**

### **3.1 Go to Service Settings**
1. Click on your service name
2. Go to **"Settings"** tab
3. Click **"Build"** section

### **3.2 Set Build Configuration**
```bash
# Build Command
uv sync

# Start Command  
uv run python -m uvicorn core.run:app --host 0.0.0.0 --port $PORT

# Health Check Path
/health
```

### **3.3 Set Python Version**
1. Go to **"Variables"** tab
2. Add environment variable:
   - **Name**: `PYTHON_VERSION`
   - **Value**: `3.11`

---

## 🔐 **STEP 4: Add Environment Variables**

### **4.1 Go to Variables Tab**
1. Click **"Variables"** in your service
2. Add each environment variable one by one

### **4.2 Add All Required Variables**

#### **Core Configuration:**
```bash
ENV_MODE=staging
PYTHON_VERSION=3.11
PORT=$PORT
```

#### **Supabase Configuration:**
```bash
SUPABASE_URL=https://lhjchjuzgxbjoldducpb.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMzMzODksImV4cCI6MjA3MzcwOTM4OX0.hfsz9St68K5R5y88qg4RGLoO0dWbgdg9Xv2frk-IdT0
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODEzMzM4OSwiZXhwIjoyMDczNzA5Mzg5fQ.vGlzdvL4iS51fG25UlwGBHIB0Rj_u4pXqrIVas5nQuY
SUPABASE_JWT_SECRET=owo6C+5Y4colzYa2VTl1wj8LbEzOSHWaPi8if3+bwMfEaX6p57Jp5QMjH+EtDrc+eIp94n0qZQrRf327HLYW1g==
```

#### **Redis Configuration:**
```bash
REDIS_HOST=redis-staging.irisvision.ai
REDIS_PORT=6379
REDIS_SSL=false
REDIS_PASSWORD=your-redis-password
```

#### **API Keys:**
```bash
GEMINI_API_KEY=AIzaSyDNlUaZTo8TMjXOjklzqD93jmCuxqha8Dk
OPENAI_API_KEY=your-openai-api-key
MORPH_API_KEY=sk-OxFElWyezl63liWv56EjAeZmA6oMjyk5_7vNGcMJ5qWNamBU
TAVILY_API_KEY=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
FIRECRAWL_API_KEY=fc-5459fb5f14894354b80fa228d05d52e4
FIRECRAWL_URL=https://api.firecrawl.dev
RAPID_API_KEY=
```

#### **Webhook Configuration:**
```bash
WEBHOOK_BASE_URL=https://api-staging.irisvision.ai
TRIGGER_WEBHOOK_SECRET=3ef2dd9c81c1c844c475950eee341df963992976a68d4f3db3fc46783e09bd23
```

#### **Security Keys:**
```bash
MCP_CREDENTIAL_ENCRYPTION_KEY=HJdK2yShSP3pVuIhahxmA3MsQ8qZOBnFXVQfEwueMr4=
ENCRYPTION_KEY=54kwtziETg6SW7uZMNOuZpy7rkDxxXSm20/8GMJpCKE=
KORTIX_ADMIN_API_KEY=1d35d7b10d1a6cae42440d2c118bc85f35ac2c7a305eb4caacc290411daa1732
```

#### **External Services:**
```bash
COMPOSIO_API_KEY=ak_YxlKVhme16qZrNHBMxJ2
COMPOSIO_WEBHOOK_SECRET=fde83f85fda27f703779172b34560d57a7b6defd80691fc07ce413d47b2bcbab
DAYTONA_API_KEY=dtn_98222fe59a1e985bc8cab94bf382500f04220a48c7056f22747ce1e56304733b
DAYTONA_SERVER_URL=https://app.daytona.io/api
DAYTONA_TARGET=us
```

#### **Frontend URL:**
```bash
NEXT_PUBLIC_URL=https://staging.irisvision.ai
```

---

## 🚀 **STEP 5: Deploy**

### **5.1 Trigger Deployment**
1. Go to **"Deployments"** tab
2. Click **"Deploy"** or push a commit to trigger auto-deploy
3. Watch the build logs

### **5.2 Monitor Build Process**
Railway will:
1. **Install dependencies** with `uv sync`
2. **Build your application**
3. **Start the server** with uvicorn
4. **Run health checks**

### **5.3 Check Build Logs**
- Look for any errors in the build process
- Ensure all dependencies install correctly
- Verify the server starts successfully

---

## 🌐 **STEP 6: Configure Domain**

### **6.1 Get Railway URL**
1. Go to **"Settings"** → **"Domains"**
2. Copy your Railway URL (something like `your-app.railway.app`)

### **6.2 Set Up Custom Domain**
1. Click **"Custom Domain"**
2. Add your domain: `api-staging.irisvision.ai`
3. Follow DNS instructions

### **6.3 DNS Configuration**
Add this DNS record to your domain provider:
```
Type: CNAME
Name: api-staging
Value: your-app.railway.app
TTL: 300
```

---

## 🔍 **STEP 7: Test Deployment**

### **7.1 Health Check**
Visit: `https://api-staging.irisvision.ai/health`
Should return: `{"status": "healthy"}`

### **7.2 API Test**
Test a simple endpoint:
```bash
curl https://api-staging.irisvision.ai/api/health
```

### **7.3 Check Logs**
1. Go to **"Deployments"** tab
2. Click on latest deployment
3. Check **"Logs"** for any errors

---

## 🔧 **STEP 8: Configure Auto-Deploy**

### **8.1 Enable GitHub Integration**
1. Go to **"Settings"** → **"GitHub"**
2. Enable **"Auto Deploy"**
3. Select branch: `main` (for staging)

### **8.2 Set Up Branch Strategy**
- **`main` branch** → Staging deployment
- **`production` branch** → Production deployment

---

## 📊 **STEP 9: Monitor & Scale**

### **9.1 Monitor Performance**
1. Go to **"Metrics"** tab
2. Monitor CPU, Memory, Network usage
3. Check response times

### **9.2 Scale if Needed**
1. Go to **"Settings"** → **"Scaling"**
2. Adjust resources based on usage
3. Enable auto-scaling if needed

---

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Build Fails:**
```bash
# Check Python version
PYTHON_VERSION=3.11

# Check build command
uv sync

# Check start command
uv run python -m uvicorn core.run:app --host 0.0.0.0 --port $PORT
```

#### **Environment Variables Missing:**
- Double-check all variables are added
- Ensure no typos in variable names
- Check variable values are correct

#### **Port Issues:**
- Railway automatically sets `$PORT`
- Use `$PORT` in your start command
- Don't hardcode port numbers

#### **Redis Connection Issues:**
- Verify Redis server is running
- Check Redis host and port
- Ensure firewall allows connections

---

## 🎯 **Production Deployment**

### **For Production:**
1. **Create new service**: `iris-backend-prod`
2. **Use production environment variables**
3. **Set domain**: `api.irisvision.ai`
4. **Deploy from `production` branch**

### **Production Environment Variables:**
```bash
ENV_MODE=production
REDIS_HOST=redis.irisvision.ai
WEBHOOK_BASE_URL=https://api.irisvision.ai
NEXT_PUBLIC_URL=https://irisvision.ai
```

---

## ✅ **Deployment Checklist**

- [ ] **Railway account created**
- [ ] **Project deployed from GitHub**
- [ ] **Root directory set to `backend`**
- [ ] **Build command configured**
- [ ] **Start command configured**
- [ ] **All environment variables added**
- [ ] **Custom domain configured**
- [ ] **DNS records updated**
- [ ] **Health check passing**
- [ ] **API endpoints working**
- [ ] **Auto-deploy enabled**
- [ ] **Monitoring set up**

---

## 🚀 **Next Steps**

After Railway deployment:
1. **Set up Vercel** for frontend
2. **Configure Redis** on your servers
3. **Set up DNS** for all domains
4. **Test full integration**
5. **Configure GitHub Actions** for CI/CD

**Your Railway backend is now ready!** 🎉
