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
- Resolved 2026-11-18: removed keywords "сайт" and "карточк" (dev/SEO/copywriting noise). Trade-off: marketplace card *design* gigs without other keywords are now missed.
- Resolved 2026-11-18: Kwork skips keyword match via config `keyword_free_sources: [kwork]` (stoplist/age/budget still apply); Kwork matches 22 -> 35/40. Off-niche Kwork design (3D models/printing, Roblox, Revit, interiors, architecture) blocked by narrow stoplist phrases; bare "3d"/"интерьер" were tried and rejected: they hit in-niche descriptions ("3D-мокап", "товар в интерьере").
- Categories (2026-11-18): config `categories` (tag -> keywords) replaced flat `keywords`; alerts carry `#tag`. Last category (`дизайн`) is generic fallback only, else it swallowed specific gigs. P2: Kwork marketplace-card gigs land in #дизайн (a #маркетплейс category would re-admit FL/Freelance copywriting noise); "интерфейс" lets some dev gigs into #веб; "упаковк" also hits SMM "упаковка профиля".
- P2: data/gighunter.log grows unbounded (~1 line/5 min, small).
- P1: repo is public.
