# 📈 Trade Alert → Execution Flow (v2: Pluggable + Reactive)

---

## 📝 1. Product Requirements Document (PRD)

### 💡 One-Sentence Summary
An automated, pluggable trading system that reacts to trade alerts from email (via Gmail Pub/Sub), extracts actionable details using LLMs, scrapes trade sizing from a secure forum, executes orders through Alpaca, and logs every action to Google Sheets.

---

### 👣 User Flow
1. A new trade alert is pushed to the system (via Gmail Pub/Sub)
2. The alert is parsed and normalized by an abstract `AlertProvider`
3. A `Trade ID` is created and a "pending" record is logged
4. System logs into `io-fund.com` and scrapes the forum post
5. LLM extracts sizing (e.g., “Buy 5% of portfolio”) from scraped content
6. System calculates the position size using Alpaca account balance
7. Market order is placed via Alpaca API
8. Result (success, fail, or pending) is logged as a new row in Google Sheets
9. LLM generates a user-friendly error message if the trade fails

---

### 🎯 Target Audience
- Algorithmic traders or builders following structured alert feeds
- Developers exploring LLM automation
- Internal tools team building reactive trading bots

---

### 🔧 Core Features
- **Pluggable alert ingestion** via `AlertProvider` abstraction
- Reactive trigger from Gmail → Pub/Sub → Webhook
- LLM-based parsing for email and forum content
- Trade sizing logic + execution via Alpaca
- Append-only event stream logging to Google Sheets
- LLM-generated explanations on failure

---

### 🛠️ Stack / Tools
- **Python** (core orchestrator)
- **Gmail API + Google Pub/Sub** (email trigger)
- **Alpaca API** (market order execution)
- **BeautifulSoup** (HTML scraping)
- **OpenAI / Claude API** (LLM parsing & summarization)
- **gspread** (Google Sheets integration)
- **Render / Railway / VPS** (hosting)
- **Flask / FastAPI** (webhook endpoint)

---

### 🧠 Optional Enhancements
- Add new `AlertProvider`s: Discord, Telegram, RSS, Manual UI
- Retry logic, trade queue, alert deduplication
- Supabase or Postgres DB for long-term state

---

## 🧱 2. Architecture Overview

```
[ Gmail (Pub/Sub) ]
        |
        v
[ Webhook Receiver (FastAPI) ]
        |
        v
[ AlertProvider (GmailPubSubProvider) ]
        |
        v
[ AlertHandler → TradeFlow(alert) ]
        |
        v
 ┌────────────────────────────────────────────┐
 │ TradeFlow Orchestration:                   │
 │  • LLM parses email                        │
 │  • Login & scrape forum                    │
 │  • LLM extracts sizing                     │
 │  • Compute quantity                        │
 │  • Execute via Alpaca                      │
 │  • Log to Google Sheet                     │
 │  • Generate error explanation (if needed)  │
 └────────────────────────────────────────────┘
```

---

## 💾 Data Model Summary (Google Sheets)

| Field         | Example                  |
|---------------|--------------------------|
| `Trade ID`    | `email-20250802-001`     |
| `Source`      | `gmail`                  |
| `Ticker`      | `COIN`                   |
| `Action`      | `Buy`                    |
| `Sizing`      | `5%`                     |
| `Status`      | `pending` / `success` / `fail` |
| `Order ID`    | Alpaca order ref         |
| `Message`     | “Executed” / error info  |
| `Timestamp`   | UTC datetime             |

---

## 📦 Project Structure

```plaintext
tradeflow/
├── main.py                      # Entry point (webhook handler)
├── config.py                    # Secrets, API keys, constants
├── requirements.txt             # Python dependencies
├── .env                         # (Optional) local secrets
│
├── core/
│   ├── orchestrator.py          # TradeFlow controller
│   ├── models.py                # Alert, TradeEvent, enums
│   └── utils.py                 # Logging, ID generation, helpers
│
├── providers/                  # Alert sources (pluggable)
│   ├── base.py                  # Abstract AlertProvider class
│   └── gmail_pubsub.py          # Gmail Pub/Sub implementation
│
├── parsers/
│   ├── email_llm.py             # LLM-based email parser
│   ├── forum_scraper.py         # HTML scraper for io-fund
│   └── forum_llm.py             # LLM sizing extraction from scraped HTML
│
├── broker/                     # Trading and brokerage integration
│   ├── alpaca_client.py         # Alpaca SDK wrapper
│   └── sizing.py                # Position size calculator
│
├── logging/
│   └── google_sheets.py         # GSpread logic for appending logs
│
├── llm/
│   └── explain_failure.py       # Optional: LLM-generated error summaries
│
├── web/
│   └── server.py                # FastAPI or Flask webhook server
│
└── tests/
    └── test_tradeflow.py        # Unit tests, mocks, etc.
```
---

## 🚀 Deployment Overview

### ✅ Components to Deploy

| Component              | Type           | Hosting Option         |
|------------------------|----------------|-------------------------|
| **Webhook Server**     | FastAPI/Flask  | Render / Railway / VPS |
| **Trade Orchestrator** | Python service | Same as above          |
| **Google Sheets Writer** | Python module | Embedded in app        |
| **LLM Calls**          | API (OpenAI, Claude) | Cloud API        |
| **Gmail Pub/Sub Listener** | Google Infra | Google Cloud Project   |

---

### 🛠️ Hosting Stack Option

Use **Render.com** (or Railway.app) to host the Python app:
- Runs the webhook server
- Processes Gmail Pub/Sub messages
- Executes trading logic

---

### 📦 Deployment Flow

```text
[Gmail] ➝ [Google Pub/Sub] ➝ [Webhook on Render (FastAPI)]

Webhook does:
  • Parse Alert
  • Scrape forum
  • Run LLM(s)
  • Call Alpaca
  • Log to Google Sheets
```

---

## 🧭 Service Architecture Diagram

```text
                +-------------------------+
                |    Gmail (Trade Alert)  |
                +-----------+-------------+
                            |
                            v
         +------------------------+
         |  Google Cloud Pub/Sub  |
         +-----------+------------+
                     |
          HTTP Push  v
              +------------------------+
              |  Webhook Server (FastAPI) |
              |  (Render / Railway)     |
              +------------+-----------+
                           |
                           v
                +--------------------------+
                |  TradeFlow Orchestrator  |
                | - LLM Email Parser       |
                | - Forum Scraper + LLM    |
                | - Alpaca Trade API       |
                | - Google Sheet Logger    |
                +--------------------------+
```