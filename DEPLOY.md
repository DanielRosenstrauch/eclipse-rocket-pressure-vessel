# Deploying to GitHub + Streamlit Community Cloud

End-to-end checklist to take this from a folder on your laptop to a live URL.
Plain copy-paste commands; no prior GitHub experience required.

## 1. One-time setup (skip if already done)

1. Create a GitHub account at <https://github.com>.
2. Install git: <https://git-scm.com/downloads> (on macOS this comes with
   Xcode Command Line Tools — running `git --version` in Terminal will
   prompt you to install it if it's missing).
3. Configure your identity (replace with your info):
   ```bash
   git config --global user.name  "Daniel Rosenstrauch"
   git config --global user.email "dr83@rice.edu"
   ```

## 2. Create the GitHub repo

1. Go to <https://github.com/new>.
2. Repository name: `eclipse-rocket-pressure-vessel`
3. Visibility: **Public** (Streamlit Community Cloud requires it; this is what
   you want for a portfolio piece anyway).
4. Do **not** check any of "Add a README", "Add .gitignore", or "Choose a
   license" — we already have those in the folder.
5. Click **Create repository**. Leave that page open; you'll need the URL.

## 3. Push this folder to GitHub

From the project folder in Terminal (`cd ~/Documents/MATLAB/MECH/eclipse-rocket-pressure-vessel`):

```bash
git init
git add .
git commit -m "Initial commit: Python + Streamlit port of MECH 315 final project"
git branch -M main
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/eclipse-rocket-pressure-vessel.git
git push -u origin main
```

If the push prompts for credentials, GitHub now requires a **Personal Access
Token** instead of your password — see
<https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>.

Refresh the GitHub repo page; you should see all the files.

## 4. Deploy to Streamlit Community Cloud (free)

1. Go to <https://share.streamlit.io> and sign in with your GitHub account.
2. Click **New app** (or **Create app**).
3. Select:
   - **Repository:** `<your-github-username>/eclipse-rocket-pressure-vessel`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (Optional) **App URL:** customize the subdomain, e.g. `eclipse-rocket.streamlit.app`.
5. Click **Deploy**. First build takes 1–2 minutes while it pulls
   `requirements.txt` and installs everything.

When it's live, copy the URL.

## 5. Add the live URL to the README

In `README.md` near the top, replace the `add Streamlit Community Cloud URL`
placeholder with your real URL, then push the change:

```bash
git add README.md
git commit -m "Add live demo URL"
git push
```

## 6. Polish (recommended for portfolio)

These are small but pay off if a recruiter / YC reviewer skims the repo:

1. **About + topics on GitHub:** open the repo on github.com, click the gear
   icon next to "About" (top right of the repo page), and:
   - Description: *Interactive Streamlit web demo of a thick-walled pressure
     vessel optimizer for a 30,000 ft hybrid rocket — Python port of my MECH
     315 final project at Rice.*
   - Website: paste your Streamlit Cloud URL
   - Topics: `streamlit`, `engineering`, `optimization`, `rocketry`,
     `pressure-vessel`, `python`, `matlab-translation`
   - Check **Use your GitHub Pages website** off, but **Releases** and
     **Packages** can stay off too.
2. **Pin the repo to your profile:** on your GitHub profile, click
   *Customize your pins* and pin this repo so it shows up at the top.
3. **Add a screenshot to the README:** open the deployed app, take a
   screenshot of the main page, save it as `docs/screenshot.png`, then add
   `![Screenshot](docs/screenshot.png)` near the top of the README. Push.

## Troubleshooting

- **`pytest` errors locally:** make sure you ran `pip install -r requirements.txt`
  inside an activated virtualenv. The tests need `numpy`, `scipy`, `pytest`.
- **Streamlit Cloud says "Module not found":** your `requirements.txt` is
  probably out of sync with what `app.py` imports. Streamlit Cloud installs
  exactly what's listed in that file.
- **Optimization seems slow on Cloud:** the default grid is 256,000 points
  per combination. The free Streamlit Cloud tier has ~1 GB RAM and 1 CPU —
  still plenty fast (well under a second per run). If you ever push the
  grid sliders above ~120 each, memory might get tight; that's just a quirk
  of the free tier, not a code issue.
