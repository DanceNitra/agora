#!/usr/bin/env python3
"""Publish the Diversity-Flip flagship as a bilingual site post via render_post's piece path.
Renders public/posts/{slug}.html + rebuilds the posts index from the manifest. Owner-approved, gated."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_post

EN = r"""
## Part 1 — the wall: cheap tricks don't fix hard *answers*

The standard advice for an unreliable LLM is "combine your way out": sample it many times and vote, try diverse prompts, add another model, let it check itself. On hard reasoning — multi-hop **MuSiQue** and graduate **MMLU-Pro**, strict grading, single-model accuracy in the **0.3–0.6** band — we measured each one, on local models plus a frontier voter.

| trick | what happened |
|---|---|
| more samples (self-consistency) | saturates — about **1.6** effective independent samples |
| prompt-strategy diversity | doesn't decorrelate (**ρ ≈ 0.72**) |
| model / family diversity | err on the same items (cross-family **ρ ≈ 0.70**) |
| "family independence" as a trust signal | no premium at matched strength (**≈ 0**) |
| self-verification | recognizes the right answer to its own failures only about **40%** of the time |

One mechanism explains all of it: **LLM errors are systematic, not random.** Aggregation only cancels *random, independent* noise; LLM errors are biased and *shared* — across a model's own samples and across different families. A model cannot average, verify, or check its way to an answer it could not produce in the first place.

## Part 2 — what works, and the trap

Hand the model the *gold* facts and multi-hop accuracy jumps **+21 points** (0.47 → 0.66). But that is an **oracle upper bound** — perfect retrieval. Real retrieval that returns only *some* of the needed facts (flat semantic search recovered about **42%** of them) scored *below* full context (**0.22 vs 0.47**): multi-hop needs the *complete* chain, and a partial chain breaks the answer. **Bad RAG is worse than no RAG.** The lever is *complete* information, not *more* opinions — and reaching that oracle is itself the hard part.

## Part 3 — the flip: the same diversity is the engine for *ideas*

Here is the turn. The model diversity that bought **≈ 0** for finding *the* answer *pays* when you want *new* answers. On open-ended ideation, three diverse model families cover **+14–16%** more unique ideas than resampling one model at equal budget (replicated across two model trios); their cross-family idea-overlap is about **2× lower** than one model's self-overlap; this survives semantic de-duplication (distinct *concepts*, not paraphrases); and a judge rated the extra ideas **as valid** as the base ones (**0.65 vs 0.65**).

Honest about size: the first-order win is fanning out to *more generators at all* — even a second model from the *same* family adds most of the gain; a *different* family is a real but modest edge (about **13%** more marginal coverage). On convergent tasks the families converge on the same, often wrong, answer; on divergent tasks they diverge to different, valid ideas.

**One law: diversity is noise when you want agreement, and signal when you want exploration.**

## What to actually do

- **Don't ensemble or self-check for hard answers.** It targets random noise you don't have — spend on a stronger model or *complete* grounding instead.
- **Invest in retrieval quality, not answer-voting** — and remember that partial retrieval can hurt.
- **Do fan out for ideation** — more generators, ideally across diverse families, when you want to cover an idea space.

Caveats: two benchmarks, specific models, strict-substring and judge grading; "hard" means the headroom subset where models have room to fail; idea *novelty* beyond validity was not separately scored. Every number above comes from a runnable experiment.
"""

SK = r"""
## Časť 1 — stena: lacné triky neopravia ťažké *odpovede*

Štandardná rada pri nespoľahlivom LLM je "skombinuj sa z toho von": navzorkuj ho veľakrát a hlasuj, skús rôzne prompty, pridaj ďalší model, nechaj ho skontrolovať sa. Na ťažkom uvažovaní — multi-hop **MuSiQue** a postgraduálne **MMLU-Pro**, prísne hodnotenie, presnosť jedného modelu v pásme **0.3–0.6** — sme odmerali každý z nich, na lokálnych modeloch plus jeden frontier model.

| trik | čo sa stalo |
|---|---|
| viac vzoriek (self-consistency) | saturuje — asi **1.6** efektívnych nezávislých vzoriek |
| diverzita prompt-stratégií | nedekoreluje (**ρ ≈ 0.72**) |
| diverzita modelov / rodín | mýlia sa na tých istých položkách (cross-family **ρ ≈ 0.70**) |
| "nezávislosť rodiny" ako signál dôvery | žiadny prínos pri rovnakej sile (**≈ 0**) |
| sebaoverenie | správnu odpoveď na vlastné zlyhania rozpozná len asi **40%** prípadov |

Jeden mechanizmus to vysvetľuje celé: **chyby LLM sú systematické, nie náhodné.** Agregácia ruší len *náhodný, nezávislý* šum; chyby LLM sú vychýlené a *zdieľané* — naprieč vlastnými vzorkami modelu aj naprieč rôznymi rodinami. Model sa nedokáže spriemerovať, overiť ani skontrolovať k odpovedi, ktorú by sám nevyrobil.

## Časť 2 — čo funguje, a pasca

Daj modelu *správne* fakty a multi-hop presnosť skočí o **+21 bodov** (0.47 → 0.66). Lenže to je **oracle horný strop** — dokonalý retrieval. Reálny retrieval, ktorý vráti len *niektoré* z potrebných faktov (ploché sémantické vyhľadávanie ich našlo asi **42%**), skóroval *pod* plným kontextom (**0.22 vs 0.47**): multi-hop potrebuje *kompletný* reťazec a neúplný reťazec zlomí odpoveď. **Zlý RAG je horší než žiadny RAG.** Páka je *kompletná* informácia, nie *viac* názorov — a dostať sa k tomu oracle je samo o sebe to ťažké.

## Časť 3 — preklopenie: tá istá diverzita je motor pre *nápady*

Tu je obrat. Diverzita modelov, ktorá kúpila **≈ 0** pri hľadaní *jednej* odpovede, sa *vypláca*, keď chceš *nové* odpovede. Pri otvorenom generovaní nápadov tri rôzne rodiny pokryjú **+14–16%** viac unikátnych nápadov než prevzorkovanie jedného modelu pri rovnakom rozpočte (replikované na dvoch triciach modelov); ich cross-family prekryv nápadov je asi **2× nižší** než vlastný prekryv jedného modelu; prežije to sémantickú de-duplikáciu (odlišné *koncepty*, nie parafrázy); a hodnotiteľ ohodnotil pridané nápady **rovnako validné** ako základné (**0.65 vs 0.65**).

Čestne k veľkosti: prvoradý zisk je rozšíriť sa na *viac generátorov vôbec* — aj druhý model z *tej istej* rodiny pridá väčšinu zisku; *iná* rodina je reálny, ale mierny bonus (asi **13%** viac marginálneho pokrytia). Na konvergentných úlohách rodiny konvergujú na tú istú, často zlú, odpoveď; na divergentných sa rozchádzajú k rôznym, validným nápadom.

**Jeden zákon: diverzita je šum, keď chceš zhodu, a signál, keď chceš objavovanie.**

## Čo s tým reálne robiť

- **Neensembluj a nenechávaj model self-checkovať pri ťažkých odpovediach.** Mieri to na náhodný šum, ktorý nemáš — radšej investuj do silnejšieho modelu alebo *kompletného* groundingu.
- **Investuj do kvality retrievalu, nie do hlasovania o odpovedi** — a pamätaj, že neúplný retrieval môže uškodiť.
- **Rozširuj sa pri generovaní nápadov** — viac generátorov, ideálne naprieč rôznymi rodinami, keď chceš pokryť priestor nápadov.

Výhrady: dva benchmarky, konkrétne modely, prísne substring/judge hodnotenie; "ťažké" znamená podmnožinu s priestorom na chybu; *novosť* nápadov nad rámec validity sme samostatne neskórovali. Každé číslo vyššie pochádza z bežateľného experimentu.
"""

spec = {
    "slug": "diversity-is-noise-for-answers-signal-for-ideas",
    "title": "Diversity is noise when you want the right answer — and the engine when you want new ideas",
    "title_sk": "Diverzita je šum, keď chceš správnu odpoveď — a motor, keď chceš nové nápady",
    "desc": "Every cheap trick for making LLMs reliable on hard answers fails — because their errors are systematic, not random. Yet the same model diversity is the engine for generating ideas: +14–16% more, equally valid. Diversity is noise for agreement, signal for exploration.",
    "desc_sk": "Každý lacný trik na spoľahlivosť LLM pri ťažkých odpovediach zlyhá — lebo ich chyby sú systematické, nie náhodné. No tá istá diverzita modelov je motorom generovania nápadov: +14–16% viac, rovnako validných. Diverzita je šum pri zhode, signál pri objavovaní.",
    "date": "2026-06-22",
    "tags": "LLM reasoning · Ensembling · Idea generation",
    "tags_sk": "LLM uvažovanie · Ensembling · Generovanie nápadov",
    "kicker": "Research", "kicker_sk": "Výskum",
    "body": EN, "body_sk": SK,
}

slug, read = render_post.render_piece(spec)
render_post.build_index()
print(f"wrote public/posts/{slug}.html  ({read} min)  + rebuilt posts index")
