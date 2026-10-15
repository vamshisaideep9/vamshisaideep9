# Setup

Everything on the profile is generated in this repo. There are no third-party stat cards, badges or
view counters. One workflow (`.github/workflows/profile.yml`) does it all:

```
profile.config.json ─┐
                     ├─► scripts/build_assets.py ─► assets/*.svg ─► README.md
METRICS_TOKEN ─► scripts/fetch_stats.py ─► stats.json ─┘
```

## 1. Allow the workflow to commit
Repo → **Settings → Actions → General → Workflow permissions** → **Read and write permissions** → Save.

## 2. Show private & organisation work in the stats
GitHub's public APIs (and every hosted stats card) only see public repos. To count private and org work,
the workflow runs with **your own token**. It publishes only totals and language percentages. Repo names,
code and commit messages are never published.

1. GitHub → Settings → Developer settings → **Personal access tokens → Tokens (classic)** → *Generate new token*.
   Scopes: **`repo`**, **`read:org`**, **`read:user`**. Set an expiry and renew it when it lapses.
   If an org uses SSO, click **Configure SSO → Authorize** next to the token.
2. This repo → **Settings → Secrets and variables → Actions → New repository secret**.
   Name: `METRICS_TOKEN`. Value: the token. Never commit it to a file.
3. **Actions → Profile → Run workflow**. It refreshes `stats.json` and every SVG, then runs daily at 06:00 IST.

Also turn on **Settings → Public profile → Contributions & activity → Include private contributions on my profile**,
so GitHub's own contribution graph matches the numbers.

Without the secret, the workflow keeps the last committed `stats.json` and still rebuilds the visuals.

## 3. Fill in your links
In `README.md`, search for `YOUR-` and replace the booking link, email, LinkedIn, portfolio and résumé URLs.
Button labels live in `profile.config.json → links`.

## 4. Edit text, projects or stack
Edit `profile.config.json` and commit. The workflow regenerates every SVG.

| Key | Controls |
| --- | --- |
| `name`, `title`, `status`, `roles`, `facts` | Hero (roles rotate; the 4th fact is live contributions) |
| `about.statement` | Serif statement. Wrap words in `*asterisks*` for the lime italic accent |
| `about.recruiters`, `about.clients` | The two panels under the statement |
| `services` | "What I build" list |
| `projects` | Project cards. Add a matching `<img src="assets/project-<slug>.svg">` cell in README |
| `stack` | Layered stack diagram |

## 5. Preview locally
```bash
pip install fonttools brotli
GH_TOKEN=$(gh auth token) python scripts/fetch_stats.py   # optional: refresh stats
python scripts/build_assets.py
```
Open any `assets/*.svg` in a browser.

## 6. Polish the profile itself (Settings → Public profile)
- **Bio (160 chars):** `AI & Full-Stack Engineer · Advanced RAG, LLM agents · FastAPI + Next.js · Android · SEO · Open to roles & freelance`
- Fill in company, location, website and social links. Recruiters filter on them.
- **Pin 6 repos:** your strongest AI, full-stack, Android and SEO work. Give each a description, topics, a live link and a screenshot.
- Archive tutorial and practice repos. Don't pin forks.

## Fonts
Instrument Serif and Geist (SIL Open Font License; licences in `scripts/fonts/`). They are subset and embedded
in each SVG, so they render on GitHub without external requests.
