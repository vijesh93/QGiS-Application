# Deploying the licensed/restricted BW assets (fonts + logo) to production

## Context

This app uses two kinds of assets that cannot be committed to this repo's
git history because the repo is **public**:

- **BaWue Sans / BaWue Serif webfonts** — licensed from Luzi Type under a
  commercial, metered web-font license (usable "for the overall number of
  monthly page views stated on your Purchase Receipt" — see the license
  note in `frontend/src/styles/index.css`). Redistributing the font files
  via a public repo would mean handing that paid license to anyone who
  clones it.
- **The official BW logo** (`BaWue_Logo_Flag_rgb.svg`) — pulled from the
  login-gated design.landbw.de portal. Official state corporate-design
  assets are restricted/controlled; they don't belong in a public repo
  either.

Both are listed in `.gitignore`:
```
frontend/public/fonts/
frontend/public/BaWue_Logo_Flag_rgb.svg
```

**The practical consequence**: a normal `git clone` / `git pull` on the
server will *never* bring these files in. They must be transferred to the
server separately, every single time the server's checkout needs them —
not just once. That includes: the first deploy, any time the server is
rebuilt from a clean clone, any time you migrate to a different server, or
if these files are ever accidentally deleted on the server.

This doc is the repeatable procedure for that transfer. It assumes you
still have the original font/logo files on your own machine (ideally also
kept in a secure, access-controlled location outside of GitHub — e.g. your
organization's Nextcloud — so you don't have to re-source them from
scratch each time).

---

## What needs to be transferred (17 files total)

```
frontend/public/BaWue_Logo_Flag_rgb.svg

frontend/public/fonts/
├── BaWueSansWeb-Regular.woff
├── BaWueSansWeb-Regular.woff2
├── BaWueSansWeb-RegularItalic.woff
├── BaWueSansWeb-RegularItalic.woff2
├── BaWueSansWeb-SemiBold.woff
├── BaWueSansWeb-SemiBold.woff2
├── BaWueSansWeb-SemiBoldItalic.woff
├── BaWueSansWeb-SemiBoldItalic.woff2
├── BaWueSansWeb-Bold.woff
├── BaWueSansWeb-Bold.woff2
├── BaWueSansWeb-BoldItalic.woff
├── BaWueSansWeb-BoldItalic.woff2
├── BaWueSerifWeb-Regular.woff
├── BaWueSerifWeb-Regular.woff2
├── BaWueSerifWeb-Bold.woff
└── BaWueSerifWeb-Bold.woff2
```

## When this must happen in the deploy sequence

These files must be in place under `frontend/public/` on the server
**before** the `gateway` image is built (`docker compose build gateway` /
`up --build`). The gateway's `nginx/Dockerfile` does a multi-stage build
that `COPY`s `frontend/` in and runs `npm run build` — Vite copies
everything under `frontend/public/` into the built `dist/` output at that
exact point. If the font/logo files aren't there yet when you build, the
build still succeeds with no error or warning — it just silently produces
an image without them.

That failure mode is easy to miss, because this app's gateway nginx config
uses an SPA fallback (`try_files $uri $uri/ /index.html;`). A request for a
missing font file doesn't 404 — it silently serves `index.html` instead,
with a `200 OK` status. Always verify with the `Content-Type` check in
Step 5, not just "did it return 200".

---

## Step-by-step

### Step 1 — package the files locally

Run this from `frontend/public/` on your own machine, so the archive keeps
the right relative structure (`fonts/` as a subfolder, the logo at the top
level):

```bash
cd frontend/public
zip -r bawue-assets.zip BaWue_Logo_Flag_rgb.svg fonts/
```

### Step 2 — upload to your organization's cloud storage and share it

Upload `bawue-assets.zip` to your org's Nextcloud (or equivalent) and
create a share link. Because this is genuinely restricted/licensed
content — not just a convenience shortcut — treat it more carefully than a
throwaway text file:

- **Set a password** on the share.
- **Set a short expiration** (e.g. same day), so it doesn't linger.
- Plan to delete the share immediately after Step 3 succeeds (Step 5).

### Step 3 — download and extract on the server

On the server, in the app's own `frontend/public/` directory:

```bash
cd ~/apps/qgis-app/frontend/public
curl -u 'SHARE_TOKEN' -L -o bawue-assets.zip 'https://<your-cloud-domain>/index.php/s/SHARE_TOKEN/download'
# enter the share password when curl prompts for it
unzip bawue-assets.zip
rm bawue-assets.zip
ls -la BaWue_Logo_Flag_rgb.svg fonts/
```

Replace `SHARE_TOKEN` and `<your-cloud-domain>` with what Step 2 actually
gave you — the share token is the part of the URL after `/s/`. (This is
the same password-protected-share + `curl -u` technique used earlier for
transferring other files to this server — see `deployment-report.txt` if
you want the original worked example.)

The final `ls -la` should show the logo file and a `fonts/` directory with
16 files in it. If `unzip` complains the archive is missing or corrupt,
the download didn't actually succeed — check `file bawue-assets.zip`
before unzipping; if it reports `HTML document` instead of `Zip archive
data`, the share link/password was wrong and you downloaded an error page
instead.

### Step 4 — rebuild the gateway image

Only `gateway` needs rebuilding — these are frontend-only static assets,
`backend` is untouched:

```bash
cd ~/apps/qgis-app
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d gateway
```

### Step 5 — verify, then delete the cloud share

```bash
curl -sI https://<your-app-domain>/BaWue_Logo_Flag_rgb.svg | grep -i content-type
curl -sI https://<your-app-domain>/fonts/BaWueSansWeb-Regular.woff2 | grep -i content-type
```

Expect `image/svg+xml` and `font/woff2` respectively. **If either comes
back `text/html` instead, the files aren't actually in the built image**
— that's the SPA-fallback trap described above; go back and confirm
Step 3 actually placed the files before Step 4's build ran, then rebuild
again.

Once confirmed, go delete the Nextcloud share link from Step 2 — it's
served its purpose and these are restricted-license files, no reason to
leave a public download link sitting around.

---

## Keeping this in sync going forward

If the fonts or logo ever change (a new weight, an updated logo file,
etc.), repeat Steps 1–5 with the new files. There's no automation for
this on purpose — it's a deliberately manual, infrequent step, kept
separate from the normal `git pull` + rebuild flow precisely so these
restricted assets never flow through git.
