# Railway Deployment Checklist

## Pre-Deployment Setup

### Local Environment
- [ ] Clone repository locally
- [ ] Create `.env` file in root with:
  ```
  API_KEY=kredl-dev-key
  ```
- [ ] Create `frontend/.env` if using different API settings
- [ ] Test locally: `bash start.sh`
  - Backend should run on http://localhost:8000
  - Frontend should run on http://localhost:5173
  - API Docs at http://localhost:8000/docs

### GitHub Repository
- [ ] All code committed and pushed to `main` branch
- [ ] Railway deployment files present:
  - [x] `Procfile` (web + release commands)
  - [x] `runtime.txt` (Python version)
  - [x] `railway.json` (Railway config)
  - [x] `build.sh` (build orchestration)
  - [x] `.env.example` (environment template)
  - [x] `RAILWAY-DEPLOYMENT.md` (documentation)

### Verify Deployment Files
```bash
bash verify-deployment.sh
```

---

## Railway Setup

### 1. Create Railway Account
- [ ] Go to https://railway.app
- [ ] Sign up with GitHub (recommended for easy integration)
- [ ] Verify email and activate account

### 2. Create New Project
- [ ] Click "Create New Project"
- [ ] Select "Deploy from GitHub Repo"
- [ ] Authorize Railway with GitHub
- [ ] Select your `UrjaDrishti` repository
- [ ] Select `main` branch
- [ ] Click "Deploy"

### 3. Configure Environment Variables
In Railway Dashboard → Your Project → Variables, add:

```
# REQUIRED - API Authentication
API_KEY=your-secure-production-key-here

# OPTIONAL - Frontend API Configuration
# Leave empty to use same-origin requests (recommended for production)
VITE_API_URL=
VITE_API_KEY=your-production-key-same-as-api-key
```

**Important:** Use a strong, secure API_KEY different from development!

### 4. Enable Auto-Deploy
- [ ] Settings → GitHub Integration
- [ ] Enable "Auto Deploy" on `main` branch
- [ ] Deployments will trigger automatically on push

---

## Post-Deployment Verification

### Check Deployment Status
1. Railway Dashboard → Deployments
2. Wait for "✓ Success" status
3. Check build logs for any errors

### Verify Application Works
```bash
# Replace YOUR-PROJECT-ID with your Railway project domain
curl https://YOUR-PROJECT-ID.up.railway.app/api/forecast/day-ahead \
  -H "X-API-Key: your-api-key"

# Should return forecasting data or appropriate error
```

### Test Frontend
- [ ] Navigate to https://YOUR-PROJECT-ID.up.railway.app
- [ ] App should load without errors
- [ ] Browser console should be clean (no 404s or CORS errors)
- [ ] Try a plant forecast query

### Check API Documentation
- [ ] Navigate to https://YOUR-PROJECT-ID.up.railway.app/docs
- [ ] Swagger UI should show all API endpoints
- [ ] Try "Try it out" on a test endpoint

---

## Monitoring & Maintenance

### Daily Operations
- [ ] Monitor Railway Dashboard for errors
- [ ] Check `/api/*` endpoints for 5xx responses
- [ ] Review build logs after each deployment

### Updating Deployment

**To update code:**
```bash
# Make changes locally
git add .
git commit -m "Your changes"
git push origin main

# Railway auto-deploys within 2-3 minutes
# Monitor: Railway Dashboard → Deployments
```

**To update environment variables:**
1. Railway Dashboard → Variables
2. Edit/add variables
3. Deployment automatically restarts

### Common Issues

| Issue | Solution |
|-------|----------|
| Build fails | Check Railway logs; ensure `requirements.txt` and `package.json` are valid |
| 404 on frontend routes | Ensure `StaticFiles` mount is working; check frontend build succeeded |
| 403 Unauthorized on API | Verify `X-API-Key` header matches `API_KEY` environment variable |
| API returns 5xx | Check Railway logs; fix Python errors; redeploy |
| Slow builds | Upgrade Railway plan; optimize dependencies |

---

## Domain & Security

### Custom Domain (Optional)
1. Railway Dashboard → Settings
2. Add your domain
3. Update DNS records per Railway instructions
4. SSL certificate auto-provisioned

### API Key Security
- [ ] Change `API_KEY` from default value
- [ ] Use strong random string (32+ characters recommended)
- [ ] Rotate periodically
- [ ] Never commit `.env` with real keys

---

## Scaling & Performance

### If Usage Grows
1. Increase dyno size: Railway Dashboard → Settings → Resize
2. Enable horizontal scaling if needed
3. Consider caching layer (Redis)
4. Monitor response times

### Database (If Added)
- [ ] Add PostgreSQL plugin from Railway Marketplace
- [ ] Update backend to use DATABASE_URL
- [ ] Run migrations on release phase

---

## Rollback Plan

If deployment breaks:
```bash
# Option 1: Revert code and push
git revert HEAD
git push origin main
# Railway redeploys ~2 minutes

# Option 2: Manual rollback in Railway Dashboard
# Deployments → Previous version → Redeploy
```

---

## Success Indicators

✓ You're ready when:
- [ ] Railway dashboard shows "✓ Deployed"
- [ ] App loads at https://YOUR-PROJECT-ID.up.railway.app
- [ ] API responds with proper data (not 404/500)
- [ ] API Docs page is accessible
- [ ] Frontend communicates with backend
- [ ] No errors in browser console
- [ ] Logs show clean startup

---

## Support & Resources

- **Railway Docs:** https://docs.railway.app
- **General Troubleshooting:** https://docs.railway.app/troubleshooting
- **Procfile Format:** https://devcenter.heroku.com/articles/procfile
- **FastAPI Static Files:** https://fastapi.tiangolo.com/tutorial/static-files/
- **Railway Support:** https://railway.app/support

---

## Final Notes

- **Build time:** First build takes 5-10 minutes, subsequent ~2-3 minutes
- **File sizes:** Ensure `/data` CSVs don't exceed storage limits
- **Cold starts:** App may take 30s after idle period
- **Monitoring:** Set up alerts in Railway Dashboard for uptime

**Deployment complete! Your UrjaDrishti forecasting system is live.** 🚀
