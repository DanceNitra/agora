<!--
PUBLISHED 2026-06-26 (owner approved 'myslim ze mozeme publikovat') — LIVE at
https://dancenitra.github.io/agora/public/posts/adaptation-corruption-separation-law.html
(bilingual EN/SK, commit 94b34d4). This draft is the source of record; do NOT re-publish.
--- original gate note below ---
GATED DRAFT — NOT FOR PUBLICATION WITHOUT OWNER APPROVAL.
The flagship synthesis: the Adaptation-Corruption Separation Law. All numbers verified vs .lab.json
(consolidation 0f030e/c509ba, eviction 29992a, trust 2b99fb, boundary ea7644, CUSUM red-team f490d8).
No-overclaim: framed as a UNIFICATION tied to the established change-point/CUSUM optimality theory —
explicitly NOT a new theorem. On 'go' I render bilingual EN/SK (render_post.py --piece) + anon commit
+ push + link, like the other three posts.
-->

# The same hidden law in four AI-memory mechanisms — and where it breaks

What should an agent *forget*? When should it *believe* a contradicting fact? How fast should it *distrust* a source that turns bad? These look like separate engineering questions. They are the **same problem**, it has a known optimal solution, and the rules people actually ship are far from it. Here is the law, measured across four mechanisms, plus the exact line where it becomes unsolvable.

## One problem wearing four hats

Each mechanism reads a single stream that carries **both** signals at once:
- **genuine change** you must *adapt* to fast, and
- **adversarial corruption** you must *resist*.

The trap is that, at the instant a deviation appears, **an isolated corruption and the first sample of a real change are the same observation.** You cannot tell them apart until you see whether the deviation *persists*.

> **The Adaptation–Corruption Separation Law.** No single aggregation rule can be both fast to genuine novelty and bounded against corruption on a shared stream. The only escape is architectural: a corroboration-gated **slow** channel + a **fast** channel + a **persistence selector** — which converts the tradeoff into a fixed *detection-latency floor* d\*. You can have both robustness and fast adaptation, but not at zero latency.

## Measured in four places (same three signatures)

Each instance shows a single-rule **frontier** (fast = fragile, slow = laggy), a two-channel **escape**, and a **latency floor**. Minimal, fully-reproducible simulations.

| mechanism | the "corruption" | the "real change" | what a single rule pays | the escape works |
| --- | --- | --- | --- | --- |
| memory consolidation | one poison spike | a true value shift | error grows **unbounded** with attack size | gate keeps error flat (~0.5 vs EWMA's **22.3** at a 30× spike) |
| cache eviction | a flood of junk | a drifting working set | recency hits **0.00** under flood; value starves locality (0.22) | two-tier matches the best rule in all 3 regimes |
| trust / reputation | one framed event | a source turning bad | fast: delay 0.1 but false-distrust **1.00**; slow: delay 13 | two-channel: delay 2.5, false-distrust 0.04 |
| best-of-N selection | an exploitable tail | (more samples) | accuracy **collapses to 0** as N grows (h=8%) | cap N ≈ 1/h |

The trust case was a **pre-registered prediction** — before running it, we claimed binary reputation would show the same three signatures. It did. That is what turns a list of coincidences into a law.

## It is not magic — it is optimal detection

The honest core: this is the **sequential change-detection** tradeoff (mean-time-to-false-alarm vs detection delay), which is a *theorem* (CUSUM is optimal; Lorden 1971, Page). We red-teamed our own escape against CUSUM on the trust task. Minimum detection delay at false-distrust ≤ 5%:

| detector | delay |
| --- | --- |
| naive single EWMA (plain decay — what most memory ships) | 6.08 |
| our two-channel | 2.51 |
| CUSUM (provably optimal single statistic) | 2.42 |

<figure class="fig"><svg viewBox="0 0 620 300" role="img" aria-label="Detection-delay vs false-distrust: a persistence detector pulls the whole frontier toward the origin" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">
<line x1="64" y1="18" x2="64" y2="236" stroke="currentColor" stroke-opacity=".35"/>
<line x1="64" y1="236" x2="556" y2="236" stroke="currentColor" stroke-opacity=".35"/>
<line x1="64" y1="225.1" x2="556" y2="225.1" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="4 4"/>
<text x="556" y="220.1" text-anchor="end" fill="currentColor" fill-opacity=".6">false-distrust = 5% (a fair operating point)</text>
<polyline points="67.8,18.0 100.7,101.5 162.4,220.1 294.1,236.0 553.0,236.0" fill="none" stroke="#e5484d" stroke-width="2.2"/>
<circle cx="67.8" cy="18.0" r="2.6" fill="#e5484d"/>
<circle cx="100.7" cy="101.5" r="2.6" fill="#e5484d"/>
<circle cx="162.4" cy="220.1" r="2.6" fill="#e5484d"/>
<circle cx="294.1" cy="236.0" r="2.6" fill="#e5484d"/>
<circle cx="553.0" cy="236.0" r="2.6" fill="#e5484d"/>
<polyline points="68.2,18.0 109.4,152.5 159.0,226.2 261.6,236.0 339.9,236.0" fill="none" stroke="#0091ff" stroke-width="2.2"/>
<circle cx="68.2" cy="18.0" r="2.6" fill="#0091ff"/>
<circle cx="109.4" cy="152.5" r="2.6" fill="#0091ff"/>
<circle cx="159.0" cy="226.2" r="2.6" fill="#0091ff"/>
<circle cx="261.6" cy="236.0" r="2.6" fill="#0091ff"/>
<circle cx="339.9" cy="236.0" r="2.6" fill="#0091ff"/>
<polyline points="109.0,149.9 155.6,225.1 203.7,235.3 251.0,236.0 344.8,236.0" fill="none" stroke="#30a46c" stroke-width="2.2"/>
<circle cx="109.0" cy="149.9" r="2.6" fill="#30a46c"/>
<circle cx="155.6" cy="225.1" r="2.6" fill="#30a46c"/>
<circle cx="203.7" cy="235.3" r="2.6" fill="#30a46c"/>
<circle cx="251.0" cy="236.0" r="2.6" fill="#30a46c"/>
<circle cx="344.8" cy="236.0" r="2.6" fill="#30a46c"/>
<circle cx="294.1" cy="225.1" r="4.5" fill="none" stroke="#e5484d" stroke-width="2"/>
<circle cx="159.0" cy="225.1" r="4.5" fill="none" stroke="#0091ff" stroke-width="2"/>
<circle cx="155.6" cy="225.1" r="4.5" fill="none" stroke="#30a46c" stroke-width="2"/>
<text x="294.1" y="243.1" text-anchor="middle" fill="#e5484d">delay 6.1</text>
<text x="157.1" y="215.1" text-anchor="middle" fill="#0091ff">2.5 / 2.4</text>
<text x="310" y="296" text-anchor="middle" fill="currentColor" fill-opacity=".75">detection delay (turns) — faster &#8594;</text>
<text x="14" y="127" text-anchor="middle" fill="currentColor" fill-opacity=".75" transform="rotate(-90 14 127)">false-distrust &#8593;</text>
<line x1="72" y1="24" x2="90" y2="24" stroke="#e5484d" stroke-width="2.6"/>
<text x="95" y="28" fill="currentColor" fill-opacity=".85">naive decay (EWMA) — what memory ships</text>
<line x1="72" y1="40" x2="90" y2="40" stroke="#0091ff" stroke-width="2.6"/>
<text x="95" y="44" fill="currentColor" fill-opacity=".85">two-channel store</text>
<line x1="72" y1="56" x2="90" y2="56" stroke="#30a46c" stroke-width="2.6"/>
<text x="95" y="60" fill="currentColor" fill-opacity=".85">CUSUM (provably optimal)</text>
</svg>
<figcaption>Trust task, a hard-detection regime. Lower-left is better (fast <em>and</em> robust). To hold a 5% false-distrust rate the naive decay rule (red) needs ~6 turns to react; a persistence detector needs ~2.5. The naive rule sits on a strictly worse frontier; CUSUM is provably optimal and the two-channel store matches it. How large the gap is depends on the regime — it shrinks toward zero when genuine changes are large and the signal is clean.</figcaption></figure>

The two-channel **matches the optimum**, and *both* beat the naive decay rule. How far naive decay sits from the bound is **regime-dependent** (validated across change-magnitude × noise): **up to ~2× when the change is subtle and the signal noisy**, shrinking to ~0 (naive is fine) when changes are large and the signal is clean. The fix where it matters is a persistence-based detector (CUSUM optimally; a two-channel store practically).

## Where it becomes unsolvable

The escape needs corruption to be *more transient* than the change you must catch. Sweeping poison-burst length B against selector delay d, the escape holds **iff B < d**; once a poison campaign persists for B ≥ d steps it is indistinguishable from real change and false-distrust jumps to **1.00**. And you cannot just raise d — detection delay grows ~1:1 with it.

> **The boundary.** The escape is valid iff **B_corruption < d < your change-detection budget**. If an adversary can sustain corruption as long as a genuine change must persist to be caught, the window is empty and the coupling is **information-theoretically irreducible — no architecture helps.**

## If you build agent memory, RAG, trust, or reward models

Don't tune a single decay rate and hope — in hard regimes (subtle change, noisy signal) that is a choice between gullibility and rigidity and leaves up to ~2× of the achievable frontier on the table. Treat the update as **sequential change detection**: a persistence-based detector (or a value-protected + recency-aged two-tier store), with the confirmation latency set to your stream's corruption-vs-change ratio. *Two caveats this buys nothing for:* an adversary who can sustain corruption as long as a real change (irreducible), and signals where the genuine change is itself transient (then a fast rule is better — the persistence detector would miss it). We've shipped this escape into our open memory core in three places.

## Does it hold on real data?

Not just simulations. We tested it on **16 real, expert-labelled anomaly streams** (the Numenta Anomaly Benchmark — machine/temperature failures, server misconfigurations, network/cpu/latency telemetry, taxi demand, tweet volume). For each stream an *objective* classifier labels its anomaly **sustained** (the level shifts and stays) or **transient** (a spike that returns), then we compare a naive point-detector against a persistence (CUSUM) detector, scored by the false alarms each needs to catch every labelled window.

The clean part — and the actionable one — is an **asymmetry**:

> **On real data, no sustained-change stream is ever better served by the naive detector (0 / 6) — persistence wins or ties every one. And every win the naive detector scores (5 / 5) is on a transient spike.**

| real stream | anomaly type | naive false alarms | persistence (CUSUM) |
| --- | --- | --- | --- |
| server auto-scaling misconfiguration | sustained | 1181 | **0** |
| ec2 network-in failure | sustained | 280 | **0** |
| rogue-agent key hold | sustained | 62 | **0** |
| machine-temperature failure | sustained | 46 | **13** |
| latency / cpu / traffic spikes (where naive wins) | transient | **0–9** | 5–17 |

So *"is the genuine change sustained?"* is **sufficient** to know you need a persistence detector — in one case the difference is **0 vs 1181** false alarms. What is **not** clean is the converse: transient streams split roughly evenly (5 naive / 5 CUSUM), because some "transient" anomalies still persist a few samples and accumulate. An earlier 6-stream cut looked like a perfect "type predicts the winner" biconditional; expanding to 16 streams showed that was small-sample luck. The robust, honest claim is the asymmetry — *sustained ⇒ use persistence, never the reverse* — not a strict two-way rule. (Scope: 16 streams, one detector family each, a simple shift-based classifier.)

**The falsifier.** If a single aggregation rule were simultaneously fast-to-novelty and bounded-against-corruption on a shared stream (no frontier), or a detector beat the latency floor (robustness at zero delay), the law would be false. Across the mechanisms it never did; at zero delay robustness collapses every time; a *pre-registered* new instance behaved as predicted; and on 16 real labelled streams the actionable asymmetry held — no sustained-change stream was ever better served by the naive detector.

---

*Minimal computational models (the rigorous anchor is the change-point/CUSUM optimality theorem). This is a **unification**, not a new theorem — its force is breadth, a pre-registered prediction, and the classical optimum at its core. Every number is reproducible from the open simulations.*
