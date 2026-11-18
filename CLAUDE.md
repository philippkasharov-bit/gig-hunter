# gig-hunter

Freelance gig alert bot for the Russian market. Owner: design-only gigs (web design, logos, banners, UI/UX, presentations). Alerts only, no auto-apply. Runs on the owner's Windows PC (RU IP). Delivery: Telegram bot.

## Working style (owner's preferences)
- Dense, technical, no filler. Findings by severity P0/P1/P2.
- Work in batches, one layer each. Propose batch, wait for explicit confirm before the next. No scope creep, surgical diffs, functions <=30 lines, files <=300 lines, no magic numbers or hardcoded secrets.
- Owner is on Windows PowerShell: scripts are blocked by execution policy (use `npm.cmd`, `.venv\Scripts\python.exe` instead of activating). Give copy-paste commands one block per command.

## Status
Done (all pushed): 1 data contracts, 2 RSS adapter (FL.ru), 4 filter+score, 5 Telegram notifier, 6 runner/backoff/CLI.
Pending: 3 HTML adapters (Freelance.ru, Kwork, Avito, Profi.ru), 7 unit tests + README (incl. Windows scheduled-task autostart).
Not yet confirmed working live: `python -m gighunter --once` has NOT been run on the owner's PC with real Telegram. First task: make that run, fix what fails.

## Layout
src/gighunter: models (Gig, Source), config (FilterConfig), store (SQLite dedupe SeenStore), adapters/rss.py + registry.py, filtering.py (rank), notifier.py (Telegram Bot API via httpx), settings.py (.env), health.py (per-source backoff), runner.py (run_once), __main__.py (CLI, `--once`).
Config: config.yaml (keywords, stoplist, feeds, intervals). Secrets: .env (gitignored; see .env.example): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, optional TELEGRAM_PROXY.

## Verified facts
- FL.ru RSS `https://www.fl.ru/rss/all.xml` works, UTF-8, CDATA titles, links `/projects/<id>/slug.html`.
- Freelance.ru has NO RSS (`/rss/feed` returns HTML). Disabled in config.yaml; needs HTML adapter from `https://freelance.ru/project/search`.
- Kwork: category feed `https://kwork.ru/projects?c=41` not yet inspected; may need login/anti-bot. Avito: anti-bot, needs browser/proxy. Profi.ru: login-gated, disabled.
- Telegram may be blocked in RU: if api.telegram.org fails, set TELEGRAM_PROXY or use VPN.
- Owner accepts low-paid gigs (reviews), so min_budget_rub is null.

## Open items
- P0: owner's bot token was pasted into an earlier chat. Remind to revoke in @BotFather (/revoke) and update .env. Never write tokens to files or logs (httpx INFO log is silenced for this reason).
- P1: keyword "сайт" in config.yaml lets dev gigs through; owner undecided.
- P1: repo is public.
