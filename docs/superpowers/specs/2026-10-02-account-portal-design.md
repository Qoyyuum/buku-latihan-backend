# Account Portal Website — Design Spec

Date: 2026-10-02
Status: Approved (design)

## Intent

Buku Latihan needs a public-facing website so the Android app can be listed on
Google Play. Play policy requires that users can delete their account (and
associated data) from outside the app via a web link. The same site provides
account self-service (signup, password change/reset, optional 2FA) and the
legal/explanatory pages (privacy policy, terms of service, homepage, FAQ).

Success criteria:

- A user can sign up on the web as a **student** or **parent**.
- A logged-in user can change their password, request a reset link by email,
  enable/disable TOTP 2FA, and permanently delete their account.
- Static pages: homepage (what Buku Latihan is, free for everyone), privacy
  policy, terms of service, FAQ.
- Deploys to Cloudflare Pages (free tier), static only.
- Uses `frontend/assets/logo.jpg` as the site logo.

## Decisions

| Question | Decision |
|---|---|
| Signup model | Public signup, role choice limited to `student` / `parent` |
| Auth approach | `django-allauth` headless mode, session token via `X-Session-Token` |
| Password reset / email verification | allauth headless + SMTP (env-configured, e.g. Resend/Brevo free tier) |
| 2FA | Optional TOTP via `allauth.mfa` |
| Account deletion | Immediate `DELETE` with password confirmation (Play-compliant) |
| Site stack | Astro, `output: 'static'`, vanilla `fetch` client, no framework islands |
| Existing JWT (mobile app) | Unchanged — SimpleJWT endpoints remain |
| Deployment | Cloudflare Pages, build `portal/` → `portal/dist` |

## Backend changes (Django)

### Dependencies / settings

- Add `django-allauth[mfa]` (pinned version, ≥7 days old at implementation time).
- `INSTALLED_APPS`: `allauth`, `allauth.account`, `allauth.mfa`,
  `allauth.headless`. Add `allauth.account.middleware.AccountMiddleware`.
- Settings (base.py, env-overridable):
  - `ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]`
  - `ACCOUNT_EMAIL_VERIFICATION = "mandatory"` — verification email sent at
    signup; login allowed but account flagged unverified until confirmed
    (allauth default behavior; document actual enforcement choice in plan).
  - `HEADLESS_ONLY = True`, `HEADLESS_SERVE_SPECIFICATION = True` (dev only,
    off in prod).
  - `HEADLESS_FRONTEND_URLS` mapping `account_confirm_email`,
    `account_reset_password`, etc. to the Astro site base URL
    (`FRONTEND_BASE_URL` env var, e.g. `https://<site>.pages.dev`).
  - `EMAIL_BACKEND` + `EMAIL_HOST`/credentials via env; console backend default
    in `local.py`/`test.py`.
  - `CORS_ALLOWED_ORIGINS`: add the Pages domain via env (no code change needed,
    but documented for deploy).
- URLs: `path("_allauth/", include("allauth.headless.urls"))` (allauth's
  recommended mount point; final path recorded in plan — use
  `HEADLESS_CLIENTS = ["app"]` so token strategy is used, avoiding
  cross-origin cookie/CSRF entirely).

### Custom signup adapter

`apps/accounts/adapters.py`: subclass allauth's account adapter to accept a
`role` field on signup, whitelisted to `UserRole.STUDENT` / `UserRole.PARENT`.
Requests for `teacher`/`admin` are rejected with a validation error. Teacher
accounts remain provisioned by admins (existing `UserViewSet.create`
`IsTeacher` path is unchanged).

### Account deletion endpoint

New `@action(detail=False, methods=["delete"], url_path="me")`-style endpoint —
`DELETE /api/v1/users/me/` — requires `password` in the body; verify with
`user.check_password`, then `user.delete()` (FK cascades handle
enrollments/marks/submissions per existing `on_delete` behavior — audit each
FK in the plan and confirm nothing blocks deletion). Returns `204`.

Note: headless tokens authenticate via allauth's `X-Session-Token`; this
endpoint must accept that auth class in addition to JWT so the website can
call it (either via `allauth.headless`' auth support or by accepting the
session token — implementation detail settled in the plan; the contract to
the site is the same).

### Tests (`apps/accounts/tests/`)

- Signup as student/parent succeeds; teacher/admin role rejected.
- Password reset request → confirm flow.
- `DELETE /users/me/`: wrong password → 400; correct → user + dependents gone.
- TOTP: activate with valid code, deactivate, recovery codes issued.
- Unauthenticated calls rejected.

## Frontend (`portal/` — Astro static)

```
portal/
  public/logo.jpg               (copied from frontend/assets/logo.jpg)
  src/pages/
    index.astro                 homepage: what Buku Latihan is, free note, links
    privacy.astro               privacy policy
    terms.astro                 terms of service
    faq.astro                   FAQ incl. "free for everyone", data control
    signup.astro                register (student/parent picker, email verify notice)
    login.astro
    verify-email.astro          handles ?key= from verification email
    reset-password.astro        request form + confirm form (?key= in URL)
    account.astro               change password, TOTP 2FA manage, delete account
  src/lib/api.ts                fetch wrapper: X-Session-Token stored in
                                sessionStorage; 401 → redirect to /login
  src/styles/global.css         hand-rolled CSS, mobile-friendly
```

- `PUBLIC_API_URL` env var supplies the API base at build time.
- `account.astro` is a client-rendered page: no token → redirect to login.
- All legal copy generic; user reviews before Play submission.

## Data / auth flow

1. Signup: site `POST _allauth/app/v1/auth/signup` with role → allauth
   creates user, sends verification email.
2. Login: site `POST .../auth/login` → response contains session token →
   stored in `sessionStorage`, sent as `X-Session-Token` on subsequent calls.
3. Password reset: request → allauth emails link to
   `https://portal/reset-password?key=...` → confirm posts key + new password.
4. Delete: `DELETE /api/v1/users/me/` with password → 204 → clear token,
   show confirmation.
5. 2FA: `GET/POST .../auth/2fa/totp` returns secret + provisioning URI (QR
   rendered client-side); activate with code; recovery codes displayed once.

## Error handling

- API errors surfaced as allauth's standard `{errors: [{code, message}]}`
  shape; site maps common codes (`email_taken`, `incorrect_password`,
  `invalid_token`) to friendly messages, shows raw message otherwise.
- Token expiry/401 → clear stored token, redirect to login.

## Deployment

- Cloudflare Pages project: build command `npm run build`, build output
  `portal/dist`, root directory `site` (or build from repo root with
  `cd portal && npm run build`).
- Env: `PUBLIC_API_URL` on Pages; on the Django side:
  `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`,
  `EMAIL_*` SMTP settings.
- Worktree branch `feat/account-portal` → PR into `prod`.

## Out of scope

- Teacher self-registration, account data export, profile editing beyond
  password, social/OAuth login, CAPTCHA (noted: public signup may want
  Turnstile later — free — flagged as follow-up, not in this spec).
