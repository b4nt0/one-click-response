# Installing 1CR

This guide walks through deploying One-click Response (1CR) to your own Firebase project: backend (Cloud Functions + Firestore), frontend (Firebase Hosting), and the Gmail add-on (Apps Script).

## Prerequisites

- A [Google Cloud](https://console.cloud.google.com/) / [Firebase](https://console.firebase.google.com/) account with billing enabled (Cloud Functions require the Blaze plan)
- [Node.js](https://nodejs.org/) 20+ (for Firebase CLI and clasp)
- [Python](https://www.python.org/) 3.13+
- [Git](https://git-scm.com/)
- A Google Cloud OAuth client for web sign-in and Gmail API access

## Overview

| Component    | Technology                         | Deployed via                       |
|--------------|------------------------------------|------------------------------------|
| Backend API  | Python Cloud Functions (2nd gen)   | `firebase deploy --only functions` |
| Database     | Firestore                          | `firebase deploy --only firestore` |
| Frontend     | Static HTML/JS on Firebase Hosting | `firebase deploy --only hosting`   |
| Gmail add-on | Google Apps Script                 | `clasp push`                       |

All three surfaces share one Firebase Hosting URL. API requests to `/api/**` are routed to the Cloud Function; static pages are served from `web/public/`.

---

## 1. Create a Firebase project

1. Open the [Firebase console](https://console.firebase.google.com/) and click **Add project**.
2. Choose a project ID (e.g. `my-1cr-app`). This ID is used throughout configuration.
3. Upgrade the project to the **Blaze (pay as you go)** plan — required for Cloud Functions.
4. In the project, enable:
   - **Authentication** → Sign-in method → **Google** (enable)
   - **Firestore Database** → Create database (start in production mode; rules are deployed from this repo). Note the **location** you choose (e.g. `nam5` multi-region, or `europe-west1`).
   - **Hosting** (enable when prompted during first deploy)

[`firebase.json`](../../firebase.json) must declare the Firestore database name and location. The default config uses `"database": "(default)"` and `"location": "nam5"`. If you created Firestore in a different region, update `location` to match (see [Firestore locations](https://firebase.google.com/docs/firestore/locations)).

### Link the local repo to your project

Edit [`.firebaserc`](../../.firebaserc) and replace the default project ID:

```json
{
  "projects": {
    "default": "my-1cr-app"
  }
}
```

Or set it from the CLI:

```bash
firebase use --add
```

### Install Firebase CLI

```bash
npm install -g firebase-tools
firebase login
```

---

## 2. Configure Google OAuth and Gmail API

### Firebase’s auto-created OAuth client (sign-in)

When you enable **Google** under **Authentication** → **Sign-in method**, Firebase automatically creates an OAuth 2.0 web client in the linked Google Cloud project. You will see it in [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials** as something like **Web client (auto created by Google Service)**.

That client is **already connected to Firebase Authentication**. You do not paste its secret into this repository. Firebase keeps the secret on Google’s side and uses it during the sign-in flow. Your frontend only needs the Firebase web app config in [`web/public/js/config.js`](../../web/public/js/config.js) (`apiKey`, `projectId`, etc.) — see [Finding your web app config](#finding-your-web-app-config) below. You do **not** need the OAuth client secret for the frontend.

The **Web client ID** is visible in Firebase console → **Authentication** → **Sign-in method** → **Google** (expand the provider). The original **client secret** for auto-created clients is not viewable after creation — that is expected.

**For sign-in alone**, you can stop here: enable Google in Firebase Auth, set `config.js`, and add your hosting domains under **Authentication** → **Settings** → **Authorized domains**.

### When you also need the client secret (Gmail forwarding)

The backend uses `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN` (Cloud Functions secrets) to send answer-forwarding notifications **from the application** to each account owner. End users never grant Gmail send permission — only the application operator configures a dedicated sender account.

You have two options for the OAuth client:

#### Option A — New secret on the existing auto-created client (simplest)

1. In Google Cloud Console → **Credentials**, open **Web client (auto created by Google Service)**.
2. Click **Add secret** (or create a new client secret). **Copy the new secret immediately** — Google only shows it once.
3. Note the **Client ID** shown on the same page.
4. In Firebase console → **Authentication** → **Sign-in method** → **Google**, open the provider and ensure the **Web client ID** matches that Client ID. If you ever replaced the default, paste the same Client ID and the **new** secret here.
5. Store the same values as Cloud Functions secrets (see [Deploy the backend](#3-deploy-the-backend)):
   - `GMAIL_CLIENT_ID` = that Client ID
   - `GMAIL_CLIENT_SECRET` = the new secret you just created

#### Option B — Separate OAuth web application

Create a dedicated **Web application** client if you prefer not to touch the auto-created one:

1. Enable **Gmail API** under **APIs & Services** → **Library**.
2. **Credentials** → **Create credentials** → **OAuth client ID** → **Web application**.
3. Add authorized JavaScript origins:
   - `https://my-1cr-app.web.app`
   - `https://my-1cr-app.firebaseapp.com`
   - `http://localhost:5000` (local emulator hosting)
4. Add authorized redirect URIs from Firebase Auth (e.g. `https://my-1cr-app.firebaseapp.com/__/auth/handler`).
5. Copy the new **Client ID** and **Client secret**.
6. In Firebase → **Authentication** → **Google**, set **Web client ID** and **Web client secret** to those values (replacing the default).
7. Set the same ID and secret as `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in Cloud Functions.

### Application sender account

Forwarding notifications are sent **from** a Gmail account you control (the application owner) **to** the signed-in user's email. Obtain a long-lived refresh token for that sender account once:

1. Create or choose a Gmail account to send notifications (e.g. `notifications@yourdomain.com`).
2. Complete a one-time OAuth consent flow with `https://www.googleapis.com/auth/gmail.send` for that account, using the same OAuth client as above (see below).
3. Store the refresh token as the `GMAIL_REFRESH_TOKEN` secret and set `GMAIL_SENDER_EMAIL` to that account's address:

   ```bash
   firebase functions:secrets:set GMAIL_REFRESH_TOKEN
   firebase functions:secrets:set GMAIL_SENDER_EMAIL
   ```

Users signing in via the web settings page only need standard Google sign-in — no Gmail scopes.

#### Obtain the refresh token (OAuth 2.0 Playground)

The easiest way to get a refresh token is [Google's OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).

**Before you start:**

- **Gmail API** is enabled in your Google Cloud project (see Option B above if you have not done this yet).
- You have your OAuth **Client ID** and **Client secret** (the same values you set as `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET`).
- On that OAuth client, add this **Authorized redirect URI**:
  - `https://developers.google.com/oauthplayground`
- On the **OAuth consent screen**, add your sender Gmail address as a **Test user** if the app is still in *Testing* mode.

**Steps:**

1. Open [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
2. Click the **gear icon** (top right) and check **Use your own OAuth credentials**.
3. Paste your **Client ID** and **Client secret**, then close the settings panel.
4. In **Step 1 — Select & authorize APIs**, enter this scope in the input box at the bottom:

   ```
   https://www.googleapis.com/auth/gmail.send
   ```

   Click **Authorize APIs**.
5. Sign in with the **sender account** (e.g. `notifications@yourdomain.com`) — not your personal admin account unless that is the sender.
6. Approve the permission request.
7. In **Step 2 — Exchange authorization code for tokens**, click **Exchange authorization code for tokens**.
8. Copy the **`refresh_token`** value from the response (not the `access_token`).

**Notes:**

- If no `refresh_token` appears, revoke the app's access at [Google Account → Third-party access](https://myaccount.google.com/permissions) and repeat the flow. Signing in fresh after revoke usually fixes a missing refresh token.
- While the OAuth app is in **Testing** mode, refresh tokens can expire after 7 days unless the sender account is a test user or you publish the consent screen. For production, publish the consent screen or keep the sender on the test-user list.
- The refresh token is tied to the OAuth client ID — use the same client you configured as `GMAIL_CLIENT_ID`.

**Verify (optional):** After deploying, trigger a response with `forward_answers` enabled. You should receive a notification **from** `GMAIL_SENDER_EMAIL` **to** the campaign owner's address.

### Summary

| Goal | What you need |
|---|---|
| Web sign-in only | Firebase `config.js` + Google enabled in Auth (auto client is enough) |
| Answer forwarding | OAuth client ID + secret + application sender refresh token in Cloud Functions secrets |

### Finding your web app config

These values are **not** in Google Cloud Console. They are in the **Firebase** console:

1. Open [Firebase console](https://console.firebase.google.com/) and select your project.
2. In the left sidebar, next to **Project Overview** at the top, click the **gear icon** → **Project settings**.
   - Direct pattern: `https://console.firebase.google.com/project/<your-project-id>/settings/general`
3. Stay on the **General** tab.
4. Scroll down to the **Your apps** section.
5. If you see a **Web** app (`</>` icon), click it — the **Firebase SDK snippet** shows `apiKey`, `authDomain`, `projectId`, and the rest.
6. If there is no web app yet, click **Add app** → choose **Web** (`</>`) → register the app (nickname is enough) → copy the `firebaseConfig` object.

Paste those values into [`web/public/js/config.js`](../../web/public/js/config.js).

---

## 3. Deploy the backend

The backend lives in [`functions/`](../../functions/) and is a single Python HTTPS function (`api`) that handles all `/api/**` routes.

### Python environment

Firebase deploy requires a virtual environment at `functions/venv/` built with **Python 3.13** (matching `runtime: python313` in `firebase.json`). The Firebase CLI looks for `firebase-functions` in that venv.

From the repository root:

```bash
./scripts/setup-local.sh
```

This creates (or recreates) `functions/venv/` with `python3.13` and installs dependencies. If the venv was built with a different Python version, the setup script removes it and rebuilds automatically.

You can point to a specific interpreter:

```bash
PYTHON_BIN=/opt/homebrew/bin/python3.13 ./scripts/setup-local.sh
```

### Secrets and environment variables

Set Cloud Functions secrets before deploying:

```bash
# Gmail OAuth credentials (application sender for forwarding notifications)
firebase functions:secrets:set GMAIL_CLIENT_ID
firebase functions:secrets:set GMAIL_CLIENT_SECRET
firebase functions:secrets:set GMAIL_REFRESH_TOKEN
firebase functions:secrets:set GMAIL_SENDER_EMAIL
```

Set the public hosting URL so encrypted response links point to your deployment. The backend reads `HOST_URL` from the environment (see [`functions/src/config.py`](../../functions/src/config.py)). It is declared as a **parameter** (not a secret) in [`functions/main.py`](../../functions/main.py).

> **Note:** Listing campaigns does **not** use `HOST_URL` — only `/api/links` when inserting response buttons. A missing or empty `HOST_URL` breaks recipient links even when the add-on works. The Gmail add-on also sends `host_url` from its `API_BASE_URL` script property; the backend uses that (or the request Host header) before falling back to `HOST_URL`.

Create `functions/.env` before deploy, or let `firebase deploy` prompt you and write `functions/.env.<project_id>`:

```bash
# functions/.env — loaded automatically on deploy
HOST_URL=https://my-1cr-app.web.app
```

You can also set it in the Google Cloud Console under **Cloud Functions** → **api** → **Edit** → **Runtime environment variables**.

### Deploy Firestore rules, indexes, and functions

```bash
export FIREBASE_PROJECT_ID=my-1cr-app   # optional; uses .firebaserc default otherwise
./scripts/deploy.sh
```

`deploy.sh` runs unit tests, then deploys:

- `firestore.rules` and `firestore.indexes.json`
- Cloud Functions (`functions/`)
- Firebase Hosting (`web/public/`)

To deploy only the backend:

```bash
firebase deploy --only firestore:rules,firestore:indexes,functions
```

### Verify the backend

After deploy, check the health endpoint (via Hosting rewrite):

```bash
curl https://my-1cr-app.web.app/api/health
# {"status":"ok"}
```

---

## 4. Deploy the frontend

The frontend is static HTML/CSS/JS in [`web/public/`](../../web/public/). It is deployed automatically with Hosting when you run `./scripts/deploy.sh`.

### Configure Firebase for the web client

Edit [`web/public/js/config.js`](../../web/public/js/config.js) with your project's web app config ([Finding your web app config](#finding-your-web-app-config)):

```javascript
window.FIREBASE_CONFIG = {
  apiKey: "...",
  authDomain: "my-1cr-app.firebaseapp.com",
  projectId: "my-1cr-app",
  storageBucket: "my-1cr-app.appspot.com",
  messagingSenderId: "...",
  appId: "...",
};
```

If you have not added a web app yet, follow step 6 in [Finding your web app config](#finding-your-web-app-config).

### Deploy hosting only

```bash
firebase deploy --only hosting
```

### Pages served

| URL                        | Purpose |
|----------------------------|---------|
| `/settings/`               | Sign in, link to campaigns and profile |
| `/settings/campaigns.html` | Campaign and response-button management |
| `/settings/profile.html`   | Account info and encryption key rotation |
| `/r/`                      | Response confirmation page (opened from email buttons) |

Hosting rewrites in [`firebase.json`](../../firebase.json) route `/api/**` to the Cloud Function and serve the response/settings pages.

---

## 5. Deploy the Gmail add-on

The add-on is a Google Apps Script project in [`gmail-addon/`](../../gmail-addon/).

### Install clasp

```bash
npm install -g @google/clasp
clasp login
```

> **clasp 3.x:** Several commands were renamed from clasp 2.x. Use `clasp open-script` (not `clasp open`), `clasp create-script` (not `clasp create`), etc. Run `clasp --help` to list commands.

### Create the Apps Script project

**Option A — link via the Apps Script console (recommended):**

1. Create a new **standalone** project at [script.google.com](https://script.google.com/).
2. Open **Project settings** and copy the **Script ID**.
3. Set it in [`gmail-addon/.clasp.json`](../../gmail-addon/.clasp.json):

```json
{
  "scriptId": "YOUR_SCRIPT_ID",
  "rootDir": "."
}
```

4. Push the local add-on code:

```bash
cd gmail-addon
clasp push
```

**Option B — create via clasp (empty directory only):**

Only use this if you are **not** starting from this repo’s `gmail-addon/` files (clasp will refuse to run if `.clasp.json` already exists):

```bash
mkdir my-1cr-addon && cd my-1cr-addon
clasp create-script --type standalone --title "One-click Response"
```

Then copy in `appsscript.json` and `Code.gs` from this repository’s `gmail-addon/` folder and run `clasp push`.

### Configure the add-on

1. Push the code:

   ```bash
   ./scripts/deploy-addon.sh
   ```

2. Open the project in the Apps Script editor:

   ```bash
   cd gmail-addon
   clasp open-script
   ```

3. Set **Script properties** (Project settings → Script properties):

   | Property       | Value                        |
   |----------------|------------------------------|
   | `API_BASE_URL` | `https://my-1cr-app.web.app` |

   Also update [`gmail-addon/appsscript.json`](../../gmail-addon/appsscript.json): `urlFetchWhitelist` and `addOns.common.openLinkUrlPrefixes` must list your hosting URL with a **trailing slash** (e.g. `https://my-1cr-app.web.app/`).

4. In the Apps Script editor, deploy as a **Gmail add-on**:
   - **Deploy** → **Test deployments** (for testing) or **Deploy** → **New deployment** → type **Add-on**.
   - Complete the [Gmail add-on SDK review checklist](https://developers.google.com/workspace/add-ons/gmail/authorize) for production.

5. **Link the add-on to your backend** (one-time, operator only — see [Link add-on to backend](#link-add-on-to-backend-one-time-operator-step) below).

### Link add-on to backend (one-time, operator step)

End users **never** configure `APPS_SCRIPT_OAUTH_CLIENT_ID`. You set it once when you deploy the stack, before anyone uses the Gmail add-on.

#### Where the value comes from

Google creates an OAuth 2.0 client automatically for **your** Apps Script project when it is linked to a Google Cloud project. Every call to `ScriptApp.getIdentityToken()` in that add-on embeds that client's ID in the token's `aud` (audience) field.

Your backend must know that ID so it can verify tokens are from **your** add-on, not from another script or a forged request.

| Deployment model | Who sets `APPS_SCRIPT_OAUTH_CLIENT_ID` | How many values |
|---|---|---|
| **You self-host** (this repo) | You, the operator, during install | One per Apps Script project you create |
| **Marketplace / shared add-on** | The publisher, once | One for all users of that published add-on |

If you create a **new** Apps Script project (new Script ID), Google creates a **new** OAuth client → you must update the backend secret to match.

#### Setup steps (do this once after `clasp push`)

1. In the Apps Script editor (**Project settings**), confirm the script is linked to the **same GCP project** as Firebase (click the project number if you need to change it).

2. Create a **test deployment** of the Gmail add-on if you have not already (**Deploy** → **Test deployments**).

3. In the editor, select **`logOAuthClientId`** in the function dropdown and click **Run**. Approve scopes if prompted.

4. Open **Executions** (left sidebar) and copy the logged client ID (`…apps.googleusercontent.com`).

5. Set it as a Cloud Functions secret and redeploy the backend:

   ```bash
   firebase functions:secrets:set APPS_SCRIPT_OAUTH_CLIENT_ID
   ./scripts/deploy.sh
   ```

6. Verify: open the add-on in Gmail compose — campaigns should load (after **Connect to backend** if prompted for external requests).

> **Do not** pick a client ID from GCP Console → Credentials unless you are certain it belongs to **this** Apps Script project. The console lists many OAuth clients (Firebase web, Gmail forwarding, etc.). The `logOAuthClientId()` output is authoritative for your add-on.

#### Why this is not configured in the add-on

The add-on only **sends** the token. The backend **validates** it before returning your Firestore data. Putting the client ID in the add-on would not help — an attacker could skip the add-on and call your API directly. The secret tells the server which `aud` to expect when verifying Google's signature.

### Using the add-on in Gmail

The add-on has two surfaces:

| Where | When it appears | What it does |
|---|---|---|
| **Right sidebar** | Reading any email | Shows a short hint — open compose to insert buttons |
| **Compose window** | Writing a new email or reply | Full UI to pick a campaign and insert response buttons |

**To insert response buttons:**

1. Click **Compose** (new email or reply).
2. Add at least one **To** recipient (required before insert).
3. In the **compose window** (not the inbox sidebar), click the **One-click Response** icon in the toolbar at the **bottom** of the draft. It uses the logo from `appsscript.json` and may appear next to the send button or under a “More” menu depending on your Gmail layout.
4. Select **Add response buttons** if prompted, then use the card to choose a campaign and insert the block.

If you only see the sidebar while reading mail, that is expected — the insert UI is compose-only.

### Authorize external requests (first use)

The add-on calls your backend with `UrlFetchApp`, which requires the `script.external_request` scope. Gmail does **not** grant that scope at install time.

1. Open compose and click the **One-click Response** icon.
2. Click **Connect to backend** — Gmail opens Google's authorization page in a new window.
3. Approve **Connect to an external service**. The add-on reloads automatically when you return.
4. Campaigns should appear in the card.

Authorization is only requested when **you** click that button in compose. It is never triggered for email recipients opening a message.

Re-installing the test deployment alone does not replace this step.

### Publish to your workspace

For personal or workspace use:

- Use **Test deployments** and install via the Gmail add-on test install link, or
- Publish through the [Google Workspace Marketplace](https://developers.google.com/workspace/marketplace) for broader distribution.

### Add-on auth note

See [Link add-on to backend](#link-add-on-to-backend-one-time-operator-step) for the full one-time setup. Summary:

| Client | What it sends | What the backend does |
|---|---|---|
| Web settings | Firebase ID token (from Google sign-in in the browser) | Verifies with Firebase Auth |
| Gmail add-on | Google OIDC token from `ScriptApp.getIdentityToken()` | Verifies Google's signature and checks the token's `aud` claim |

The add-on and web settings use different token types. Signing in on the web does not authenticate the Gmail add-on. Use the same Google account in both.

**Operator checklist (not shown to end users):**

1. Run `logOAuthClientId()` in the Apps Script editor after the first test deployment.
2. Set `APPS_SCRIPT_OAUTH_CLIENT_ID` to the logged `aud` value.
3. Redeploy functions (`./scripts/deploy.sh`).

The helper function lives in [`gmail-addon/Code.gs`](../../gmail-addon/Code.gs). Error-card debug output is for troubleshooting only — normal install uses the steps above.

---

## 6. Post-install checklist

- [ ] `curl https://<project>.web.app/api/health` returns `{"status":"ok"}`
- [ ] Sign in at `https://<project>.web.app/settings/` with Google
- [ ] Create a campaign with response buttons in settings
- [ ] Gmail add-on `API_BASE_URL` points to your hosting URL
- [ ] `HOST_URL` set in `functions/.env` (e.g. `https://<project>.web.app`) and functions redeployed
- [ ] `APPS_SCRIPT_OAUTH_CLIENT_ID` set from `logOAuthClientId()` and functions redeployed
- [ ] Insert a response block in a Gmail compose window (recipients required)
- [ ] Click a response button and confirm on `/r/` — answer is recorded or forwarded per campaign rules

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `401` on API calls from settings | Firebase config in `config.js` does not match project; user not signed in |
| Functions deploy: "Failed to find location of Firebase Functions SDK" | Venv was created with wrong Python version. Run `./scripts/setup-local.sh` (uses Python 3.13), then redeploy |
| `Firestore database configuration is missing in firebase.json` | Add `database` and `location` under `firestore` in `firebase.json` (included in this repo; set `location` to your Firestore region) |
| Response links point to `localhost` | `HOST_URL` not set for Cloud Functions — add to `functions/.env` and redeploy |
| Response links are `http:///r/?p=…` (no hostname) | `HOST_URL` is empty or invalid (e.g. `http://` only). Set `HOST_URL=https://<project>.web.app` in `functions/.env`, then `./scripts/deploy.sh` |
| Gmail forwarding fails | `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, or `GMAIL_SENDER_EMAIL` secrets missing or invalid |
| Add-on: `UrlFetchApp.fetch` permission denied | Click **Connect to backend** in the compose add-on card; see [Authorize external requests](#authorize-external-requests-first-use) |
| Add-on: OAuth prompt shown to email recipient | Fixed in current add-on code — remove `authorizationCheckFunction`, redeploy with `clasp push`; auth only runs from compose **Connect to backend** |
| Add-on: `invalid_scope` / `gmail.addons.current.message.compose` | That scope does not exist — compose needs `gmail.addons.current.action.compose`. Run `clasp push`, create a **new** test deployment, reinstall. In Apps Script editor → Project settings → Scopes, verify scopes match `appsscript.json` |
| Add-on: "Could not load campaigns" (HTTP 401 / unauthorized) | Open compose add-on — the card now shows an **Auth debug** block with token `aud`, backend secret fingerprint, and per-audience verification errors. Compare token `aud` to `APPS_SCRIPT_OAUTH_CLIENT_ID` (must match exactly). Also call `POST /api/auth/inspect` with the same Bearer token, or check Cloud Functions logs |
| `clasp open`: Unknown command | clasp 3.x renamed this to `clasp open-script` |
| URL does not match prefixes whitelisted | Set `addOns.common.openLinkUrlPrefixes` and `urlFetchWhitelist` in `appsscript.json` to your full hosting URL with trailing slash (not `https://` alone); redeploy test deployment |
| `clasp push`: **The caller does not have permission** | Enable Apps Script API at [script.google.com/home/usersettings](https://script.google.com/home/usersettings) and in Google Cloud Console; run `clasp logout` then `clasp login`; verify Script ID in `.clasp.json` belongs to your account |
| Firestore permission denied from client | Expected for `responses` and `deduplication` — only Cloud Functions write those collections |

For local development and testing, see [Development](../development/README.md).
