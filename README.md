# AI Job Agent

An automated job-application agent that reads pending roles from Google Sheets, analyzes job descriptions with OpenAI, generates tailored outreach emails, sends them via Gmail with your resume attached, and updates the spreadsheet with results.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Google      │────▶│ LangGraph        │────▶│ Gmail API       │
│ Sheets      │◀────│ Pipeline         │     │ (send email)    │
└─────────────┘     └────────┬─────────┘     └─────────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │ OpenAI GPT      │
                      │ (analyze + write)│
                      └─────────────────┘
```

### Pipeline flow

```
START → Fetch Job → Analyze JD → Generate Email → Send Email → Update Sheet → END
```

### Project structure

| Layer | Path | Responsibility |
|-------|------|----------------|
| Entry | `main.py` | CLI, logging, orchestration |
| Graph | `graph.py` | LangGraph workflow wiring |
| State | `state.py` | `AgentState` TypedDict |
| Nodes | `nodes/` | Single-responsibility pipeline steps |
| Repository | `repositories/` | Google Sheets data access |
| Clients | `utils/` | Google Sheets, OpenAI, Gmail wrappers |
| Config | `config.py` | Environment-based settings |

## Google Sheet format

Create a sheet with these columns (row 1 = headers):

| Job Role | Job Description | Recruiter Email | Status | Timestamp | Error |
|----------|-----------------|-----------------|--------|-----------|-------|
| Software Engineer | ... | recruiter@co.com | Pending | | |

- **Status** values: `Pending` → `Sent` or `Failed`
- On success, **Timestamp** is set automatically
- On failure, **Error** stores the message

## Installation

### Prerequisites

- Python 3.11+
- Google Cloud service account with Sheets API access
- Gmail OAuth credentials (for sending email)
- OpenAI API key

### Setup

```bash
git clone <your-repo-url>
cd ai-job-agent
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

1. Place your Google service account JSON as `credentials.json` in the project root.
2. Share your Google Sheet with the service account email.
3. Fill in `.env` with your OpenAI key, sheet name/ID, and Gmail settings.
4. Place your resume at `resumes/resume.pdf`.
5. Run Gmail OAuth once locally to generate `gmail_token.json`.

## Usage

### Step 1 — Verify Google Sheets connection

```bash
python main.py --print-sheets
```

Expected output (headers + data rows):

```
Job Role    Job Description    Recruiter Email    Status
...         ...                ...                Pending
```

### Run the full agent (one pending job per run)

```bash
python main.py
```

The agent processes **one** `Pending` row per invocation:

1. Fetches the first pending job
2. Analyzes the job description (skills, technologies, responsibilities, experience)
3. Generates a professional email (≤ 180 words)
4. Sends it via Gmail with resume attached
5. Updates the sheet to `Sent` or `Failed`

## GitHub Actions

The workflow in `.github/workflows/agent.yml` runs every **5 minutes** and on manual dispatch.

### Required secrets

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model name (e.g. `gpt-4o`) |
| `GOOGLE_CREDENTIALS_JSON` | Full service account JSON |
| `GOOGLE_SHEETS_SPREADSHEET_ID` or `GOOGLE_SHEET_NAME` | Target spreadsheet |
| `GOOGLE_SHEETS_WORKSHEET_NAME` | Worksheet tab name |
| `GMAIL_CREDENTIALS_JSON` | Gmail OAuth client JSON |
| `GMAIL_TOKEN_JSON` | Pre-authorized Gmail token JSON |
| `GMAIL_SENDER_EMAIL` | Sender address |

## Screenshots

_Add screenshots of your Google Sheet, a sent email, and a successful GitHub Actions run here after setup._

## Future improvements

- Process multiple pending jobs per run with rate limiting
- Retry failed rows with exponential backoff
- Support custom email templates per role type
- Add candidate profile / resume context to GPT prompts
- Web dashboard for monitoring application status
- Slack or email notifications on failures
- Unit and integration tests with mocked APIs

## License

MIT
