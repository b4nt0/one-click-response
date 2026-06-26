# Gmail add-on

Apps Script add-on for inserting one-click response button blocks into Gmail compose.

## Setup

1. Install [clasp](https://github.com/google/clasp): `npm install -g @google/clasp`
2. Login: `clasp login`
3. Create a **standalone** Apps Script project at [script.google.com](https://script.google.com/) and set its Script ID in `.clasp.json`
4. Set Script Properties in the Apps Script console:
   - `API_BASE_URL` — your Firebase Hosting URL (e.g. `https://one-click-response.web.app`)

Gmail add-on behavior is defined in `appsscript.json` (the `gmail` block).

Open the online editor with `clasp open-script` (clasp 3.x; older docs use `clasp open`).

## Auth

The add-on sends `ScriptApp.getIdentityToken()` as a Bearer token. The backend accepts this **or** a Firebase ID token (web settings). You must sign in at `/settings/` once with the same Google account; the backend maps add-on identity tokens to Firebase users by email.

Set Cloud Functions secret `APPS_SCRIPT_OAUTH_CLIENT_ID` once during install — run `logOAuthClientId()` in the Apps Script editor and copy the logged `aud` value. End users never configure this. See [INSTALL.md § Link add-on to backend](../docs/installing/INSTALL.md#link-add-on-to-backend-one-time-operator-step).

## Deploy

```bash
./scripts/deploy-addon.sh
```

## Manual testing

See [TESTING.md](./TESTING.md).
