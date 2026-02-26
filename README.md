# Skylark BI Agent

A conversational Business Intelligence agent powered by **Groq (Llama 3.3 70B)** and **Monday.com GraphQL API**. Answers founder-level queries against live CRM (Deals Pipeline) and operational (Work Orders) data with a real-time agent trace panel.

## Architecture

```
User → Chat UI (HTML/CSS/JS · SSE streaming)
         ↓
    FastAPI Backend
         ↓
    Groq API — Llama 3.3 70B (function calling)
         ↓
    Monday.com GraphQL API (live, no cache)
         ↓
    Data Normalizer (sectors, dates, currency, nulls)
         ↓
    Streamed response + tool traces to UI
```

## Features

- **Live Monday.com API calls** — every query fetches fresh data, no caching
- **Real-time agent trace panel** — watch API calls happen as the agent works
- **Data resilience** — handles 50%+ missing values, inconsistent formats, mixed date types
- **Cross-board analysis** — correlates Deals and Work Orders by deal name
- **Founder-level insights** — pipeline health, sector performance, billing vs revenue

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| AI | Groq · Llama 3.3 70B | Free tier, ultra-fast inference, OpenAI-compatible tool calling |
| Backend | Python + FastAPI | Fast to build, native async, SSE streaming |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, full control, fast load |
| Monday.com | GraphQL API v2 | Official API, flexible queries, up to 500 items/call |
| Hosting | Render.com (free) | Auto-deploy from GitHub, HTTPS, env var management |

## Quick Start

### 1. Get API keys (both free, no credit card)

**Monday.com API token:**
1. Sign up at monday.com (free plan)
2. Profile picture → Admin → API → copy your Personal API Token

**Groq API key:**
1. Go to https://console.groq.com
2. Sign up → API Keys → Create new key → copy it

### 2. Set up Monday.com Boards

1. Create board **"Deals Pipeline"** → import `Deal funnel Data.xlsx`
   - Configure columns: Deal Stage (Dropdown), Sector/service (Dropdown), Masked Deal value (Numbers), Deal Status (Status), Dates as Date columns
2. Create board **"Work Orders Tracker"** → import `Work_Order_Tracker Data.xlsx`
   - **Important:** actual column headers are in row 1 — skip row 0 on import
3. Note both Board IDs from the URL: `monday.com/boards/<BOARD_ID>`

### 3. Configure environment

```bash
cp .env.example .env
# Fill in your values:
# MONDAY_API_TOKEN=...
# GROQ_API_KEY=...
# DEALS_BOARD_ID=...
# WORK_ORDERS_BOARD_ID=...
```

### 4. Run locally

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
# Open http://localhost:8000
```



## Sample Queries

| Question | Tool Used |
|----------|-----------|
| "How's our pipeline this quarter?" | `query_deals_board` |
| "Which sector has the most deal value?" | `query_deals_board` |
| "Show all in-progress work orders" | `query_work_orders_board` |
| "Compare pipeline vs billed amounts" | `cross_board_analysis` |
| "Powerline sector deep dive" | `cross_board_analysis` |
| "Which owner has the most open deals?" | `query_deals_board` |

## Data Quality Notes

| Issue | Coverage | How It's Handled |
|-------|----------|-----------------|
| Missing deal values | 52% | Reports "X/346 deals have value data" |
| Missing actual close dates | 91% | Falls back to tentative close date |
| Work orders header in row 1 | Structural | Skip row 0 on Monday.com import |
| Sector name variations | Low | Canonical map: "power line" → "Powerline" |
| Missing collection data | ~99% | Explicit caveat in every response |
| Mixed date formats | Multiple | Tries 10+ formats incl. Excel serial |

## File Structure

```
skylark-bi-agent/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI + SSE endpoint
│   ├── agent.py          # Groq function-calling loop
│   ├── monday_client.py  # Monday.com GraphQL client
│   ├── normalizer.py     # Data cleaning utilities
│   └── tools.py          # Tool definitions + executor
├── frontend/
│   ├── index.html        # Chat UI with trace panel
│   └── assets/
│       └── style.css     # Styles
├── .env.example
├── render.yaml
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONDAY_API_TOKEN` | Monday.com Personal API Token |
| `GROQ_API_KEY` | Groq API key from console.groq.com |
| `DEALS_BOARD_ID` | Monday.com board ID for Deals Pipeline |
| `WORK_ORDERS_BOARD_ID` | Monday.com board ID for Work Orders |
