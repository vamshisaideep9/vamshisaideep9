# Setup — about 15 minutes

## 1. Create the special profile repo
GitHub shows a repo's README on your profile when the repo **has the same name as your username**.

1. Go to <https://github.com/new>
2. Repository name: **`vamshisaideep9`** · Public · tick *Add a README*
3. Upload everything in this folder (keep the folder structure: `assets/`, `scripts/`, `.github/`).

> Tip: the easiest upload is `git clone`, copy the files in, then `git add -A && git commit -m "profile" && git push`.
> GitHub's web uploader skips hidden folders like `.github/`.

## 2. Turn on the automations
1. Repo → **Settings → Actions → General → Workflow permissions** → choose **Read and write permissions** → Save.
2. Repo → **Actions** tab → run each workflow once with **Run workflow**:
   - *Contribution snake* — creates the `output` branch with the snake SVGs
   - *3D contribution graph* — creates `profile-3d-contrib/`
   - *Live feeds* — fills the recent-activity list
3. Optional blog feed: **Settings → Secrets and variables → Actions → Variables → New variable**
   `BLOG_FEEDS` = comma-separated RSS URLs (Medium: `https://medium.com/feed/@you`, dev.to: `https://dev.to/feed/you`).

After that, everything refreshes by itself (snake + 3D daily, feeds every 6 hours).

## 3. Fill in your links
Search the README for `YOUR-` and replace: LinkedIn, email, portfolio, résumé, booking link (cal.com or Calendly).

## 4. Change any text or project
Edit **`profile.config.json`** (name, title, roles, terminal lines, services, project cards) and commit.
The *Rebuild profile visuals* workflow regenerates every SVG automatically.
To add a project card: add an entry to `projects`, then add its `<img src="assets/project-<slug>.svg">` cell in the README table.

## 5. Add demo GIFs (big win for clients)
Record 10–15 second clips of your best apps (ScreenToGif on Windows, Kap on Mac, or a phone screen recording for Android).
Keep each under ~5 MB (800px wide, 15 fps). Put them in `assets/demos/` and uncomment the demo block in the README.

## 6. Polish the profile itself (settings → Public profile)
- **Name:** Vamshi Sai Deep
- **Bio (160 chars):** `AI & Full-Stack Engineer · Advanced RAG, LLM agents · FastAPI + Next.js · Android (Kotlin/RN) · SEO · Open to roles & freelance`
- **Company / Location / Website / Social links:** fill all four — recruiters filter on them.
- **Status:** "🚀 Open to work" with *Busy* off.
- **Pin 6 repos** (Profile → Customize your pins): your strongest AI, full-stack, Android and SEO projects.

## 7. Clean up the 71 repos (recruiters do click through)
- Give every pinned or featured repo a one-line description, topics, a live link, a screenshot or GIF, and a short README.
- Archive tutorial/practice repos (Settings → Archive) or make them private.
- Mark forks clearly; don't pin forks.

## Stats cards note
The stats/streak cards use free public services that are occasionally rate-limited. If a card shows an error,
self-host github-readme-stats on Vercel (one click from its repo) and swap the domain in the README.

## Make your contribution numbers reflect reality
Most of your work happens in org/client repos. Turn on **Settings → Public profile → Contributions & activity →
"Include private contributions on my profile"** so the graph, streak, snake and 3D chart count it (no code is exposed).

## 8. Include private & organisation repos in your stats (optional)
Free public stat services can only see public repos. This workflow uses your own token so stats include private
and org work — publishing **only totals and language percentages, never code**.

1. Create a token: GitHub → Settings → Developer settings → **Personal access tokens → Tokens (classic)** →
   scopes **`repo`** and **`read:org`** (and `read:user`). Set an expiry and renew it when it lapses.
   For SSO-protected orgs, click *Configure SSO → Authorize* next to the token.
2. In the profile repo: **Settings → Secrets and variables → Actions → New repository secret** →
   name `METRICS_TOKEN`, paste the token. Never put it in a file.
3. Actions → *Rebuild profile visuals* → **Run workflow**. It refreshes `stats.json` and `assets/stats.svg`,
   then repeats daily.

Client confidentiality: `scripts/fetch_stats.py` stores counts and language percentages only. Repo names, code
and commit messages are never written.
