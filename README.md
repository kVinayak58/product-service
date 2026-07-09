# Product Service

ShopEasy product catalog API — **golden-path** microservice repository.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/products` | List products |

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
flask run
```

## CI/CD

This is a **standalone Git repository**. The `Jenkinsfile` calls `platform-shared-library` and checks out `helm-charts` + `platform-config` at build time via `checkoutPlatformDeps()`.

Promotion flow: Dev → QA → UAT → Prod using the **same image digest** (BOMP).

## Related repos

| Repo | Role |
|------|------|
| `platform-shared-library` | Pipeline steps (`dockerBuild`, `trivyScan`, `deployHelm`, …) |
| `helm-charts` | Kubernetes chart + environment values |
| `platform-config` | Gitleaks, SonarQube, Checkov policies |
