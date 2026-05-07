# Railway Deployment Setup Guide

## Quick Start

This project is configured for **automatic deployment on Railway.app**.

### Prerequisites
- GitHub account with this repository pushed
- Railway account (get free credits at railway.app)

---

## Deployment Steps

### 1. Create Railway Project

```bash
# Option A: Using Railway CLI
npx railway login
npx railway link
npx railway up

# Option B: Using Railway Dashboard
# Go to https://railway.app/new and select "GitHub Repo"
```

### 2. Configure Environment Variables in Railway

In Railway Dashboard → Your Project → Variables:

```
# Backend API Configuration
API_KEY=your-secure-api-key-here

# Frontend Build Configuration (optional, defaults work fine)
VITE_API_URL=https://your-project-name.up.railway.app
VITE_API_KEY=your-secure-api-key-here
```

### 3. Enable Auto-Deploy (GitHub Integration)

1. Go to Railway Dashboard → Settings
2. Connect your GitHub repository
3. Enable "Auto Deploy" on the `main` branch
4. Optional: Set up deployment notifications

### 4. Verify Deployment

Once deployed, your app will be available at:
- **Frontend**: `https://your-project-name.up.railway.app`
- **API Docs**: `https://your-project-name.up.railway.app/docs`
- **API Root**: `https://your-project-name.up.railway.app/api/*`

---

## Project Structure for Railway

```
├── Procfile              # Start commands (web + release)
├── runtime.txt           # Python version
├── railway.json          # Railway configuration
├── build.sh              # Pre-deployment build script
├── .env.example          # Copy this for local development
├── backend/
│   ├── requirements.txt   # Python dependencies
│   └── src/main.py       # FastAPI app with static file serving
└── frontend/
    ├── package.json      # Node dependencies
    └── src/              # React/Vite app
```

### Key Configuration Files

**Procfile**: Defines how to build and run the app
- `release`: Installs dependencies, builds frontend
- `web`: Runs FastAPI server on Railway's PORT

**build.sh**: Handles full build orchestration
- Installs Python dependencies
- Installs Node dependencies
- Builds React frontend

**railway.json**: Railway deployment preferences
- Uses Heroku buildpacks for mixed Python/Node support

---

## How It Works

1. **Push to GitHub** → Railway automatically detects changes
2. **Release phase** runs (`build.sh`):
   - Installs backend Python dependencies
   - Installs frontend Node dependencies
   - Builds React app to `frontend/dist`
3. **Web phase** starts:
   - FastAPI server runs and serves:
     - `/api/*` routes → Python backend logic
     - `/` routes → Static React frontend from `frontend/dist`

---

## Development with Local Backend

For local testing before deployment:

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
python -m uvicorn src.main:app --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Frontend will be at `http://localhost:5173`
Backend API at `http://localhost:8000`

---

## Troubleshooting

### Build Fails
- Check Railway's build logs: Dashboard → Deployments → View Logs
- Verify all dependencies in `requirements.txt` and `frontend/package.json`

### API Not Responding
- Check that API_KEY matches between frontend `.env` and Railway variables
- Verify backend logs in Railway Dashboard

### Static Files Not Loading
- Confirm `frontend/dist` is created during build
- Check that `fastapi.staticfiles.StaticFiles` is correctly mounted

### Updates Not Deploying
- Verify GitHub integration is connected
- Check that auto-deploy is enabled for `main` branch
- Manual trigger: Railway Dashboard → Deployments → Redeploy Latest

---

## Production Checklist

- [ ] Set strong `API_KEY` in Railway variables
- [ ] Update `VITE_API_URL` to production domain
- [ ] Review CORS settings if accessing from external domains
- [ ] Set up monitoring/alerts in Railway Dashboard
- [ ] Enable Railway's database if needed for persistence
- [ ] Review logs regularly for errors

---

## Useful Railway Commands (CLI)

```bash
# Check deployment status
railway status

# View real-time logs
railway logs -f

# Open Railway dashboard
railway open

# Redeploy current branch
railway up

# View environment variables
railway variables
```

---

## Need Help?

- Railway Docs: https://docs.railway.app
- FastAPI Static Files: https://fastapi.tiangolo.com/tutorial/static-files/
- Vite Build: https://vitejs.dev/guide/build.html
