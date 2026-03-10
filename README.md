# LP Prospect Enrichment & Scoring Engine

AI-powered system for enriching and scoring LP (Limited Partner) prospects for PaceZero Capital Partners' fundraising pipeline.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Next.js UI  │────>│  FastAPI Backend  │────>│  PostgreSQL  │
│  (Port 3000) │     │  (Port 8000)     │     │  (Port 5432) │
└──────────────┘     └────────┬─────────┘     └──────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────┴─────┐    ┌───────┴───────┐
              │  Tavily   │    │   Anthropic   │
              │ (Search)  │    │   (Claude)    │
              └───────────┘    └───────────────┘
```

**Pipeline Flow**: CSV Upload → Parse & Deduplicate → Tavily Web Search → Claude Extraction → Claude Scoring → Validation → Dashboard

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- API Keys: [Tavily](https://tavily.com) + [Anthropic](https://console.anthropic.com)

### 1. Database Setup
```bash
# Start PostgreSQL (or use Docker)
docker compose up db -d

# Create database
createdb lp_enrichment
```

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env with your API keys: TAVILY_API_KEY, ANTHROPIC_API_KEY

pip install -e .

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Run the Pipeline
1. Open http://localhost:3000
2. Navigate to **Import CSV**
3. Upload `data/challenge_contacts.csv`
4. Click **Start Enrichment & Scoring Pipeline**
5. Monitor progress, then view results on the **Dashboard**

### Docker Compose (Alternative)
```bash
cp backend/.env.example .env
# Edit .env with API keys
docker compose up
```

## Scoring System

| Dimension | Weight | Source |
|-----------|--------|--------|
| D1: Sector & Mandate Fit | 35% | AI-scored (Tavily + Claude) |
| D2: Relationship Depth | 30% | Pre-computed from CSV |
| D3: Halo & Strategic Value | 20% | AI-scored |
| D4: Emerging Manager Fit | 15% | AI-scored |

**Tiers**: PRIORITY CLOSE (>=8.0) | STRONG FIT (>=6.5) | MODERATE FIT (>=5.0) | WEAK FIT (<5.0)

## Key Features

- **AI Web Enrichment**: Tavily search + Claude extraction per organization
- **Calibration-Anchored Scoring**: 4 reference organizations ensure scoring accuracy
- **Org-Level Deduplication**: Multiple contacts from same org share enrichment data
- **6-Point Validation Layer**: Catches GP/service provider misscoring, calibration drift, data quality issues
- **Cost Tracking**: Per-API-call cost logging with projections
- **Resume Capability**: Interrupted pipelines restart from last unprocessed org
- **Check Size Estimation**: AUM-based commitment range by org type

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ingest/csv` | Upload CSV |
| POST | `/api/v1/pipeline/{id}/start` | Start pipeline |
| GET | `/api/v1/pipeline/{id}/status` | Check progress |
| GET | `/api/v1/prospects` | List scored prospects (paginated, sortable, filterable) |
| GET | `/api/v1/prospects/{id}` | Prospect detail |
| GET | `/api/v1/dashboard/summary` | Dashboard data |
| GET | `/api/v1/costs/{run_id}` | Cost breakdown |

## Estimated Cost per Run

| Scale | Est. Cost |
|-------|-----------|
| 100 contacts (~94 orgs) | ~$4.70 |
| 1,000 contacts (~750 orgs) | ~$37.50 |
| 5,000 contacts (~3,000 orgs) | ~$150.00 |
