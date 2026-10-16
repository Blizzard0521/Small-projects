# SHIELD-API

**Scalable Hybrid Intelligent Engine for Layered Defence of APIs**

SHIELD-API is a prototype API security gateway that protects REST and GraphQL endpoints with several defence layers working together. It combines fixed rules (bot fingerprinting, authentication, GraphQL depth limits) with an anomaly score based on machine learning that also adjusts the rate limiter as it goes. This prototype was a group assignment for our Computer Intrusion Detection module where I was in charge of the development of this prototype.

The project has three parts:

| Component | File | Purpose |
|---|---|---|
| Live gateway | [`app.py`](app.py) | A FastAPI server whose middleware runs every request through the defence layers |
| Attack simulator | [`attack_sim.py`](attack_sim.py) | Sends legitimate and malicious traffic to the running gateway to show each layer working |
| ML evaluation | [`simulate.py`](simulate.py) | Builds 100,000 synthetic requests, trains an Isolation Forest and reports detection metrics |

> **Status:** Research / academic prototype. Several pieces of infrastructure (Redis, JA3 TLS fingerprinting, JWT validation) are simulated in memory. See [Limitations](#limitations).

---

## Table of Contents

- [Architecture](#architecture)
- [Defence Layers](#defence-layers)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Response Headers](#response-headers)
- [Running the Attack Simulation](#running-the-attack-simulation)
- [ML Model Evaluation](#ml-model-evaluation)
- [Results](#results)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Roadmap](#roadmap)

---

## Architecture

Every incoming request passes through the `shield_api_middleware` gate before it reaches an endpoint. The first layer that rejects a request returns an error straight away, and the response names the layer that blocked it.

```
                 ┌──────────────────────────────────────────────┐
  Request ─────▶ │ L0 / L5  Edge Filter & Bot Fingerprinting    │──▶ 403
                 ├──────────────────────────────────────────────┤
                 │ L1       Authentication Gate                 │──▶ 401
                 ├──────────────────────────────────────────────┤
                 │ L3       ML Anomaly Detector (score 0–1)     │──▶ 403
                 ├──────────────────────────────────────────────┤
                 │ L2       Adaptive Rate Limiter               │──▶ 429
                 │          (bucket shrinks when score > 0.5)   │
                 └──────────────────────────────────────────────┘
                                      │
                                      ▼
                 ┌──────────────────────────────────────────────┐
                 │ Endpoint  (/graphql also applies L4:         │──▶ 400 / 403
                 │           introspection + depth limiting)    │
                 └──────────────────────────────────────────────┘
                                      │
                                      ▼
                   Response + X-SHIELD-* security headers
```

Layer 3 runs **before** Layer 2 on purpose. The anomaly score is computed first so that the rate limiter can tighten its limit for suspicious clients.

---

## Defence Layers

### Layer 0 & 5: Edge Filter and Bot Fingerprinting
The gateway hashes the `User-Agent` header with MD5 and checks it against a set of known malicious fingerprints. This stands in for JA3 TLS fingerprint matching.

- Known bad fingerprint (prototype): `Scrapy/2.11.0`
- Result on match: **HTTP 403**

### Layer 1: Authentication Gate
Every endpoint except the public ones needs an `Authorization` header.

- Public endpoints: `/api/login`, `/health`, `/docs`, `/openapi.json`
- Result when the header is missing: **HTTP 401**

### Layer 3: ML Anomaly Detector
This layer gives each request an anomaly score between `0.0` and `1.0`. The live gateway uses a lightweight heuristic that copies the patterns the Isolation Forest learns in `simulate.py`:

| Signal | Score contribution |
|---|---|
| Base score (all traffic) | +0.1 |
| Client request count > 15 | +0.5 |
| Scripting User-Agent (`python-requests/2.31.0`) | +0.6 |
| GraphQL request with depth > 5 | +0.7 |

The total is capped at `1.0`.

- Block threshold: score **> 0.75**, which returns **HTTP 403**

### Layer 2: Adaptive Rate Limiter
This is a per-IP request counter. It is backed by an in-memory dictionary that stands in for Redis. The limit changes with the Layer 3 score:

| Anomaly score | Request limit |
|---|---|
| ≤ 0.50 | 100 |
| > 0.50 | 20 |

- Result when the limit is exceeded: **HTTP 429**

### Layer 4: GraphQL Protection
These checks run inside the `/graphql` endpoint:

1. **Introspection blocking:** a query containing `__schema` or `__type` is rejected with **HTTP 403**.
2. **Query depth limiting:** the endpoint counts nested `{ }` levels, and a query deeper than **5** is rejected with **HTTP 400**.

---

## Getting Started

### Prerequisites
- Python 3.9+

### Installation

```bash
cd SHIELD-API
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install fastapi uvicorn pydantic httpx pandas numpy scikit-learn faker
```

### Run the Gateway

```bash
uvicorn app:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Health check. Returns status and version. |
| `POST` | `/api/login` | Public | Simulated login. Returns a demo token. |
| `GET` | `/api/products` | Required | Returns a sample product list. |
| `GET` | `/api/user/{user_id}` | Required | Returns sample data for one user. |
| `POST` | `/graphql` | Required | GraphQL endpoint protected by Layer 4. |

### Examples

**Login**
```bash
curl -X POST http://127.0.0.1:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

**Authenticated request**
```bash
curl http://127.0.0.1:8000/api/products \
  -H "Authorization: Bearer <token>"
```

**GraphQL query**
```bash
curl -X POST http://127.0.0.1:8000/graphql \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ user { orders { id } } }"}'
```

### Error Responses

Every block returns a JSON body that names the layer responsible:

```json
{ "error": "Blocked at Layer 5: Known malicious bot fingerprint" }
```

| Status | Layer | Meaning |
|---|---|---|
| `401` | L1 | Missing `Authorization` header |
| `403` | L5 | Known malicious bot fingerprint |
| `403` | L3 | Anomaly score exceeds 0.75 |
| `429` | L2 | Adaptive rate limit exceeded |
| `400` | L4 | GraphQL query depth exceeds 5 |
| `403` | L4 | GraphQL introspection attempted |

---

## Response Headers

The gateway adds these headers to every request that gets through:

| Header | Example | Description |
|---|---|---|
| `X-SHIELD-Score` | `0.1` | The request's anomaly score from Layer 3 |
| `X-SHIELD-Layers` | `L0_Edge, L5_Bot, L1_Auth, L3_ML, L2_RateLimiter` | The layers the request passed |
| `X-SHIELD-Latency` | `1.42ms` | Processing time inside the gateway |

---

## Running the Attack Simulation

Start the gateway first. Then run this in a second terminal:

```bash
python attack_sim.py
```

The script runs four scenarios in order:

| # | Scenario | Technique | Expected Outcome |
|---|---|---|---|
| 1 | Legitimate user | Browser User-Agent with a valid auth header | **HTTP 200**, low anomaly score |
| 2 | Web scraper | `Scrapy/2.11.0` User-Agent | **HTTP 403**, blocked at Layer 5 |
| 3 | GraphQL deep query | Nested query of depth 7 | **HTTP 400**, blocked at Layer 4 |
| 4 | Credential stuffing | Rapid burst of logins with a `python-requests` User-Agent | **HTTP 403**, blocked at Layer 3 once the request count passes 15 |

> **Note:** Rate-limit counters live in memory and never reset. All simulated clients share `127.0.0.1`, so restart the server between runs to get the same results each time.

---

## ML Model Evaluation

[`simulate.py`](simulate.py) checks how well the anomaly detection approach works on a large synthetic dataset.

### Dataset

The script generates 100,000 labelled requests with a fixed random seed (`42`), so every run produces the same data:

| Traffic Class | Count | Share |
|---|---|---|
| Legitimate | 80,000 | 80% |
| Web scraper | 7,000 | 7% |
| Credential stuffer | 5,000 | 5% |
| GraphQL attacker | 4,000 | 4% |
| DDoS bot | 4,000 | 4% |

### Features (13)

| Feature | Description |
|---|---|
| `request_rate` | Requests per minute |
| `payload_size_zscore` | How far the payload size is from normal |
| `method_ratio` | Share of GET requests vs POST requests |
| `endpoint_entropy` | How many different endpoints the client visits |
| `time_of_day_score` | How unusual the request time is |
| `geo_velocity` | Signs of physically impossible location changes |
| `ua_consistency` | How stable the User-Agent is |
| `jwt_claim_anomaly` | Signs of a forged or tampered token |
| `response_code_ratio` | Share of successful (2xx) responses |
| `graphql_depth` | Normalised GraphQL query depth |
| `graphql_complexity` | Normalised GraphQL query cost |
| `ja3_risk_score` | Risk level of the TLS fingerprint |
| `session_idle_time` | Pause between consecutive requests |

### Methodology

1. **Model:** scikit-learn `IsolationForest` (`n_estimators=100`, `contamination=0.07`, `random_state=42`).
2. **Training:** the model learns from legitimate traffic only. This is unsupervised novelty detection: it learns what normal traffic looks like and flags anything that departs from it.
3. **Scoring:** the model scores all 100,000 requests. The script reverses the raw decision scores so higher means more anomalous, then scales them to the range `[0, 1]` with `MinMaxScaler`.
4. **Thresholding:** requests scoring **> 0.75** are classified as attacks. This matches the Layer 3 threshold in the live gateway.

### Run

```bash
python simulate.py
```

Outputs:
- **`results.csv`**: all 100,000 requests with their features, the true label, the anomaly score, the predicted label and a simulated latency
- **`metrics.json`**: a summary of the evaluation metrics

---

## Results

Evaluation results from [`metrics.json`](metrics.json):

| Metric | Value |
|---|---|
| Detection Rate (Recall) | **94.8%** |
| False Positive Rate | **0.0%** (4 of 80,000) |
| Precision | **100.0%** |
| F1-Score | **0.973** |
| AUC-ROC | **1.000** |

### Confusion Matrix

|  | Predicted Normal | Predicted Attack |
|---|---|---|
| **Actual Normal** | TN = 79,996 | FP = 4 |
| **Actual Attack** | FN = 1,044 | TP = 18,956 |

> These figures come from **synthetic** data in which the attack classes are well separated from normal traffic. Real-world traffic is noisier, so expect lower performance in production.

---

## Project Structure

```
SHIELD-API/
├── app.py           # FastAPI gateway with the layered security middleware
├── attack_sim.py    # Async attack scenarios that target the live gateway
├── simulate.py      # Synthetic data generation, Isolation Forest training and evaluation
├── results.csv      # Per-request evaluation output (100,000 rows)
├── metrics.json     # Summary evaluation metrics
└── README.md
```

---

## Limitations

SHIELD-API is a prototype. The following simplifications apply:

| Area | Prototype Behaviour | Production Equivalent |
|---|---|---|
| Rate-limit store | Python dictionary in memory, no expiry window | Redis cluster with sliding or token-bucket windows |
| Bot fingerprinting | MD5 hash of the User-Agent | JA3/JA4 TLS fingerprints |
| Authentication | Checks only that an `Authorization` header is present | JWT signature, expiry and claims validation |
| Anomaly detection | Hand-tuned heuristic rules | The trained Isolation Forest, served for live inference |
| GraphQL depth | Counts `{ }` nesting levels | AST-based depth and cost analysis |
| Login | Hardcoded demo credentials | Credential store with hashed passwords |
| Latency in `results.csv` | Random values (4–11 ms) | Measured gateway latency |

Additional notes:
- The Layer 3 GraphQL heuristic never receives the query depth, so it never fires. GraphQL depth attacks are currently stopped by Layer 4 alone.
- Request counters never decrease. Once a client reaches the limit, it stays blocked until the server restarts.

---

## Roadmap

- [ ] Serve the trained Isolation Forest model from the middleware for live scoring
- [ ] Replace the in-memory store with Redis and add time-windowed rate limiting
- [ ] Implement real JWT validation
- [ ] Add JA3/JA4 TLS fingerprinting at the edge
- [ ] Use an AST-based GraphQL depth and complexity analyser
- [ ] Add a `requirements.txt` and automated tests
- [ ] Build a dashboard to visualise `results.csv` (score distribution, ROC curve, latency)
