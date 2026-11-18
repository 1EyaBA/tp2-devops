"""API REST de catalogue produit — TP2 DevOps avancé."""

import asyncio
import os
import random
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from app import catalog
from app.telemetry import setup_logging, setup_telemetry

app = FastAPI(title="Catalog API", version="1.1.0")
logger = setup_logging()
setup_telemetry(app)

# ---------- Métriques Prometheus (méthode RED) ----------
REQUESTS = Counter(
    "http_requests_total",
    "Nombre total de requêtes HTTP",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Durée des requêtes HTTP en secondes",
    ["method", "path"],
    # 0.2 s est présent pour pouvoir mesurer le SLO de latence (p95 <= 200 ms)
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0),
)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        # On utilise le template de route (/products/{product_id}) pour limiter la cardinalité
        path = route.path if route is not None else "unmatched"
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(duration)
            logger.info(
                "requête traitée",
                extra={
                    "path": path,
                    "method": request.method,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                },
            )


# ---------- Modèles ----------
class CartItem(BaseModel):
    product_id: int
    quantity: int


class CheckoutRequest(BaseModel):
    items: list[CartItem] = Field(default_factory=list)


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/products")
def get_products():
    return [p.__dict__ for p in catalog.list_products()]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    try:
        return catalog.get_product(product_id).__dict__
    except catalog.ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/checkout")
async def checkout(order: CheckoutRequest):
    """Traitement lent simulé : 30-150 ms en général, parfois 300-800 ms."""
    slow_prob = _env_float("CHECKOUT_SLOW_PROB", 0.05)
    min_ms = _env_float("CHECKOUT_MIN_MS", 30)
    max_ms = _env_float("CHECKOUT_MAX_MS", 150)
    if random.random() < slow_prob:  # NOSONAR - aléatoire non cryptographique, simulation
        delay_ms = random.uniform(300, 800)  # NOSONAR
    else:
        delay_ms = random.uniform(min_ms, max_ms)  # NOSONAR
    await asyncio.sleep(delay_ms / 1000)

    try:
        total = catalog.compute_total([(i.product_id, i.quantity) for i in order.items])
    except catalog.ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (catalog.InvalidQuantityError, catalog.OutOfStockError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "confirmed", "total": total, "processing_ms": round(delay_ms, 1)}


@app.get("/flaky")
def flaky():
    """Renvoie une erreur 500 avec une probabilité FLAKY_ERROR_RATE (défaut 20 %)."""
    error_rate = _env_float("FLAKY_ERROR_RATE", 0.2)
    if random.random() < error_rate:  # NOSONAR - simulation d'erreurs
        logger.error("erreur intermittente simulée", extra={"path": "/flaky"})
        raise HTTPException(status_code=500, detail="Erreur intermittente simulée")
    return {"status": "ok"}
