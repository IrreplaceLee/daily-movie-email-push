# Public Release Security Checklist

Before publishing or updating this public repository:

- [ ] No real `.env` file is committed.
- [ ] No OAuth refresh token, API key, cookie, or authorization header is committed.
- [ ] No real `history.json` or `recipient_memory.json` is committed.
- [ ] No Gmail message id, recipient memory, or private user preference appears in committed files.
- [ ] README examples use `recipient@example.com` placeholders only.
- [ ] `assets/stills/sources.json` documents sources/licenses for still images.
- [ ] Git history is new public history, not the original private repository history.
- [ ] GitHub Actions logs do not print raw recipient email addresses or Gmail message ids.
