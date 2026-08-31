# Seed Scripts

Development utilities for populating Firebase Auth and Firestore with local test data.

## Quick start

```bash
cd teamchat-ai/backend
source .venv/bin/activate

export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export FIREBASE_PROJECT_ID=your-firebase-project-id

python ../scripts/seed_dev_data.py
```

See [docs/seed-credentials.md](../docs/seed-credentials.md) for prerequisites, test accounts, and rerun behavior.
