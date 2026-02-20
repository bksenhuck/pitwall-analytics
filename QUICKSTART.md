# Quick Start Guide - Pitwall Analytics Refactored

## 🚀 5-Minute Setup

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run the App
```powershell
python run.py both
```

### Step 3: Open Browser
```
http://127.0.0.1:8050
```

That's it! ✅

---

## 📋 Common Commands

### Development
```powershell
# Run both services
python run.py both

# Run backend only
python run.py backend

# Run frontend only
python run.py frontend

# Run backend directly
python -m backend.app

# Run frontend directly
python -m frontend.app
```

### Testing Backend API
```powershell
# Health check
curl http://127.0.0.1:5000/api/health

# Get seasons
curl http://127.0.0.1:5000/api/data/seasons

# Get races for 2023
curl http://127.0.0.1:5000/api/data/races/2023

# Get session data
curl "http://127.0.0.1:5000/api/data/session?season=2023&event=Monaco"
```

---

## 🔧 Troubleshooting

### Backend won't start
- Check port 5000 is not in use
- Verify virtual environment is activated
- Check `.env` file exists

### Frontend won't start
- Check port 8050 is not in use
- Verify backend is running first
- Check BACKEND_API_URL in `.env`

### "Backend API: 🔴 Disconnected"
- Make sure backend is running: `python run.py backend`
- Check firewall settings
- Verify `.env` has correct BACKEND_API_URL

### Data not loading
- Check backend logs for errors
- Verify FastF1 cache is working
- Check internet connection (FastF1 needs it)

---

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `run.py` | Launch both services |
| `backend/app.py` | Backend entry point |
| `frontend/app.py` | Frontend entry point |
| `backend/api/data.py` | API endpoints |
| `backend/services/f1_data_service.py` | Business logic |
| `frontend/pages/analytics.py` | Main analytics page |
| `.env` | Configuration |
| `requirements.txt` | Dependencies |

---

## 🎯 What to Migrate First

1. ✅ **Test new structure** - Run and verify it works
2. 🔄 **Move data_loader.py functions** to `backend/services/f1_data_service.py`
3. 🔄 **Create API endpoints** in `backend/api/data.py`
4. 🔄 **Update one page** (e.g., analytics) to use API
5. 🔄 **Move charts** to `frontend/components/charts.py`
6. 🔄 **Repeat** for other pages

---

## 💡 Pro Tips

- Keep old code running while migrating
- Test each API endpoint before using in frontend
- Use browser DevTools Network tab to debug API calls
- Add print statements in backend to debug
- Start simple, add complexity later

---

## 📚 Full Documentation

See `README-NEW.md` for complete documentation.
See `ARCHITECTURE.md` for design details.

---

**Happy coding! 🏁**
