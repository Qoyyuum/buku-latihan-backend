# Account Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Public Astro marketing/account site on Cloudflare Pages plus the backend account-management API (allauth headless) it consumes, satisfying Google Play's account-deletion requirement.

**Architecture:** `django-allauth` headless mode (`app` client, session-token auth via `X-Session-Token`) mounted at `_allauth/` provides signup/login/reset/change/TOTP; one custom DRF endpoint `DELETE /api/v1/users/me/` handles deletion. A static Astro site in `site/` talks to it via `fetch`.

**Tech Stack:** Django 6.x + DRF + django-allauth[mfa] + SimpleJWT (unchanged) · Astro static + vanilla TS · pytest · uv · ruff

**Spec:** `docs/superpowers/specs/2026-10-02-account-portal-design.md`

## Global Constraints

- Backend work happens in `backend/`; site in `site/`. All paths below are repo-relative.
- Signup `role` is whitelisted to `student`/`parent` only — `teacher`/`admin` rejected.
- Existing SimpleJWT endpoints (`/api/v1/auth/token/…`) and teacher-provisioned `POST /api/v1/users/` must keep working — regression tests guard this.
- Backend test/lint commands: `cd backend && uv run pytest` / `uv run ruff check`. Site build: `cd site && npm run build`.
- Pin `django-allauth[mfa]` to a version ≥7 days old (e.g. `~=65.x.y` matching what's resolved).
- Public signup, immediate deletion — see spec for rationale.
- Email backend: console in `local.py`/`test.py` (locmem for tests is fine); SMTP via env in production.

## Review Focus

Risks the spec implies but happy-path tests don't pin:

- **Role escalation**: signup payload claiming `teacher`/`admin`/`superuser` must be rejected — tested in Task 1.
- **Deletion password check**: `DELETE /users/me/` with wrong/missing password must 400 and NOT delete — tested in Task 2.
- **Cascade on teacher delete**: `Classroom.teacher` is CASCADE — deleting a teacher deletes their classrooms. Acceptable per spec (immediate deletion), but confirm test asserts enrollments/students' rows behave as expected (students are separate Users — they persist).
- **Email verification enforcement**: `ACCOUNT_EMAIL_VERIFICATION="mandatory"` — verify a login attempt post-signup either succeeds with `email_verification` pending flow or is blocked; pin actual allauth behavior in Task 1 tests.
- **`_allauth` URL mount + JWT coexistence**: JWT login must still work after allauth is installed — regression test in Task 1.

---

### Task 1: Wire allauth headless + role-whitelisted signup

**Files:**
- Modify: `backend/pyproject.toml` (add `django-allauth[mfa]`)
- Modify: `backend/config/settings/base.py`
- Modify: `backend/config/settings/test.py`
- Modify: `backend/config/urls.py`
- Create: `backend/apps/accounts/adapters.py`
- Create: `backend/apps/accounts/forms.py`
- Test: `backend/apps/accounts/tests/test_headless_auth.py`

**Interfaces:**
- Produces (used by site + tests): headless endpoints under `/_allauth/app/v1/` — `POST auth/signup`, `POST auth/login`, `POST auth/password/request`, `POST auth/password/reset`, `POST auth/password/change`, `GET/POST/DELETE auth/2fa/totp`, `GET/POST auth/2fa/recovery-codes`, `GET/PUT/POST/DELETE account/email`. Auth header for app client: `X-Session-Token: <token>`.

- [ ] **Step 1: Write failing tests** in `test_headless_auth.py` (follow existing fixture style; `APIClient`, `pytest.mark.django_db`):

```python
SIGNUP = "/_allauth/app/v1/auth/signup"
LOGIN = "/_allauth/app/v1/auth/login"

def test_signup_student(db, client):
    res = client.post(SIGNUP, {
        "username": "new", "email": "n@x.com",
        "password": "Str0ng!Pass", "role": "student",
    }, format="json")
    assert res.status_code == 200
    assert User.objects.get(username="new").role == UserRole.STUDENT

def test_signup_teacher_rejected(db, client):  # role escalation
    res = client.post(SIGNUP, {
        "username": "t", "email": "t@x.com",
        "password": "Str0ng!Pass", "role": "teacher",
    }, format="json")
    assert res.status_code in (400, 403)
    assert not User.objects.filter(username="t").exists()

def test_login_returns_session_token(db, client, student):
    res = client.post(LOGIN, {
        "username": "student", "password": "pw",
    }, format="json")
    assert res.status_code == 200
    assert res.json()["meta"]["session_token"]  # or access_token — assert whichever allauth emits

def test_jwt_login_still_works(db, client, student):  # regression
    res = client.post("/api/v1/auth/token/", {
        "username": "student", "password": "pw",
    }, format="json")
    assert res.status_code == 200 and "access" in res.json()
```

(Adjust fixtures: `student` fixture needs `email` and verified email — or set `ACCOUNT_EMAIL_VERIFICATION="none"` in `test.py` and mandatory in base; pick per what the signup response asserts. Pin whichever behavior allauth produces in the passing test.)

- [ ] **Step 2: Run tests** — `cd backend && uv run pytest apps/accounts/tests/test_headless_auth.py -v` — expect failures (endpoints 404).

- [ ] **Step 3: Install + configure allauth**
  - `uv add "django-allauth[mfa]"` (check resolved version is ≥7 days old).
  - `base.py` — append to `THIRD_PARTY_APPS`: `"allauth"`, `"allauth.account"`, `"allauth.mfa"`, `"allauth.headless"`; middleware: `"allauth.account.middleware.AccountMiddleware"` after `AuthenticationMiddleware`.
  - Settings:
    ```python
    ACCOUNT_LOGIN_METHODS = {"username", "email"}
    ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
    ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="mandatory")
    ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
    ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.RoleSignupForm"
    HEADLESS_CLIENTS = ["app"]
    HEADLESS_ONLY = True
    HEADLESS_FRONTEND_URLS = {
        "account_confirm_email": env("FRONTEND_BASE_URL", default="http://localhost:4321") + "/verify-email?key={key}",
        "account_reset_password_from_key": env("FRONTEND_BASE_URL", default="http://localhost:4321") + "/reset-password?key={key}",
        "account_signup": env("FRONTEND_BASE_URL", default="http://localhost:4321") + "/signup",
    }
    EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
    EMAIL_HOST = env("EMAIL_HOST", default="")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@bukulatihan.app")
    ```
  - `test.py`: `ACCOUNT_EMAIL_VERIFICATION = "none"`, `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"`.
  - `urls.py`: `path("accounts/", include("allauth.urls"))` and `path("_allauth/", include("allauth.headless.urls"))`.
  - `adapters.py`: `AccountAdapter(DefaultAccountAdapter)`; `save_user` sets `user.role` from the signup form's `role` field (already validated to student/parent).
  - `forms.py`: `RoleSignupForm(forms.Form)` — `role = forms.ChoiceField(choices=[("student",...),("parent",...)])` rejecting teacher/admin by construction; `signup(self, request, user)` assigns `user.role = self.cleaned_data["role"]`.
  - Run `uv run python manage.py migrate`.

- [ ] **Step 4: Run tests** — expect PASS. If headless strips the extra `role` field before the form, wire it through `HEADLESS_...` signup input per allauth docs; the tests are the contract.

- [ ] **Step 5: Lint + commit**
  - `uv run ruff check` — fix issues.
  - Commit: `feat: add allauth headless signup/login with role whitelist`

### Task 2: `DELETE /api/v1/users/me/` account deletion

**Files:**
- Modify: `backend/config/settings/base.py` (add `XSessionTokenAuthentication` to `DEFAULT_AUTHENTICATION_CLASSES`)
- Modify: `backend/apps/accounts/api/views.py` (add `delete` handling on `me` action or new `delete_me` action)
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Consumes: `allauth.headless.contrib.rest_framework.authentication.XSessionTokenAuthentication`; `UserViewSet` (Task 1 settings).
- Produces: `DELETE /api/v1/users/me/` — body `{"password": str}` → `204`; wrong/missing password → `400`; unauthenticated → `401`.

- [ ] **Step 1: Failing tests** appended to `test_api.py`:

```python
def test_delete_me_wrong_password(client, student):
    client.force_authenticate(student)
    res = client.delete("/api/v1/users/me/", {"password": "nope"}, format="json")
    assert res.status_code == 400
    assert User.objects.filter(pk=student.pk).exists()

def test_delete_me_success_cascades(client, teacher, student):
    classroom = Classroom.objects.create(name="C", teacher=teacher)
    Enrollment.objects.create(student=student, classroom=classroom)
    client.force_authenticate(student)
    res = client.delete("/api/v1/users/me/", {"password": "pw"}, format="json")
    assert res.status_code == 204
    assert not User.objects.filter(pk=student.pk).exists()
    assert not Enrollment.objects.filter(student_id=student.pk).exists()
    assert Classroom.objects.filter(pk=classroom.pk).exists()  # other users unaffected

def test_delete_me_unauthenticated(client):
    assert client.delete("/api/v1/users/me/").status_code == 401
```

- [ ] **Step 2: Run** — `uv run pytest apps/accounts/tests/test_api.py -v` — expect 405/404 on DELETE.

- [ ] **Step 3: Implement.** In `UserViewSet`, change `me` action to `methods=["get", "delete"]`; on DELETE read `request.data.get("password")`, `request.user.check_password` else `Response({"detail": "incorrect password"}, status=400)`, then `request.user.delete()` → `Response(status=204)`. Add `XSessionTokenAuthentication` to `DEFAULT_AUTHENTICATION_CLASSES` in `base.py`.

- [ ] **Step 4: Run tests** — PASS; run whole `apps/accounts` suite for regressions.

- [ ] **Step 5: Commit** — `feat: add DELETE /users/me/ with password confirmation`

### Task 3: Astro site scaffold + static pages

**Files:**
- Create: `site/package.json`, `site/astro.config.mjs`, `site/tsconfig.json`, `site/.gitignore`
- Create: `site/src/layouts/Base.astro` (header w/ logo + nav, footer links to privacy/terms/faq)
- Create: `site/src/styles/global.css`
- Create: `site/src/pages/{index,privacy,terms,faq}.astro`
- Create: `site/public/logo.jpg` (copy of `frontend/assets/logo.jpg`)

**Interfaces:**
- Produces: `site/dist` via `npm run build`; `Base.astro` layout props `{title: string}` used by all pages; shared `.btn`, `.card`, `form` styles in `global.css` reused by auth pages in Tasks 4–5.

- [ ] **Step 1: Scaffold** — `npm create astro@latest site -- --template minimal --no-install` (or hand-write `package.json` with `astro` devDep pinned ≥7 days old; then `npm install`). `astro.config.mjs`: `export default defineConfig({ output: 'static' })` (default anyway). Copy `frontend/assets/logo.jpg` → `site/public/logo.jpg`.

- [ ] **Step 2: Write pages** — `index.astro`: hero ("Buku Latihan — practice past-year papers, write on worksheets, get marked"), free-for-everyone callout, links to app + FAQ. `privacy.astro` / `terms.astro`: complete generic policy text covering account data, email, submissions, deletion rights (user reviews before Play submission — keep placeholders out; write real copy). `faq.astro`: free? delete data? who can sign up? contact.

- [ ] **Step 3: Verify** — `cd site && npm run build` exits 0 and `site/dist/index.html` exists; spot-check `dist/privacy/index.html`.

- [ ] **Step 4: Commit** — `feat: scaffold Astro site with marketing/legal pages`

### Task 4: Auth API client + signup/login/reset/verify pages

**Files:**
- Create: `site/src/lib/api.ts`
- Create: `site/src/pages/{login,signup,verify-email,reset-password}.astro`

**Interfaces:**
- Consumes: headless endpoints from Task 1 under `${PUBLIC_API_URL}/_allauth/app/v1/`; allauth error shape `{errors: [{code, message, param?}]}`; `meta.session_token` on login/signup response.
- Produces: `api.ts` exports —
  ```ts
  apiFetch(path: string, opts?: RequestInit): Promise<Response>   // base URL + JSON + X-Session-Token from sessionStorage
  login(username, password): Promise<void>                        // stores token
  logout(): Promise<void>
  getToken(): string | null
  requireAuth(): void                                             // redirect /login if no token
  ```  — imported by `account.astro` in Task 5.

- [ ] **Step 1: `api.ts`** — thin wrapper as specified; `PUBLIC_API_URL` via `import.meta.env.PUBLIC_API_URL`; on 401 clear token.

- [ ] **Step 2: Pages** — `login.astro`: username+password form → `auth/login`, on 401 flow `is_2fa_required` redirect to `/account` after second-factor step (keep simple: inline TOTP code input shown when `meta.is_authenticated` requires 2FA — implement the `auth/2fa/authenticate` call inline). `signup.astro`: username/email/password/role radio (Student|Parent) → `auth/signup`; show "check your email" on success. `verify-email.astro`: reads `?key=` → `POST account/email/verify` (or `auth/email/verify` — use the path allauth exposes; check `/_allauth/openapi` spec during implementation). `reset-password.astro`: no `key` → request form (`auth/password/request`); with `?key=` → confirm form (`auth/password/reset`).

- [ ] **Step 3: Verify** — `npm run build` clean; `npm run dev` + manual smoke against `manage.py runserver` if feasible, else code review against allauth openapi (`/_allauth/app/v1/openapi.json` or the docs).

- [ ] **Step 4: Commit** — `feat: site auth pages and API client`

### Task 5: Account page — change password, TOTP 2FA, delete

**Files:**
- Create: `site/src/pages/account.astro`
- Modify: `site/src/lib/api.ts` if a helper is needed (e.g. `deleteAccount(password)`)

**Interfaces:**
- Consumes: `api.ts` exports; `auth/password/change`, `auth/2fa/totp` GET/POST/DELETE, `auth/2fa/recovery-codes`, `DELETE ${PUBLIC_API_URL}/api/v1/users/me/`.

- [ ] **Step 1: `account.astro`** — `requireAuth()` guard; three sections:
  - **Change password**: current + new password → `auth/password/change`.
  - **2FA**: GET `auth/2fa/totp` — if absent, POST to create → render `totp_url` as QR (tiny client-side: use an `otpauth://` QR via `https://api.qrserver.com` image or a small vendored QR lib — prefer no external image service; vendor `qrcode` npm pkg and render to canvas); activate with code → show recovery codes once. If enabled, DELETE deactivates.
  - **Danger zone**: "Delete account" → confirm dialog + password field → `DELETE /api/v1/users/me/` → on 204 clear token, show "account deleted" + link home.

- [ ] **Step 2: Verify** — `npm run build` clean.

- [ ] **Step 3: Commit** — `feat: account page with password change, TOTP, deletion`

### Task 6: Deploy config + docs + final review

**Files:**
- Create: `site/wrangler.jsonc` or document Pages settings in `site/README.md` (Pages projects are usually connected via dashboard; a README with build cmd `npm run build`, output `dist`, env `PUBLIC_API_URL` suffices)
- Modify: `backend/.env.example` or README — document `EMAIL_*`, `FRONTEND_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `ACCOUNT_EMAIL_VERIFICATION`

- [ ] **Step 1: Write deploy docs** — `site/README.md`: connect repo to Cloudflare Pages, build settings, env vars; backend `.env` additions for prod (SMTP creds, frontend URL, CORS).

- [ ] **Step 2: Full test suite** — `cd backend && uv run pytest` + `uv run ruff check`; `cd site && npm run build`. All green.

- [ ] **Step 3: Commit** — `docs: deploy instructions for Pages and backend env`
