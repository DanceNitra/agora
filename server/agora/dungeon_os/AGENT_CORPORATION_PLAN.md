# 🏢 Autonomous Agent Corporation — Architektúra a Plán

> **Vízia:** Samo-sa-zlepšujúci ekosystém agentov, ktorí ako firma spoločne výskumajú, navrhujú, implementujú a komunikujú vylepšenia systému. Každý quest má *HEAD* (výskum) a *PATA* (realizácia).

---

## 📋 Prehľad: Ako to funguje

*Inšpirované Compound Engineering: 80/20 planning-to-execution, paralelné subagenty, STRATEGY.md north star, adversariálne filtrovanie, compound learning loop.*

```
┌─────────────────────────────────────────────────┐
│                  CRON (15 min)                   │
│  Celý cyklus ─ každých 15 minút tickne           │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  📜 STRATEGY.md (North Star)                    │
│  Definuje: core problém, target persona,        │
│  kľúčové metriky, technický smer               │
│  → Všetci agenti z neho čítajú                  │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  👁️  SCOUT skenuje horizont (1 min)             │
│  GitHub trending, Phaser releases, blogy        │
│  → Nájdená téma → Quest HEAD                   │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  🔬 RESEARCH (3x paralelne — 8 min)             │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ repo-research │ │ docs-    │ │ best-        │ │
│  │ -analyst     │ │researcher│ │practices-    │ │
│  │              │ │          │ │researcher    │ │
│  └──────────────┘ └──────────┘ └──────────────┘ │
│  → Syntéza do findings.md                       │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  🧠 BRAINMASTER → Vault                         │
│  Štruktúruje, ukladá, spája s existujúcim       │
│  know-how → Design proposal                     │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  ⚔️  ADVERSARIAL FILTERING                       │
│  Agenti navzájom kritizujú proposal             │
│  Slabé nápady odpadnú skôr ako sa dostanú       │
│  k exekúcii                                      │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  👔 CTO + CEO evaluation                        │
│  "Toto implementujeme. Priorita: HIGH/MEDIUM"   │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  🛠️  PATA FÁZA — EXEKÚCIA (20% času)            │
│  Designer/Developer → QA (multi-review)         │
│  → Writer → Compound (lessons learned)          │
│  → Systém je lepší ako pred 15 minútami         │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  📚 COMPOUND (retrospective)                    │
│  Extrahuje inžinierske lekcie, bug patterny,    │
│  architektonické guideliney                     │
│  → Zapisuje do MEMORY.md / AGENTS.md            │
│  → Systém je permanentne múdrejší               │
└─────────────────────────────────────────────────┘
```

---

## 👥 Agent Roles (The Corporation)

### Executive Layer (Strategic)

| Agent | Role | Zodpovednosť |
|:------|:-----|:-------------|
| **CEO** | Chief Executive Officer | Vízia, priority, finálne schválenia, trhové smerovanie. Hovorí "toto budeme robiť". |
| **CTO** | Chief Technology Officer | Architektúra, tech stack, kvalita kódu, rozhoduje AKO. Garantuje že riešenie je technicky správne. |

### Research Layer (Knowledge)

| Agent | Role | Zodpovednosť |
|:------|:-----|:-------------|
| **Scout** | Horizon Scanner | Skenuje GitHub, Phaser releases, Hacker News, arXiv, blogy. Hľadá čo je nové a relevantné. |
| **Researcher** | Deep Diver | Číta reálne zdroje (nie generuje). GitHub kód, dokumentácia, API reference. Syntetizuje. |
| **Brainmaster** | Knowledge Engineer | Ukladá poznatky do vaultu, udržiava knowledge graph, spája koncepty. Vault = firemné know-how. |

### Creative Layer (Design)

| Agent | Role | Zodpovednosť |
|:------|:-----|:-------------|
| **Designer** | UI/UX + Game Design | Vizuály, UI komponenty, shadery, animácie, herný dizajn, konzistentný vizuálny jazyk. |
| **Writer** | Technical Writer | Dokumentácia, changelogy, architektonické rozhodnutia (ADR), user guides. |

### Execution Layer (Engineering)

| Agent | Role | Zodpovednosť |
|:------|:-----|:-------------|
| **Developer** | Builder | Implementuje schválené zmeny: backend, frontend, Phaser hra. Píše produkčný kód. |
| **QA** | Validator | Testuje, validačné skripty, kontroluje že zmena spĺňa kritériá. Nedovolí zlému kódu von. |

### Growth Layer (Business)

| Agent | Role | Zodpovednosť |
|:------|:-----|:-------------|
| **Marketer** | Growth Strategist | Positioning, content strategy, value proposition, use casey. Čo povedať svetu. |
| **Social Agent** | Broadcaster | Posiela na X/Twitter, LinkedIn. Komunikuje progress, features, víziu. Buduje komunitu. |

---

## 🧬 HEAD + PATA — Každý Quest

## HEAD fáza (Hĺbkový Exploratívny AI Research)

HEAD transformuje quest z "chceli by sme" na **"toto presne vieme a máme dôkazy"**.

```
Vstup: "Vylepši Phaser grafiku"
│
│  HEAD FÁZA:
│  ┌─────────────────────────────────────────┐
│  │ 1. SCOUT → Nájde Phaser 4.1.0 release    │
│  │ 2. RESEARCHER → Číta changelog, nové     │
│  │    RenderConfig, Layer GameObject,       │
│  │    Texture mipmap regeneration            │
│  │ 3. BRAINMASTER → Syntéza do vaultu       │
│  │    "Phaser 4.1.0 umožňuje mipmap         │
│  │     regeneráciu na DynamicTexture"        │
│  └─────────────────────────────────────────┘
│
Výstup HEAD: knowledge.md + design-proposal.md
```

## PATA fáza (Praktická Aplikácia a Transformácia Agenty)

PATA aplikuje HEAD poznatky na reálny upgrade systému.

```
HEAD výstup → PATA:
│
│  ┌─────────────────────────────────────────┐
│  │ 4. CTO → "Mipmap regeneration dáva       │
│  │    zmysel pre particle systém"            │
│  │ 5. CEO → "Priorita HIGH, ideme na to"    │
│  │ 6. DESIGNER → Navrhne particle upgrade   │
│  │ 7. DEVELOPER → Implementuje              │
│  │ 8. QA → Validuje, testuje                │
│  │ 9. WRITER → Dokumentuje zmeny            │
│  │ 10. SOCIAL → Píše o vylepšení            │
│  └─────────────────────────────────────────┘
│
Výstup PATA: commit+push + changelog + post
```

---

## 🔄 Recursive Self-Improvement

Systém sa zlepšuje na **3 úrovniach** zároveň:

### Level 1: Direct Improvement
```
Research → Knowledge → Implementation → Upgrade → Research (new topic)
```
Príklad: Scout nájde Phaser 4.1.0 → výskum → implementácia → hra je lepšia

### Level 2: Meta-Improvement (zlepšovanie agentov)
```
Analýza vlastného výkonu → zlepšenie promptov → lepší výskum → lepšie výsledky
```
Príklad: Researcher zistí že jeho výskum je plytký → Brainmaster upraví jeho prompt → nabudúce je hlbší

### Level 3: Recursive Architecture (zlepšovanie samotného zlepšovania)
```
Zlepšiť ako systém zlepšuje → lepšia metodológia → lepší cyklus → exponenciálny rast
```
Príklad: Systém zistí že HEAD fáza je príliš pomalá → vytvorí quest na optimalizáciu research pipeline → nový pipeline je 2x rýchlejší

---

## 📦 Fáza 1: Foundation (Dnes)

**Cieľ:** Spustiť prvý 15-minútový cyklus s HEAD+PATA

### Čo treba spraviť:

1. **Nové quest typy** — každý quest má `head` a `pata` phase v DB
   - `phase: "head"` — research phase
   - `phase: "pata"` — execution phase
   - `research_source` — URL/ref čo sa čítalo
   - `findings_path` — kam sa uložili poznatky

2. **Rozšíriť AgentWorker** — tick spracúva HEAD a PATA questy oddelene
   - HEAD questy → Scout/Researcher/Brainmaster
   - PATA questy → Designer/Developer/QA

3. **Scout action** — `action_scan_horizon()` v hermes.py
   - Volá curl na GitHub API (Phaser releases, trending repos)
   - Vyberie najrelevantnejšiu tému
   - Vytvorí HEAD quest

4. **Researcher action** — `action_deep_research()`
   - Číta URL (GitHub README, docs, changelog)
   - Syntetizuje poznatky: čo je nové, ako to použiť, aký je impact

5. **Brainmaster action** — `action_store_knowledge()`
   - Ukladá do `~/Obsidian Vault/agora-research/`
   - Structured frontmatter: source, date, relevance, subsystem

6. **Cron 15 min** — spustí tick cyklus

### Čo hneď otestujeme:
- Scout nájde niečo na GitHub → vytvorí HEAD quest
- Researcher prečíta → zapíše poznatky
- Brainmaster uloží do vaultu
- CEO/CTO vyhodnotí → buď spustí PATA alebo nie

---

## 📦 Fáza 2: Agent Corporation (Tento týždeň)

1. **Všetkých 10 agent rolí** — každý má:
   - Unikátny systém prompt (personality + expertíza)
   - Action funkciu (reálny tool call)
   - Skill set (čo vie robiť)
   
2. **CEO/CTO evaluácia** — po HEAD fáze automatické vyhodnotenie:
   - Je to technicky zmysluplné? (CTO)
   - Má to business hodnotu? (CEO)
   - Priorita (HIGH/MEDIUM/LOW)
   
3. **Knowledge Vault** — automatická štruktúra:
   - `agora-research/` — HEAD výstupy
   - `agora-proposals/` — design proposals
   - `agora-decisions/` — čo sa schválilo (ADR)
   - `agora-changelog/` — čo sa zmenilo

---

## 📦 Fáza 3: Recursive Loop (Budúci týždeň)

1. **Meta-questy** — systém vytvára questy na zlepšenie seba samého:
   - "Zlepši kvalitu research výstupov"
   - "Optimalizuj 15-minútový cyklus"
   - "Pridaj novú agent rolu ak chýba"
   
2. **Agent skill upgrade** — na základe HEAD/PATA výsledkov:
   - Ak Researcher opakovane dáva slabé výstupy → Brainmaster upraví jeho prompt
   - Ak Developer píše bugy → QA dostane viac právomocí
   
3. **Vault ako firemné know-how** — každý HEAD výstup:
   - Je tagged podľa subsystemu
   - Má trust score (overené výskumom?)
   - Je linkovaný na súvisiace poznatky

---

## 📦 Fáza 4: External Growth (Budúci mesiac)

1. **X/Twitter bot** — Social agent píše:
   - "Dnes náš výskumný tím objavil..."
   - "Nový feature implementovaný..."
   - Budovanie osobnej značky
   
2. **Marketer** — analyzuje:
   - Čo konkurencia robí
   - Aké use casey komunikovať
   - Positioning stratégia
   
3. **Revenue pipeline** — prvé monetizačné experimenty

---

## 🚀 Čo spravím HNEĎ TERAZ

| Krok | Čo | Čas |
|:-----|:---|:---:|
| 1 | Pridám `phase` do quest modelu (HEAD/PATA) | 5 min |
| 2 | Scout action — skenuje GitHub Phaser releases | 5 min |
| 3 | Researcher action — číta URL, syntetizuje | 5 min |
| 4 | Brainmaster action — ukladá do vaultu | 5 min |
| 5 | CEO/CTO evaluácia po HEAD fáze | 5 min |
| 6 | Cron 15 min — autonómny cyklus | 5 min |
| **→** | **CELKOM: 30 minút do prvého autonómneho cyklu** | |

Chceš aby som začal **hneď teraz** s Fázou 1? Postupne, krok za krokom — HEAD+PATA quest model, Scout, Researcher, Brainmaster, potom cron. Každý krok otestujeme na reálnom výstupe.

Podme na to? 👇
