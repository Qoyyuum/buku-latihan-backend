# Frontend app

One Expo (React Native + React Native Web) codebase produces:

- **Android app** — EAS build (`npx eas-cli build -p android`)
- **Static web SPA** — `npx expo export --platform web` → `dist/`,
  hostable on Cloudflare Pages, Caddy, or any static server.

SDK 57, Expo Router, strict TypeScript, TanStack Query for all API data.

## Layout

```
frontend/src/
  app/              # Expo Router routes only
    _layout.tsx     # providers: QueryClient, Auth, theme, root Stack
    index.tsx       # auth-aware redirect
    login.tsx
    (app)/          # authenticated group (guard in _layout)
      index.tsx     # role redirect: teacher → dashboard, else → subjects
      subjects.tsx  worksheets.tsx  worksheet.tsx
      write.tsx     # ink canvas over the worksheet page
      attempts.tsx  dashboard.tsx
      admin/        # teacher/admin only (guard in _layout)
        upload.tsx  marking.tsx  review.tsx
  api/              # typed client + DTO types mirroring the DRF serializers
  auth/             # token-store (SecureStore native / AsyncStorage web), store
  offline/          # worksheet bundle download + local manifest
  components/       # ink-canvas.tsx, themed text/view
  constants/  hooks/
```

## Key behaviours

- **Auth**: JWT access/refresh pair; refresh-on-401 handled inside the API
  client. Tokens live in `expo-secure-store` on native, AsyncStorage on
  web. Route groups `(app)` and `(app)/admin` redirect when unauthenticated
  or wrong role.
- **Offline worksheets**: `worksheet.tsx` → *Download for offline* fetches
  the bundle manifest and all page PNGs into `FileSystem` document
  storage; `write.tsx` prefers the local file, falling back to the signed
  URL when online.
- **Ink**: `InkCanvas` uses RN responder events (stylus/finger/pointer on
  all platforms) drawing into `react-native-svg` polylines. Strokes are
  normalised 0–1 and uploaded as vector JSON — the server composites them
  onto page images for review/grading.
- **Teacher upload**: `expo-document-picker` for PDF (rasterised
  server-side) or page images; each file goes straight to S3 via a
  presigned PUT (`expo/fetch` handles `File` bodies on native).

## Config

`EXPO_PUBLIC_API_URL` — API base URL, inlined at build time
(`.env`/`.env.production` or EAS env vars).

## Checks

```bash
npx tsc --noEmit
npx expo lint
npx expo export --platform web   # static-build smoke test
```
