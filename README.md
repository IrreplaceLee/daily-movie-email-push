# Daily Movie Email Push

Public showcase version of a daily personalized classic movie recommendation email workflow. The private project runs on GitHub Actions, reads recipient feedback from Gmail, asks DeepSeek to generate a personalized recommendation, and sends one HTML email per recipient.

This public repository is prepared for HR review. It keeps the core implementation, workflow, movie catalogue, and still-image assets, while removing private runtime history, recipient memory, OAuth recovery notes, and real secrets.

## Highlights

- Scheduled automation with GitHub Actions.
- Gmail API integration for sending personalized HTML emails.
- DeepSeek API integration for preference analysis, movie selection, and email writing.
- Per-recipient processing so each recipient receives an individual recommendation.
- Local still-image library under `assets/stills/`, with source/license notes in `assets/stills/sources.json`.
- Public-safe repository boundary: runtime history and memory are ignored and only example templates are committed.

## How it works

```text
GitHub Actions schedule
  -> movie_mailer.py
  -> Gmail access-token refresh
  -> optional Gmail reply lookup
  -> DeepSeek preference analysis and recommendation
  -> HTML email composition
  -> Gmail send API
  -> local history/memory update
```

The public workflow does not commit generated `history.json` or `recipient_memory.json` back to the repository. If you run it yourself, those files remain local runtime state and are ignored by Git.

## Repository structure

```text
.
├── .github/workflows/daily-movie-email.yml
├── assets/stills/
├── docs/architecture.md
├── tools/check_stills.py
├── movie_mailer.py
├── movies.json
├── history.example.json
├── recipient_memory.example.json
├── .env.example
└── SECURITY_CHECKLIST.md
```

## Required GitHub Secrets

Open `Settings` -> `Secrets and variables` -> `Actions`, then add:

```text
GMAIL_CLIENT_ID=your_google_oauth_client_id
GMAIL_CLIENT_SECRET=your_google_oauth_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
SENDER_EMAIL=your_gmail_address@gmail.com
RECIPIENT_EMAIL=recipient@example.com;friend@example.com
DEEPSEEK_API_KEY=your_deepseek_api_key
```

Optional:

```text
DEEPSEEK_MODEL=deepseek-v4-pro
```

## Local setup

```bash
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` with local test values, then export those variables before running `python movie_mailer.py`.

## Still image assets

The public repository keeps the existing still-image assets so reviewers can inspect the resource organization. Source and license notes are tracked in `assets/stills/sources.json`; only keep images you have permission to store and redistribute. `movies.json` is filtered to movie entries whose referenced still files are complete in this public release.

Check still coverage with:

```bash
python tools/check_stills.py
```

## Public release boundary

Not included in this public repository:

- real `history.json`
- real `recipient_memory.json`
- OAuth refresh-token recovery notes
- real `.env` files
- original private Git history
- any real API key, OAuth token, Gmail message id, or recipient memory

## Notes

- The project uses model knowledge for recommendation writing and does not claim live movie-database verification.
- Public workflow logs intentionally avoid printing raw recipient addresses or Gmail message ids.
- If this repository is used for real sending, keep all secrets in GitHub Actions Secrets and do not commit runtime state.
