# gig-hunter

Telegram alerts for new **design** gigs on Russian freelance platforms
(web/UI/UX, logos, branding, banners, presentations, infographics).
Alerts only: it never applies or replies for you.

| Source | How | Status |
|---|---|---|
| FL.ru | RSS `fl.ru/rss/all.xml` | on |
| Freelance.ru | HTML task feed `freelance.ru/task` | on |
| Kwork | JSON embedded in `kwork.ru/projects?c=15` (Дизайн) | on |
| Avito | anti-bot, needs browser/proxy | off, no adapter |
| Profi.ru | login required | off, no adapter |

Every 5 minutes it fetches all enabled sources, keeps gigs that match your
category keywords (and none of the stop words), ranks them, and sends up to 5 new ones to
Telegram. Sent gigs are remembered in `data/gighunter.db`, so nothing repeats.
A source that fails is backed off (5 min, doubling, max 1 h) without stopping the others.

## Setup (Windows, PowerShell)

Needs Python 3.12+. Commands avoid `Activate.ps1`, so the default execution policy is fine.

```powershell
git clone https://github.com/philippkasharov-bit/gig-hunter.git
```
```powershell
cd gig-hunter
```
```powershell
python -m venv .venv
```
```powershell
.venv\Scripts\python.exe -m pip install -e .[dev]
```
```powershell
copy .env.example .env
```

### Telegram

1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Press **Start** in your new bot (a bot cannot message you first).
3. Get your numeric chat id from **@userinfobot**.
4. Edit `.env` (`notepad .env`):

```
TELEGRAM_BOT_TOKEN=123456789:AA...
TELEGRAM_CHAT_ID=123456789
TELEGRAM_PROXY=
```

`.env` is gitignored. Never commit it or paste the token anywhere; if it leaks,
revoke it in @BotFather (`/mybots` → bot → API Token → Revoke).

## Run

One check, then exit (good for testing):

```powershell
.venv\Scripts\python.exe -m gighunter --once
```

Continuous (checks every `poll_interval_s`, Ctrl+C to stop):

```powershell
.venv\Scripts\python.exe -m gighunter
```

The log line `run: RunStats(fetched=…, candidates=…, sent=…, failed_sources=[…])`
summarises each check.

## Autostart with Windows

`scripts\gighunter.cmd` runs the bot from the repo folder, appends logs to
`data\gighunter.log` and restarts it 60 s after a crash. Put a minimized
shortcut to it in your Startup folder (no admin rights needed). Run this from
the repo folder:

```powershell
$s = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\gighunter.lnk"); $s.TargetPath = "$PWD\scripts\gighunter.cmd"; $s.WorkingDirectory = "$PWD"; $s.WindowStyle = 7; $s.Save()
```

It starts at your next sign-in as a minimized `gig-hunter` window; closing that
window stops the bot. Start it now without signing out:

```powershell
start "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\gighunter.lnk"
```

Remove autostart:

```powershell
del "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\gighunter.lnk"
```

Watch the log:

```powershell
Get-Content data\gighunter.log -Tail 20 -Wait
```

## Configuration (`config.yaml`)

| Key | Meaning |
|---|---|
| `sources` | turn each platform on/off |
| `feeds` | URL per source |
| `categories` | tag → keywords (case-insensitive substrings). A gig must contain at least one keyword; it is tagged with the specific category that has the most hits (title counts more, ties go to the earlier one), shown as a hashtag like `#логотип`. The **last** category (`дизайн`) is generic: used only when no specific category hits. Short Latin words (`ui`) match whole words only |
| `stoplist` | any hit rejects the gig |
| `keyword_free_sources` | sources already limited to design (default: `kwork`); keyword match skipped, other filters still apply |
| `min_budget_rub` | budget floor; `null` = none. Gigs without a stated budget always pass |
| `max_age_hours` | skip older gigs |
| `poll_interval_s` | seconds between checks (keep ≥ 60 to avoid being rate-limited) |
| `max_alerts_per_run` | the rest wait for the next check |
| `db_path` | dedupe database |

Score: +10 per keyword in the title, +3 per keyword in the description,
+2 if a budget is stated, +3 if posted within 3 hours.
Restart the bot after editing the config.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Parsers are tested against small synthetic copies of each site's markup, so a
site redesign shows up as an `AdapterError` in the log, not a crash.

## Troubleshooting

- **`Unauthorized` / `telegram error 401`**: wrong or revoked token in `.env`.
- **`telegram error 400: chat not found`**: wrong `TELEGRAM_CHAT_ID`, or you never pressed Start in the bot.
- **`ValidationError ... chat_id`**: `TELEGRAM_CHAT_ID` is empty or `.env` was not saved.
- **Telegram unreachable** (`request failed: ConnectError`): set `TELEGRAM_PROXY=http://host:port`
  (for `socks5://` first run `.venv\Scripts\python.exe -m pip install httpx[socks]`) or use a VPN.
  The proxy is used for Telegram only, never for the job sites.
- **`<source> failed: AdapterError`**: the site changed its layout; that source is
  backed off while the others keep working. The parser needs updating.
