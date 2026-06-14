# Architecture

## Runtime flow

```text
GitHub Actions
  -> Python mailer
  -> Gmail OAuth token refresh
  -> Gmail reply search
  -> DeepSeek JSON response
  -> HTML email
  -> Gmail send API
  -> local runtime history and memory files
```

## Key modules

- Environment validation keeps secrets outside the repository.
- Gmail helpers refresh tokens, query recent replies, and send MIME emails.
- DeepSeek helpers request structured JSON for movie selection and email composition.
- Memory helpers merge preference updates and avoid repeat recommendations.
- Still-image assets are stored locally with source/license metadata for review.

## Public-safety boundary

The public repository shows the engineering structure without shipping private recipient history, private memory, OAuth recovery notes, or real credentials. Runtime files are ignored by Git.
