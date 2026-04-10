# GovCon Pipeline — Digital Services

A government contracting opportunity tracker for a HUBZone / Small Business digital services firm. Tracks solicitations from SAM.gov, SBIR.gov, and USASpending automatically via GitHub Actions, and serves a full pipeline management app via GitHub Pages.

---

## 🚀 One-Time Setup (15 minutes)

### 1. Create the GitHub repo

```bash
gh repo create govcon-pipeline --public
cd govcon-pipeline
git init && git add . && git commit -m "init"
git push -u origin main
```

### 2. Add your SAM.gov API Key as a GitHub Secret

1. Get a free key at [api.data.gov/signup](https://api.data.gov/signup)
2. In your GitHub repo → **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `SAM_API_KEY` · Value: your key
5. Save

### 3. Enable GitHub Pages

1. Repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` · Folder: `/ (root)`
4. Save — your site will be live at `https://YOUR-USERNAME.github.io/govcon-pipeline`

### 4. Run the first data fetch manually

1. Repo → **Actions → Fetch GovCon Opportunities**
2. Click **Run workflow**
3. Wait ~60 seconds — it commits fresh data to `data/opportunities.json`
4. Reload your GitHub Pages site — you now have live SAM.gov data

---

## 🔄 How It Works

```
GitHub Actions (daily @ 6 AM ET)
    └── scripts/fetch_opportunities.py
          ├── SAM.gov Opportunities API  → filtered by your NAICS codes
          ├── SBIR.gov API               → AI/ML & software solicitations
          └── Writes → data/opportunities.json

GitHub Pages
    └── index.html reads data/opportunities.json
          ├── Scores each opp (0–99 fit score)
          ├── Displays pipeline dashboard
          ├── Kanban capture board
          └── Proposal outline generator
```

No backend, no hosting costs, no CORS issues.

---

## 📁 Repo Structure

```
govcon-pipeline/
├── index.html                        # Main pipeline app (GitHub Pages)
├── data/
│   └── opportunities.json            # Auto-updated nightly by GitHub Actions
├── scripts/
│   └── fetch_opportunities.py        # Data fetcher (SAM.gov + SBIR)
├── .github/
│   └── workflows/
│       └── fetch-opportunities.yml   # Nightly cron job
└── README.md
```

---

## 🎯 Your NAICS Codes (Pre-configured)

| Code   | Description                        |
|--------|------------------------------------|
| 541511 | Custom Computer Programming        |
| 541512 | Computer Systems Design Services   |
| 541519 | Other Computer Related Services    |
| 518210 | Data Processing / Cloud Hosting    |
| 541715 | R&D / AI-ML Services               |

Edit `scripts/fetch_opportunities.py` → `NAICS_CODES` to add more.

---

## 🏢 Certifications Tracked

- **Small Business (SB)**
- **HUBZone** ← priority set-aside
- **WOSB** (Women-Owned Small Business)

---

## 🛠 Local Development

For local dev with live SAM.gov data, use the included proxy server:

```bash
# In the same folder as server.py
python3 server.py
# Open http://localhost:8000
```

`server.py` is not needed for the GitHub Pages deployment — it's only for local testing.

---

## 📬 Questions / Issues

File an issue in this repo or reach out to your team.
