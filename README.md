# Job Application Bot

Automated job application bot for engineering roles with visa sponsorship. Searches LinkedIn, Indeed, Seek, Reed, and StepStone across 20+ countries, generates AI-tailored cover letters, and applies automatically or semi-automatically.

**Cost:** ~$3-6/month (Claude API only). Everything else is free.

---

## Install on a New PC (Windows)

Open **PowerShell as Administrator** and run this single command:

```powershell
irm https://raw.githubusercontent.com/bilalaslam1244-stack/job-application-bot/master/install.ps1 | iex
```

This automatically:
- Installs Python 3.11 (if not present)
- Downloads the bot
- Installs all packages
- Downloads the browser (~150MB, one time)
- Creates `config.yaml` for you to fill in
- Schedules the bot to run at **8am, 1pm, 6pm** daily

---

## Setup After Install

### Step 1 — Fill in config.yaml

Open `config.yaml` (in your home folder → `job-application-bot`) in Notepad or VS Code.

Replace every `REPLACE_ME` with your actual values:

```yaml
anthropic_api_key: "sk-ant-..."        # from console.anthropic.com
telegram_bot_token: "123456:ABC..."    # from @BotFather on Telegram
telegram_chat_id: "987654321"          # your Telegram user ID (see below)
```

Then fill in your email and password for each job portal.

### Step 2 — Get your Telegram bot token + chat ID

1. Open Telegram → search `@BotFather` → send `/newbot`
2. Name it anything (e.g. "My Job Bot")
3. Copy the **token** → paste into `telegram_bot_token`
4. Start a chat with your new bot (send it `/start`)
5. Open in browser (replace TOKEN): `https://api.telegram.org/botTOKEN/getUpdates`
6. Find `"chat":{"id":XXXXXXXXX}` → copy that number → paste into `telegram_chat_id`

### Step 3 — Get your Anthropic API key

1. Go to `console.anthropic.com`
2. Sign up / log in → API Keys → Create Key
3. Copy and paste into `anthropic_api_key`

### Step 4 — Test

Open PowerShell in the `job-application-bot` folder:

```powershell
.venv\Scripts\activate
python main.py config
```

Should print: `Config valid.`

### Step 5 — First run (search only)

```powershell
python main.py search
```

This finds jobs but does NOT apply. Check what it found:

```powershell
python main.py status
```

### Step 6 — Full run

```powershell
python main.py run
```

Or just double-click `run.bat`.

---

## Commands

| Command | What it does |
|---------|-------------|
| `python main.py run` | Full cycle: search + apply + check statuses |
| `python main.py search` | Find new jobs only, no applications |
| `python main.py apply` | Apply to jobs already found in DB |
| `python main.py check` | Check application statuses on portals |
| `python main.py status` | View dashboard (how many found/applied/viewed etc.) |
| `python main.py config` | Validate your config.yaml |

---

## How It Works

### LinkedIn
Bot searches LinkedIn with stealth mode (human-like behaviour). When it finds a matching job, it sends you a **Telegram message with the link**. You open the link and apply manually. Your main LinkedIn account is protected — no automated form submissions.

### Indeed
Bot applies fully automatically via Indeed Quick Apply. Fills in your details and cover letter, submits without you needing to do anything.

### Seek, Reed, StepStone
Bot finds the job, fills in the application form, then **opens the browser for you** to review and click Submit. Takes ~30 seconds per application.

---

## Telegram Notifications

You'll receive messages for:
- New matching job found
- Application submitted automatically
- Application viewed by employer
- Status changed (In Review, Interview, Rejected)
- Recruiter message received
- CAPTCHA needed (you solve it, bot continues)
- Daily digest every morning

---

## Target Regions

| Priority | Countries |
|----------|-----------|
| Highest | UAE, Qatar, Saudi Arabia, Australia, France, Belgium, UK, Ireland |
| High | Netherlands, Germany, Canada, Luxembourg, New Zealand |
| Medium | Singapore, Sweden, Norway, Denmark, Switzerland, Austria, Finland |
| Worth casting | USA, Japan, South Korea, Portugal, Spain, Italy, Czech Republic, Poland, Hong Kong |

---

## Troubleshooting

**`Config error: Config file not found`** → You haven't created `config.yaml` yet. Copy from `config.template.yaml` and fill it in.

**`playwright._impl._errors.TimeoutError`** → The job portal changed its HTML. Open an issue on GitHub.

**LinkedIn not finding jobs** → Your session may have expired. Delete `data/sessions/linkedin_session.json` and run again — it will log in fresh.

**CAPTCHA message on Telegram** → Open a browser, go to the portal URL shown, solve the CAPTCHA, then run the bot again.
