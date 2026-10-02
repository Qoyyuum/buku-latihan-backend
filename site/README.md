# Buku Latihan — Account Portal

Static Astro site: marketing pages (index, privacy, terms, FAQ) plus
account self-service (signup, login, email verification, password reset
and change, optional TOTP 2FA, account deletion). Talks to the Django API
via `django-allauth` headless endpoints (`/_allauth/app/v1/`) with an
`X-Session-Token`.

## Develop

```bash
cd site
npm install
npm run dev     # http://localhost:4321
```

## Build

```bash
npm run build   # outputs static files to dist/
```

## Environment

| Var | Purpose | Example |
|---|---|---|
| `PUBLIC_API_URL` | Base URL of the Django API | `https://api.bukulatihan.app` |

Local dev: copy `.env` (gitignored) or create `.env` with
`PUBLIC_API_URL=http://localhost:8000`.

## Deploy — Cloudflare Pages

1. Cloudflare dashboard → Workers & Pages → Create → Pages → Connect to Git.
2. Build settings:
   - **Build command:** `npm run build`
   - **Build output directory:** `site/dist` (or set root directory to `site`
     and output `dist`)
3. Environment variable: `PUBLIC_API_URL=https://<your-api-host>`.
4. Backend must allow the Pages origin: add `https://<site>.pages.dev` (and
   any custom domain) to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`,
   and set `FRONTEND_BASE_URL` to the site URL so email links point back here.

## Backend env vars required for the portal

```env
FRONTEND_BASE_URL=https://<site>.pages.dev
CORS_ALLOWED_ORIGINS=https://<site>.pages.dev,http://localhost:8081
CSRF_TRUSTED_ORIGINS=https://<site>.pages.dev,http://localhost:8081

EMAIL_HOST=smtp.resend.com        # or Brevo, etc.
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<smtp-token>
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=noreply@bukulatihan.app

ACCOUNT_EMAIL_VERIFICATION=mandatory
```

Headless endpoints used:

| Flow | Endpoint |
|---|---|
| Signup | `POST /_allauth/app/v1/auth/signup` |
| Login / logout / session | `POST /_allauth/app/v1/auth/login`, `DELETE .../auth/session` |
| Email verify | `POST /_allauth/app/v1/auth/email/verify` |
| Password request/reset | `POST .../auth/password/request`, `.../auth/password/reset` |
| Password change | `POST .../account/password/change` |
| TOTP | `GET/POST/DELETE .../account/authenticators/totp` |
| Recovery codes | `GET/POST .../account/authenticators/recovery-codes` |
| 2FA login | `POST .../auth/2fa/authenticate` |
| Delete account | `DELETE /api/v1/users/me/` |
