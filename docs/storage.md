# Storage

All user media lives in an S3-compatible bucket; the API never proxies
file bytes.

## Recommended: Cloudflare R2

- 10 GB storage free, **zero egress fees** (worksheet PNGs are downloaded
  by every student — egress is the usual S3 bill-killer).
- S3-compatible API; credentials from the R2 dashboard → env vars
  `AWS_S3_ENDPOINT_URL` (`https://<account>.r2.cloudflarestorage.com`),
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`,
  `AWS_S3_REGION_NAME=auto`.

Alternatives: Backblaze B2, MinIO (self-host on the VPS), any S3 clone.

## Key layout

```
worksheets/{worksheet_id}/worksheet-pages/<uuid>.<ext>   page PNGs
worksheets/{worksheet_id}/pdfs/<uuid>.pdf                source PDFs
worksheets/{worksheet_id}/answer-sheets/<uuid>.<ext>     answer keys
attempts/{attempt_id}/pages/{page_id}/strokes.json       student ink vectors
attempts/{attempt_id}/pages/{order}/composite.png        ink composited onto page
```

## Presigned URLs

- `storage.presign_put(key, content_type)` — short-lived PUT for
  teacher/student uploads (default 15 min).
- `storage.presign_get(key)` — short-lived GET embedded in bundle
  manifests and `PageSubmission.url` for review.
- `storage.put_bytes` / `get_bytes` — server-side (stroke JSON, composite
  renders).

Because downloads are signed rather than public, the bucket can stay
private; URLs expiring just means refetching the manifest.
