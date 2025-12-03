# Railway Deployment Instructions

## 1. Delete Current Service
In Railway dashboard, delete the existing service.

## 2. Create New Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select: `Surya-Chinnathambi/HR-Mate-Pro`
3. **Important**: Set **Root Directory** to: `hrms_backend`
4. Railway will auto-detect the Dockerfile

## 3. Add Environment Variables

Go to **Variables** tab and add these (copy-paste all):

```
APP_NAME=HRMS Backend
APP_VERSION=1.0.0
DEBUG=False
HOST=0.0.0.0
PORT=8000
DATABASE_URL=postgresql://postgres:SuryaSur@123@db.pusxdaxqzmjrantwjakj.supabase.co:5432/postgres
UPSTASH_URL=https://lenient-mongrel-26817.upstash.io
UPSTASH_TOKEN=AWjBAAIncDI3ZWMxOTIxZDUwODc0MzQ5YmFmY2U1Yjk2YjhkZDVhYnAyMjY4MTc
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
AZURE_OPENAI_ENDPOINT=https://litellm.dev.asoclab.dev/v1
AZURE_OPENAI_KEY=sk-cX6455aOorGC07hIUVf49g
AZURE_OPENAI_DEPLOYMENT=azure/gpt-5-chat
AZURE_OPENAI_API_VERSION=2024-02-15-preview
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:5174","https://*.railway.app","https://*.vercel.app"]
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=100
```

## 4. Deploy

Click **"Deploy"** and wait 2-5 minutes.

## 5. Get Your Backend URL

Once deployed, copy the public domain (e.g., `https://xyz.up.railway.app`)

## 6. Test

```
curl https://your-url.up.railway.app/health
```

Should return:
```json
{"status":"healthy","app":"HRMS Backend","version":"1.0.0"}
```

---

**Note**: The key is setting **Root Directory** to `hrms_backend` during service creation. This tells Railway to look in that folder for the Dockerfile.
