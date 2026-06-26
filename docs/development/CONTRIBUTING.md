# Development guide

This guide covers setting up a local development environment and running tests for 1CR.

## Prerequisites

Install these tools on your machine:

| Tool | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/) | **3.13** (must match Cloud Functions runtime; `python3.13` on PATH) |
| [Node.js](https://nodejs.org/) | 20+ | Firebase CLI, clasp (add-on) |
| [Firebase CLI](https://firebase.google.com/docs/cli) | latest | Emulators and deploy |
| [Git](https://git-scm.com/) | any | Clone the repository |

Optional, for Gmail add-on work:

```bash
npm install -g @google/clasp
```

---

## 1. Clone and install

```bash
git clone <repository-url>
cd one-click-response
```

### Python virtual environment

All Python dependencies are installed into a project-local virtual environment at `functions/venv/`. Nothing is installed globally.

```bash
./scripts/setup-local.sh
```

This script:

1. Creates `functions/venv/` (if it does not exist)
2. Installs packages from [`functions/requirements.txt`](../../functions/requirements.txt) and [`functions/requirements-dev.txt`](../../functions/requirements-dev.txt)

The virtual environment **must use Python 3.13** to match the Cloud Functions runtime (`python313` in `firebase.json`). The setup script picks `python3.13` automatically.

To activate the venv manually in your shell:

```bash
source functions/venv/bin/activate
```

### Firebase CLI

```bash
npm install -g firebase-tools
firebase login
```

Link to your Firebase project (or use the default in [`.firebaserc`](../../.firebaserc)):

```bash
firebase use --add
```

---

## 2. Firebase emulators

The emulator configuration is in [`firebase.json`](../../firebase.json):

| Emulator | Port | Use |
|---|---|---|
| Hosting | 5000 | Frontend (`web/public/`) |
| Functions | 5001 | Python API |
| Firestore | 8080 | Database |
| Auth | 9099 | Google sign-in (optional) |
| Emulator UI | 4000 | Dashboard at http://localhost:4000 |

### Start emulators

From the repository root:

```bash
firebase emulators:start
```

To persist data between sessions:

```bash
firebase emulators:start --import=./emulator-data --export-on-exit=./emulator-data
```

### Local frontend config

For emulator-based Auth, [`web/public/js/firebase-init.js`](../../web/public/js/firebase-init.js) automatically connects to the Auth emulator when the page is served from `localhost`.

Update [`web/public/js/config.js`](../../web/public/js/config.js) with your Firebase project credentials (same values as production, or a dedicated dev project).

### Local backend

When the Functions emulator runs, `/api/**` requests from Hosting (port 5000) are rewritten to the function.

For standalone API development without the full emulator suite:

```bash
source functions/venv/bin/activate
cd functions
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export GCLOUD_PROJECT=one-click-response
python dev_server.py
```

`dev_server.py` starts a local Flask server on port 5001.

Set `HOST_URL` when testing response link generation:

```bash
export HOST_URL=http://localhost:5000
```

### Seed sample data

With the Firestore emulator running:

```bash
./scripts/seed-emulator.sh
```

This creates a dev user, campaign, and sample response buttons for manual testing.

---

## 3. Running tests

All test commands use the virtual environment automatically via [`scripts/test.sh`](../../scripts/test.sh).

### Unit tests

Fast tests with mocked dependencies (no emulators required):

```bash
./scripts/test.sh unit
```

Equivalent manual command:

```bash
source functions/venv/bin/activate
cd functions
pytest tests/unit -v --cov=src --cov-report=term-missing
```

### Integration tests

Requires the Firestore emulator. `test.sh` starts it automatically via `firebase emulators:exec`:

```bash
./scripts/test.sh integration
```

### All tests

```bash
./scripts/test.sh all
```

Runs unit tests, then integration tests against the Firestore emulator.

### Lint

```bash
./scripts/test.sh lint
```

Runs [ruff](https://docs.astral.sh/ruff/) on `functions/src/` and `functions/tests/`.

### Test layout

```
functions/tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_api.py      # HTTP route tests (Flask test client)
│   ├── test_auth.py     # Token verification
│   ├── test_crypto.py   # Encryption round-trips
│   ├── test_links.py    # Link creation service
│   └── test_responses.py # Registration, dedup, record/forward rules
└── integration/
    └── test_register_flow.py  # End-to-end with Firestore emulator
```

---

## 4. Typical development workflows

### Backend change

1. Edit code under `functions/src/`.
2. `./scripts/test.sh unit`
3. `firebase emulators:start` and exercise endpoints via `http://localhost:5000/api/...`

### Frontend change

1. Edit files under `web/public/`.
2. With emulators running, open `http://localhost:5000/settings/`.
3. Hard-refresh the browser after changes (static files are served directly).

### Gmail add-on change

1. Edit `gmail-addon/Code.gs`.
2. `cd gmail-addon && clasp push`
3. Reload the add-on in Gmail compose (test deployment).
4. See [`gmail-addon/TESTING.md`](../../gmail-addon/TESTING.md) for a manual checklist.

### Full stack local test

1. `./scripts/setup-local.sh`
2. `firebase emulators:start`
3. `./scripts/seed-emulator.sh` (optional)
4. Open `http://localhost:5000/settings/` — sign in, create campaign
5. Use the Gmail add-on with `API_BASE_URL` set to `http://localhost:5000` (add-on testing against localhost requires Apps Script test deployment and may need tunneling for external requests)

> **Note:** The Gmail add-on runs on Google's servers and cannot reach `localhost` directly. For add-on development, either deploy to a staging Firebase project or use a tunnel (e.g. ngrok) pointing at the Hosting emulator.

---

## 5. CI

GitHub Actions workflow [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs on push/PR to `main`:

1. `./scripts/setup-local.sh` — create venv and install deps
2. `./scripts/test.sh lint`
3. `./scripts/test.sh unit`
4. `./scripts/test.sh integration` — Firestore emulator via `firebase emulators:exec`

---

## 6. Project structure (quick reference)

```
one-click-response/
├── functions/           # Python Cloud Functions backend
│   ├── src/             # Application code
│   ├── tests/           # pytest suites
│   └── venv/            # Local virtualenv (gitignored)
├── web/public/          # Frontend static files
├── gmail-addon/         # Apps Script Gmail add-on
├── scripts/             # setup, test, deploy helpers
├── firebase.json        # Hosting, functions, emulator config
├── firestore.rules      # Security rules
└── docs/
    ├── installing/      # Production deployment guide
    ├── development/     # This guide
    └── specs/           # Product specifications
```
