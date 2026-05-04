
# Bravo AAC

An open-source Augmentative and Alternative Communication (AAC) application powered by Google Gemini and deployed on Google Cloud Platform.

Bravo AAC helps individuals with communication differences express themselves using AI-generated word suggestions, pictogram symbol boards, and customizable communication pages. It supports scan-based access, multiple AAC board formats (Grid, Tap, Freestyle/Compose), and import from common AAC formats (Accent MTI, TouchChat).

## Features

- **AI-powered word prediction** — Context-aware suggestions using Google Gemini
- **Multiple board types** — Grid, Tap interface, and Freestyle/Compose modes
- **Scan access** — Full switch/scan support across all interfaces
- **AAC format import** — Import from Accent MTI and TouchChat formats
- **Custom image support** — Upload and manage per-user pictogram images
- **Multi-environment** — Development, testing, and production environments on GCP
- **Firebase Auth** — User authentication and per-account data isolation
- **Firestore** — Real-time database for user profiles, boards, and content

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI |
| LLM | Google Gemini (via `google-generativeai`) |
| Database | Firestore |
| Auth | Firebase Authentication |
| Storage | Google Cloud Storage |
| Deployment | Cloud Run (Docker), Cloud Build CI/CD |
| TTS | Google Cloud Text-to-Speech |

## Getting Started

### Prerequisites

- Python 3.12+
- Docker (for local Cloud Run simulation)
- A GCP project with the following APIs enabled:
  - Cloud Run, Cloud Build, Firestore, Firebase Auth, Cloud Storage, Text-to-Speech, Gemini API
- A Firebase project linked to your GCP project
- A Google Gemini API key

### Local Development

1. **Clone the repo**
   ```bash
   git clone https://github.com/OSUBlakester/BravoGCPCopilot.git
   cd BravoGCPCopilot
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-local.txt
   ```

3. **Configure credentials**
   ```bash
   cp config.py.template config.py
   # Edit config.py with your Firebase project credentials
   ```
   Or create a `.env` file from the template:
   ```bash
   cp .env.template .env
   # Edit .env with your environment variables
   ```

4. **Start the server**
   ```bash
   ./restart-local.sh
   ```
   The app will be available at `http://localhost:8000`.

### Cloud Run Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full multi-environment deployment instructions.

Automated deployments are configured via [cloudbuild.yaml](cloudbuild.yaml) — merging to `main` triggers a Cloud Build pipeline that builds and deploys to Cloud Run.

## Required Environment Variables

These must be set in your Cloud Run service (or `.env` for local dev):

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | Yes | `development`, `testing`, or `production` |
| `GCP_PROJECT_ID` | Yes | Your GCP project ID |
| `GEMINI_PRIMARY_MODEL` | Yes | Primary Gemini model (e.g. `gemini-2.5-flash-lite`) |
| `GEMINI_FALLBACK_MODEL` | Yes | Fallback Gemini model (e.g. `gemini-1.5-flash-latest`) |
| `GEMINI_FAST_WORDS_MODEL` | No | Defaults to `GEMINI_PRIMARY_MODEL` |
| `FIREBASE_API_KEY_*` | Yes | Firebase API key for your environment suffix |
| `FIREBASE_AUTH_DOMAIN_*` | Yes | Firebase auth domain |
| `FIREBASE_PROJECT_ID_*` | Yes | Firebase project ID |
| `FIREBASE_STORAGE_BUCKET_*` | Yes | Firebase storage bucket |
| `GOOGLE_API_KEY` | Yes | Gemini API key (via Secret Manager recommended) |
| `SERVICE_ACCOUNT_KEY_PATH` | Yes | Path to GCP service account JSON |
| `EMAIL_FEATURE_ENABLED` | No | Set `true` to enable Gmail integration |
| `GOOGLE_OAUTH_CLIENT_ID` | If email enabled | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | If email enabled | OAuth client secret |
| `EMAIL_OAUTH_STATE_SECRET` | If email enabled | Random secret for OAuth state |
| `EMAIL_TOKEN_ENCRYPTION_KEY` | If email enabled | Fernet key for token encryption |

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for full details and GCP Console/CLI setup instructions.

## AAC Format Import

Bravo supports importing communication boards from:

- **Accent/NovaCHAT MTI files** — via `accent_mti_parser.py` and `accent_bravo_mapper.py`
- **TouchChat .ce/.c4v files** — via `touchchat_ce_parser.py`

See [MTI_MIGRATION_PROCESS.md](MTI_MIGRATION_PROCESS.md) for the migration workflow.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching workflow and contribution guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
