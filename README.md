# TP2 DevOps avancé — catalog-api

Microservice FastAPI + CI/CD sécurisée (SonarQube, Trivy, OPA Gatekeeper) + GitOps (ArgoCD)
+ observabilité (OpenTelemetry, Prometheus, Grafana, Loki, Tempo) + SRE (k6, SLO, burn rate).

| Dossier | Contenu |
|---|---|
| `app/` | API : `/products`, `/products/{id}`, `/checkout` (lent), `/flaky` (erreurs), `/metrics`, `/health` |
| `tests/` | Tests pytest (couverture ≥ 85 %, rapport Cobertura `coverage.xml`) |
| `Dockerfile` | Image multi-stage, utilisateur non-root |
| `.github/workflows/ci-cd.yml` | Lint & Test → SonarQube + Quality Gate → Build → Trivy → Push → mise à jour GitOps |
| `charts/catalog-api/` | Chart Helm déployé par ArgoCD |
| `argocd/application.yaml` | Application ArgoCD (sync automatique) |
| `gatekeeper/` | ConstraintTemplates Rego + Constraints (pas de `latest`, resources obligatoires) |
| `k8s/non-compliant/` | Manifestes de démo (rejeté / accepté) |
| `observability/` | Values Helm (Prometheus/Grafana/Alertmanager, Loki, Tempo, OTel Collector), règles SLO, dashboard |
| `k6/load-test.js` | Ramp-up 100 VU, stress 500 VU, spike 1500 VU |
| `demo/bad-pr/` | Code volontairement mauvais pour faire échouer la Quality Gate |
| `kind/kind-config.yaml` | Cluster Kind avec ports 8080 (API) et 3000 (Grafana) |

## Démarrage rapide (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                      # tests + couverture
uvicorn app.main:app --reload
```

## Tester les règles SLO sans cluster

```bash
promtool test rules observability/tests/slo-rules-test.yml
```
