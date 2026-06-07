# Agora — Mega Roadmap (v2.0)

> **Verzia:** 2.0.0
> **Dátum:** 2026-06-07
> **Status:** Plán

---

## Prehľad

Tento roadmap definuje upgrade Agory z **0.1.0 (dungeon playground)** na **1.0.0 (production-ready multi-agent platform)**. Rozdelený na 4 fázy, každá s jasným míľnikom.

---

## Legenda

| Skratka | Význam |
|:--------|:--------|
| 🟢 **Hotovo** | Implementované (Phase 0–IIIb + God Console v2) |
| 🔵 **Fáza 1** | Foundation Upgrade — production infra |
| 🟡 **Fáza 2** | Trust & Consensus — ESS/TFT plný výkon |
| 🔴 **Fáza 3** | Agent Ecosystem — sandbox, routing, lifecycle |
| 🟣 **Fáza 4** | Interface & Deployment — dashboard v3, auth, CI/CD |

---

## 🟢 CURRENT STATE (čo už máme)

### Layer 5 — Interface ✅
- God Console 2.0 (5 tabov: Agent Mgmt, Byzantine, Agent OS, Controller, Health)
- REST API (FastAPI, ~30 endpointov)
- WebSocket (event stream)
- Dashboard (trust, energy, economy, system health)
- Game (Phaser 3 dungeon, minimapa, HUD)

### Layer 4 — Orchestration ✅
- Controller (room cluster dispatcher, ProcessPoolExecutor, 4 workers)
- Epoch engine (lifecycle/batches)
- Task executor (task pipeline)
- Economy engine (resources, trade offers, auto-trade)

### Layer 3 — Agent Logic ✅
- Agent OS (body, brain, soul, abilities, skills)
- Physical World (movement, help-seeking, pending moves)
- ETCSLV Harness (Execution, Tool Registry, Context, State Store, Lifecycle Hooks, Validation)
- Agent lifecycle (death detection, energy replenish)

### Layer 2 — Consensus & Trust ⚠️
- ESS Engine (basic — trust scores exist)
- Stigmergy Processor (traces, alerts, best-agent selection)
- **TFT Verifier ✅** (Tit-for-Tat: nice/retaliatory/forgiving/clear detectors, 30% blend into trust)

### Layer 1 — Storage ⚠️
- Redis (geo queries, NPC positions — funguje)
- **PostgreSQL ✅** (SQLAlchemy 2.0 + Alembic, Docker Compose)
- **S3/MinIO — CHYBAJÚCI**
- **Firecracker microVM — CHYBAJÚCI**
- **Alembic migrations ✅** (001 baseline + 002 TFT interaction_log)

---

## 🔵 FÁZA 1: Foundation Upgrade

> *Cieľ: produkčná infraštruktúra, ktorá unesie 100+ agentov*

### 1.1 PostgreSQL + Alembic

```yaml
Migrácia:    SQLite → PostgreSQL 16
ORM:         SQLAlchemy 2.0 async + asyncpg
Migrations:  Alembic (baseline + versioned)
Pool:        connection pool (min=5, max=20)
```

**Čo treba spraviť:**
- [x] Prepísať `storage/connection.py` na asyncpg namiesto aiosqlite
- [x] Vytvoriť Alembic baseline migráciu z aktuálneho SQLite schema
- [x] Nahradiť všetky `cursor = await db.execute(...)` SQLAlchemy Core/ORM volaniami
- [x] Pridať `AGORA_DATABASE_URL` podporu pre `postgresql+asyncpg://`
- [ ] Migration skript: SQLite → PostgreSQL data export
- [x] Pridať Docker Compose pre PostgreSQL službu

### 1.2 Redis Production Ready

```yaml
Aktuálne:    len geo NPC positions
Cieľ:        cache + pub/sub + rate limiting + session store
```

- [ ] Redis pub/sub pre notifikácie namiesto broadcast v main.py
- [ ] Cache layer pre časté DB dopyty (agent list, trust scores)
- [ ] Rate limiting pre API endpointy
- [ ] Session store pre WebSocket spojenia

### 1.3 S3/MinIO Artifact Storage

- [ ] MinIO v Docker Compose
- [ ] Upload endpoint: `/api/v1/artifacts/upload`
- [ ] Download endpoint: `/api/v1/artifacts/{id}/download`
- [ ] Artifact lifecycle (TTL, cleanup)

### 1.4 Performance Baseline

- [ ] Load test (100 concurrent agents, 1000 ticks)
- [ ] Profiling (cProfile + py-spy)
- [ ] Connection pooling tuning
- [ ] Query optimalizácia (indexy, N+1 eliminácia)
- [ ] Async všade — žiadne blokujúce volania

---

## 🟡 FÁZA 2: Trust & Consensus Engine

> *Cieľ: dôveryhodná multi-agent kolaborácia s matematickým základom*

### 2.1 ESS Engine v2 — EigenTrust Similarity Scoring

```python
# Aktuálne: jednoduchý trust_score update
trust = min(1.0, max(0.0, current + delta))

# Cieľ: plný EigenTrust algoritmus
def eigenvector_centrality(
    trust_matrix: np.ndarray,  # NxN directed trust
    damping: float = 0.85,
    iterations: int = 100,
) -> np.ndarray:
    """Globálne trust skóre = dominantný eigenvektor."""
```

- [ ] Matica dôvery (N×N medzi všetkými agentmi)
- [ ] Iteratívny výpočet: `t^(k+1) = (1-d)·e + d·C·t^(k)`
- [ ] Normalizácia na [0, 1] pre každý riadok
- [ ] Per-epoch recompute (na konci každej epochy)
- [ ] API endpoint: `/api/v1/trust/matrix` — kompletná trust heatmap
- [ ] Vizualizácia v God Console: trust graf (nodes=agents, edges=trust)

### 2.2 TFT Verifier — Tit-for-Tat

```python
# Tit-for-Tat protocol:
# 1. NICE: vždy cooperates na prvý ťah
# 2. RETALIATORY: vracia defection
# 3. FORGIVING: po cooperácii odpúšťa
# 4. CLEAR: správanie je predvídateľné

class TFTVerifier:
    def evaluate(
        interaction_history: list[tuple[agent, agent, outcome]]
    ) -> dict:
        """Vráti nice/retaliatory/forgiving/clear scores."""
```

- [x] Interakčný log (kto s kým, kedy, výsledok)
- [x] Nice detector: prvý ťah vždy cooperate?
- [x] Retaliatory detector: defection → defection response?
- [x] Forgiving detector: po cooperácii reset?
- [x] Clear detector: konzistentné správanie?
- [x] TFT skóre = funkcia 4 dimenzií
- [x] Weighting do ESS trust skóre (30% TFT, 70% výsledky)
- [x] API: `/api/v1/trust/tft/{agent_id}`

### 2.3 Stigmergy Processor v2

- [ ] Pridanie decay funkcie (exponenciálny, nie lineárny TTL)
- [ ] Trace aggregation (podobné traces → summary)
- [ ] Anomaly detection (trace pattern odchýlky)
- [ ] Cross-agent trace correlation

---

## 🔴 FÁZA 3: Agent Ecosystem

> *Cieľ: sandboxovaní, multi-model, auto-škálujúci sa agenti*

### 3.1 Firecracker MicroVM Sandbox

```yaml
Runtime:     Firecracker 1.8+
Kernel:      custom 5.10+ (minimal)
RootFS:      Alpine Linux (10MB)
Interface:   API → spawn microVM → execute code → return result → destroy
```

- [ ] Firecracker SDK/integrácia (Python `aiomonitor` alebo `firecracker-py`)
- [ ] Kernel + rootFS build script (`scripts/firecracker_setup.sh`)
- [ ] Agent sandbox pool (min 2, max 10 microVMs)
- [ ] Task → microVM dispatch (task executor → sandbox)
- [ ] 60s max execution, potom force-kill
- [ ] Network isolation (dedicated bridge `agora-fcbr0`)
- [ ] Stderr/stdout capture → result dict
- [ ] Fallback: in-process execution ak sandbox nie je dostupný

### 3.2 Multi-Model LLM Router

```yaml
Tiers:
  cheap:    deepseek-v4-flash      (rýchle, lacné)
  medium:   deepseek-v4-chat       (vyvážené)
  expert:   claude-sonnet-4        (najlepšie)

Routing:
  per-agent:        AGENT_LLM_TIER config
  per-task:         task complexity → model
  fallback:         cheap → medium → expert pri chybe
```

- [ ] Model router (`execution/model_router.py`)
- [ ] Provider abstraction (OpenAI-compatible API)
- [ ] Per-agent model tier config
- [ ] Auto-fallback (ak expert padne → medium)
- [ ] Rate limiting (RPM per tier)
- [ ] Token counting a cost tracking

### 3.3 Agent Auto-Scaling

- [ ] Agent spawner (detekcia loadu → noví agenti)
- [ ] Agent death/deprecation (trust < 0.1 → cleanup)
- [ ] Role balancer (rovnomerné rozloženie rolí)
- [ ] Auto-recovery (mŕtvi agenti → respawn)
- [ ] Agent genetics (genome mutácie pri nových agentoch)

### 3.4 Agent OS v3 — Deep Learning

```yaml
Aktuálne:    rule-based state_of_mind (health, stamina, fatigue)
Cieľ:        LLM-driven decisions + memory consolidation
```

- [ ] LLM-driven think (namiesto `if health < 20: panicked`)
- [ ] Memory consolidation (short-term → long-term → archive)
- [ ] Reflection (pravidelná sebareflexia)
- [ ] Planning (multi-step plány, nie single goal)
- [ ] Personality drift (archetype sa mení podľa skúseností)

---

## 🟣 FÁZA 4: Interface & Deployment

> *Cieľ: produkčný deployment s monitoringom, authom a CI/CD*

### 4.1 Authentication & AuthZ

- [ ] JWT tokenová autentifikácia
- [ ] API key pre machine-to-machine
- [ ] RBAC (admin, operator, viewer)
- [ ] Rate limiting per API key
- [ ] Audit log (kto čo kedy spravil)

### 4.2 WebSocket v2 — Event System

```yaml
Aktuálne:    jeden /ws endpoint, broadcast všetkým
Cieľ:        topic-based pub/sub cez Redis
```

- [ ] Redis pub/sub channels per topic
- [ ] Topicy: `agent:{id}`, `room:{name}`, `system`, `epoch`
- [ ] Subscribe/unsubscribe per WebSocket spojenie
- [ ] Event replay (pripoj sa → dostaneš posledných N eventov)
- [ ] Event persistence v PostgreSQL

### 4.3 God Console v3 — Real-Time

- [ ] WebSocket-based live update (namiesto 10s pollingu)
- [ ] Agent timeline (každý krok agenta vizuálne)
- [ ] Trust graph (interaktívny force-directed graph)
- [ ] Byzantine violations timeline (graf v čase)
- [ ] Room heatmap (NPC pozície, movement trajectories)
- [ ] Mobile-responsive layout

### 4.4 Game Client v2

- [ ] Phaser 3 → WebGL 3D prechod
- [ ] Online multiplayer (viac hráčov v dungeon)
- [ ] Player agent (player = agent s God powers)
- [ ] Dungeon editor (drag & drop miestností, NPC spawn)

### 4.5 CI/CD & Deployment

```yaml
Build:       GitHub Actions + Docker buildx
Registry:    ghcr.io/dancenitra/agora
Deploy:      Render / Fly.io / self-hosted
```

- [ ] Multi-stage Dockerfile (Python + Node + Nginx)
- [ ] Docker Compose (Postgres + Redis + MinIO + API + frontend)
- [ ] CI pipeline: lint → test → build → push
- [ ] CD pipeline: auto-deploy na main commit
- [ ] Health checks + auto-restart
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Log aggregation (Loki or similar)

### 4.6 Documentation

- [ ] API doc (OpenAPI/Swagger — už je auto-generated)
- [ ] Architecture doc (update ARCHITECTURE.md)
- [ ] Deployment guide
- [ ] Developer onboarding (`CONTRIBUTING.md`)
- [ ] Video demo (screen recording)

---

## 📊 Prioritizácia

### Podľa hodnoty (ROI)

| # | Feature | Effort | Impact | ROI |
|---|---------|--------|--------|-----|
| 1 | PostgreSQL + Alembic | 3 dni | 🟢🟢🟢 | **9** |
| 2 | WebSocket Event System | 2 dni | 🟢🟢🟢 | **9** |
| 3 | TFT Verifier | 1 deň | 🟢🟢 | **8** |
| 4 | ESS Engine v2 | 2 dni | 🟢🟢 | **8** |
| 5 | Auth + API keys | 2 dni | 🟢🟢 | **8** |
| 6 | Multi-Model Router | 1 deň | 🟢🟢 | **8** |
| 7 | God Console v3 (WebSocket) | 3 dni | 🟢🟢 | **7** |
| 8 | Agent OS v3 (LLM think) | 3 dni | 🟢🟢 | **7** |
| 9 | CI/CD pipeline | 2 dni | 🟢🟢 | **6** |
| 10 | Firecracker Sandbox | 5 dní | 🟢 | **5** |
| 11 | S3/MinIO Artifacts | 1 deň | 🟢 | **4** |
| 12 | Agent Auto-Scaling | 3 dni | 🟢 | **4** |

### Odporúčaný order

```
Týždeň 1:  PostgreSQL + TFT Verifier + WebSocket Event System
Týždeň 2:  ESS v2 + Auth + Multi-Model Router
Týždeň 3:  God Console v3 (WebSocket live) + Agent OS v3 (LLM think)
Týždeň 4:  CI/CD + Firecracker + Agent Auto-Scaling + Documentation
```

---

## 📈 Metriky úspechu

| Metrika | Aktuálne | Cieľ |
|:--------|:---------|:-----|
| Max agentov | 30 | **500+** |
| Ticks per second | ~1 (5s interval) | **10+** |
| LLM volania parallel | 2 | **všetci agenti** |
| Databáza | SQLite (1 writer) | **PostgreSQL (100+ conn)** |
| Agent isolation | None | **Firecracker microVM** |
| Trust algoritmus | Simple | **EigenTrust + TFT** |
| Deployment | Manual | **Auto CI/CD** |
| Monitoring | None | **Prometheus + Grafana** |
| Auth | None | **JWT + API keys + RBAC** |

---

## 📝 Poznámky

- **SQLite → PostgreSQL:** Toto je **najkritickejší upgrade**. SQLite nepodporuje concurrent writes — už pri 10 agentoch je to bottleneck. PostgreSQL + asyncpg = 100+ concurrent connections.
- **TFT Verifier:** Malý kód (1 deň), obrovský impact na trust system. TFT je overený v game theory (Axelrod tournament winner).
- **Firecracker:** Najväčší effort (5+ dní) ale najväčší bezpečnostný upgrade. Odložený na koniec — kým nemáme 500 agentov v produkcii, sandbox nie je kritický.
- **ESS v2:** EigenTrust je matematicky krásny, ale pre <50 agentov nemá výrazne lepšie výsledky ako jednoduchý trust update. Priorita po PostgreSQL.

---

*Planované: 2026-06-07 → 2026-07-05 (4 týždne)*
