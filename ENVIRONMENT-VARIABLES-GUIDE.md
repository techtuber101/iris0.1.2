# 🔧 Environment Variables Guide for Hybrid Deployment

## 📋 Complete Environment Variables Checklist

### **🎯 What You Need to Set Up:**

| Service | Local | Staging | Production | Where to Get |
|---------|-------|---------|------------|--------------|
| **Supabase** | ✅ Already set | ✅ Already set | ✅ Already set | Your Supabase project |
| **Redis** | ✅ Docker | ❌ Need to set | ❌ Need to set | Your servers |
| **Vercel** | ❌ N/A | ❌ Need to set | ❌ Need to set | Vercel dashboard |
| **Railway** | ❌ N/A | ❌ Need to set | ❌ Need to set | Railway dashboard |
| **Domain** | ❌ N/A | ❌ Need to set | ❌ Need to set | Your domain provider |

---

## 🚀 **STEP 1: Vercel Setup (Frontend)**

### **1.1 Create Vercel Project**
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Set root directory to `frontend`
4. Get these values from Vercel dashboard:

```bash
# Vercel Project Settings
VERCEL_TOKEN=your-vercel-token
VERCEL_ORG_ID=your-org-id  
VERCEL_PROJECT_ID=your-project-id
```

### **1.2 Add Vercel Environment Variables**
In Vercel dashboard → Project Settings → Environment Variables:

```bash
# Frontend Environment Variables for Vercel
NEXT_PUBLIC_ENV_MODE=staging  # or production
NEXT_PUBLIC_SUPABASE_URL=https://lhjchjuzgxbjoldducpb.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMzMzODksImV4cCI6MjA3MzcwOTM4OX0.hfsz9St68K5R5y88qg4RGLoO0dWbgdg9Xv2frk-IdT0
NEXT_PUBLIC_BACKEND_URL=https://api-staging.irisvision.ai  # or https://api.irisvision.ai
NEXT_PUBLIC_URL=https://staging.irisvision.ai  # or https://irisvision.ai
```

---

## 🚂 **STEP 2: Railway Setup (Backend)**

### **2.1 Create Railway Project**
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub
3. Connect your repository
4. Get these values from Railway dashboard:

```bash
# Railway Project Settings
RAILWAY_TOKEN=your-railway-token
RAILWAY_SERVICE_ID=your-service-id
```

### **2.2 Add Railway Environment Variables**
In Railway dashboard → Project → Variables:

```bash
# Backend Environment Variables for Railway
ENV_MODE=staging  # or production
SUPABASE_URL=https://lhjchjuzgxbjoldducpb.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMzMzODksImV4cCI6MjA3MzcwOTM4OX0.hfsz9St68K5R5y88qg4RGLoO0dWbgdg9Xv2frk-IdT0
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxoamNoanV6Z3hiam9sZGR1Y3BiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODEzMzM4OSwiZXhwIjoyMDczNzA5Mzg5fQ.vGlzdvL4iS51fG25UlwGBHIB0Rj_u4pXqrIVas5XqrIVas5nQuY
SUPABASE_JWT_SECRET=owo6C+5Y4colzYa2VTl1wj8LbEzOSHWaPi8if3+bwMfEaX6p57Jp5QMjH+EtDrc+eIp94n0qZQrRf327HLYW1g==
REDIS_HOST=redis-staging.irisvision.ai  # or redis.irisvision.ai
REDIS_PORT=6379
REDIS_SSL=false
REDIS_PASSWORD=your-redis-password
GEMINI_API_KEY=AIzaSyDNlUaZTo8TMjXOjklzqD93jmCuxqha8Dk
OPENAI_API_KEY=your-openai-api-key
MORPH_API_KEY=sk-OxFElWyezl63liWv56EjAeZmA6oMjyk5_7vNGcMJ5qWNamBU
TAVILY_API_KEY=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
FIRECRAWL_API_KEY=fc-5459fb5f14894354b80fa228d05d52e4
FIRECRAWL_URL=https://api.firecrawl.dev
RAPID_API_KEY=
WEBHOOK_BASE_URL=https://api-staging.irisvision.ai  # or https://api.irisvision.ai
TRIGGER_WEBHOOK_SECRET=3ef2dd9c81c1c844c475950eee341df963992976a68d4f3db3fc46783e09bd23
MCP_CREDENTIAL_ENCRYPTION_KEY=HJdK2yShSP3pVuIhahxmA3MsQ8qZOBnFXVQfEwueMr4=
COMPOSIO_API_KEY=ak_YxlKVhme16qZrNHBMxJ2
COMPOSIO_WEBHOOK_SECRET=fde83f85fda27f703779172b34560d57a7b6defd80691fc07ce413d47b2bcbab
DAYTONA_API_KEY=dtn_98222fe59a1e985bc8cab94bf382500f04220a48c7056f22747ce1e56304733b
DAYTONA_SERVER_URL=https://app.daytona.io/api
DAYTONA_TARGET=us
KORTIX_ADMIN_API_KEY=1d35d7b10d1a6cae42440d2c118bc85f35ac2c7a305eb4caacc290411daa1732
ENCRYPTION_KEY=54kwtziETg6SW7uZMNOuZpy7rkDxxXSm20/8GMJpCKE=
NEXT_PUBLIC_URL=https://staging.irisvision.ai  # or https://irisvision.ai
```

---

## 🌐 **STEP 3: Domain Setup**

### **3.1 DNS Configuration**
Add these DNS records to your domain provider:

```bash
# Staging Environment
staging.irisvision.ai → Vercel deployment URL
api-staging.irisvision.ai → Railway deployment URL
redis-staging.irisvision.ai → Your staging server IP

# Production Environment  
irisvision.ai → Vercel deployment URL
api.irisvision.ai → Railway deployment URL
redis.irisvision.ai → Your production server IP
```

### **3.2 SSL Certificates**
- **Vercel**: Automatic SSL (handled by Vercel)
- **Railway**: Automatic SSL (handled by Railway)
- **Redis**: Self-signed or Let's Encrypt

---

## 🔐 **STEP 4: GitHub Secrets**

### **4.1 Add GitHub Secrets**
Go to your GitHub repository → Settings → Secrets and variables → Actions:

```bash
# Vercel Secrets
VERCEL_TOKEN=your-vercel-token
VERCEL_ORG_ID=your-org-id
VERCEL_PROJECT_ID=your-project-id

# Railway Secrets
RAILWAY_TOKEN=your-railway-token
```

---

## 🗄️ **STEP 5: Redis Setup**

### **5.1 Install Redis on Your Servers**
Follow the `REDIS-SETUP.md` guide:

```bash
# On your staging server
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# On your production server  
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### **5.2 Configure Redis Security**
```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Add password
requirepass your-redis-password

# Bind to specific IPs
bind YOUR_SERVER_IP

# Restart Redis
sudo systemctl restart redis-server
```

---

## 📝 **STEP 6: Update Your Environment Files**

### **6.1 Backend Environment Files**
Update these files with your actual values:

```bash
# backend/.env.staging
REDIS_HOST=redis-staging.irisvision.ai
REDIS_PASSWORD=your-actual-redis-password
WEBHOOK_BASE_URL=https://api-staging.irisvision.ai
NEXT_PUBLIC_URL=https://staging.irisvision.ai

# backend/.env.production  
REDIS_HOST=redis.irisvision.ai
REDIS_PASSWORD=your-actual-redis-password
WEBHOOK_BASE_URL=https://api.irisvision.ai
NEXT_PUBLIC_URL=https://irisvision.ai
```

### **6.2 Frontend Environment Files**
Update these files with your actual values:

```bash
# frontend/.env.staging
NEXT_PUBLIC_ENV_MODE=staging
NEXT_PUBLIC_BACKEND_URL=https://api-staging.irisvision.ai
NEXT_PUBLIC_URL=https://staging.irisvision.ai

# frontend/.env.production
NEXT_PUBLIC_ENV_MODE=production
NEXT_PUBLIC_BACKEND_URL=https://api.irisvision.ai
NEXT_PUBLIC_URL=https://irisvision.ai
```

---

## 🚀 **STEP 7: Deploy**

### **7.1 Test Local Development**
```bash
./switch-env.sh local
# Start your services - everything works locally
```

### **7.2 Deploy to Staging**
```bash
./switch-env.sh staging
# Push to main branch - GitHub Actions deploys to staging
```

### **7.3 Deploy to Production**
```bash
./switch-env.sh production
# Push to production branch - GitHub Actions deploys to production
```

---

## ✅ **Quick Checklist**

- [ ] **Vercel**: Create project, get tokens, add environment variables
- [ ] **Railway**: Create project, get tokens, add environment variables  
- [ ] **Domain**: Set up DNS records for staging and production
- [ ] **Redis**: Install and configure on your servers
- [ ] **GitHub**: Add secrets for Vercel and Railway
- [ ] **Environment Files**: Update with actual values
- [ ] **Test**: Deploy and verify everything works

---

## 🎯 **Summary**

You need to set up:
1. **Vercel** (frontend hosting)
2. **Railway** (backend hosting)  
3. **Your servers** (Redis hosting)
4. **Domain** (DNS configuration)
5. **GitHub Secrets** (deployment automation)

**Total time needed**: ~2-3 hours
**Cost**: ~$0-20/month (depending on usage)

**You're ready to deploy!** 🚀
