# gig-hunter

Freelance gig alert bot for the Russian market. Owner: design-only gigs (web design, logos, banners, UI/UX, presentations). Alerts only, no auto-apply. Runs on the owner's Windows PC (RU IP). Delivery: Telegram bot.

## Working style (owner's preferences)
- Dense, technical, no filler. Findings by severity P0/P1/P2.
- Work in batches, one layer each. Propose batch, wait for explicit confirm before the next. No scope creep, surgical diffs, functions <=30 lines, files <=300 lines, no magic numbers or hardcoded secrets.
- Owner is on Windows PowerShell: scripts are blocked by execution policy (use `npm.cmd`, `.venv\Scripts\python.exe` instead of activating). Give copy-paste commands one block per command.

## Status
Done: 1 data contracts, 2 RSS adapter (FL.ru), 3 HTML adapters (Freelance.ru, Kwork; merged PR #1), 4 filter+score, 5 Telegram notifier, 6 runner/backoff/CLI, 7 tests (pytest, 41) + README + autostart.
Verified live on owner's PC 2026-11-18: `--once` delivers to Telegram, dedupe works, launcher works from another cwd.
Deferred: Avito (anti-bot), Profi.ru (login). Autostart = Startup-folder shortcut to scripts/gighunter.cmd (no admin, minimized, restart loop), not Task Scheduler (ONLOGON needs admin).

## Layout
src/gighunter: models (Gig, Source), config (FilterConfig), store (SQLite dedupe SeenStore), adapters/{common,rss,freelance_ru,kwork,registry}.py, filtering.py (rank), notifier.py (Telegram Bot API via httpx), settings.py (.env), health.py (per-source backoff), runner.py (run_once), __main__.py (CLI, `--once`).
tests/ (pytest, synthetic markup fixtures; `.venv\Scripts\python.exe -m pytest -q`). scripts/gighunter.cmd (autostart launcher, logs to data/gighunter.log).
Config: config.yaml (keywords, stoplist, feeds, intervals). Secrets: .env (gitignored; see .env.example): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, optional TELEGRAM_PROXY.

## Verified facts
- FL.ru RSS `https://www.fl.ru/rss/all.xml` works, UTF-8, CDATA titles, links `/projects/<id>/slug.html`.
- Freelance.ru has NO RSS. `https://freelance.ru/task` (UTF-8, no login): 25 `article.task-card` per page, id in `/task/view/<id>`, date in foot-item `title` "dd.mm.yyyy HH:MM" MSK, budget `.task-card__budget .bold` + `.cost-unit` ("/ заказ" or "/ час").
- Kwork: no login needed. `c=41` is bots/scripts, NOT design; design = `c=15`. Data in `window.stateData.wantsListData.pagination` (12/page, `next_page_url`, not sorted by date). `priceLimit` = buyer's max, `date_create` MSK.
- httpx 0.28 `params=` REPLACES the URL query; get_page merges via `copy_merge_params`.
- Avito: anti-bot, needs browser/proxy. Profi.ru: login-gated.
- Telegram api.telegram.org reachable directly from owner's PC (no proxy needed as of 2026-11-18). Bot: @PCashmirGPT_bot; another program may also poll it (getUpdates queue was drained).
- Owner accepts low-paid gigs (reviews), so min_budget_rub is null.

## Open items
- P0: bot token was exposed in a screenshot in chat (2026-11-18). Remind to revoke in @BotFather and update .env. Never write tokens to files or logs (httpx INFO log is silenced for this reason).
- P1: keyword noise, owner undecided: "сайт" lets dev/SEO gigs through; "карточк" lets copywriting ("карточки товаров") through.
- P2: Kwork design category already on-topic but 19/44 dropped by keyword filter; option: skip keyword check for Kwork.
- P2: data/gighunter.log grows unbounded (~1 line/5 min, small).
- P1: repo is public.
