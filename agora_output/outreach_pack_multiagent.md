# Outreach pack — multi-agent herding result (warm, peer-to-peer, NOT a pitch)

**Goal:** put our measured herding result in front of the few people who work on exactly this, as
researcher-to-researcher contact about related work — the one channel that isn't filtered by reputation.
**Gated: Rasto sends.** Honest note: I picked FEW + deeply tailored over 10 generic — 10 identical cold
emails is spam; a specific note that engages someone's actual paper gets a reply.

**Numbers (re-verified):** collective accuracy ~100% (independent / k=0) → ~90% (1 peer) → ~64% at 2
peers ≈ a single agent (60%); onset threshold k_c ≈ own-weight + 1; the collapse is specific to *naive*
updating — discount redundant peers, or share evidence not verdicts → back near 100% at the same k.

**Links to include:**
- writeup: https://dancenitra.github.io/agora/public/posts/why-crowds-get-dumber-when-they-watch-each-other-and-the-sur.html
- one-file model: https://github.com/DanceNitra/agora/tree/main/herdcheck

**How to reach them:** the author emails are on the **first page of each arXiv PDF** (links below) — that's
the cleanest, unfiltered channel for researchers. (I will not invent X handles; if you want X, search the
person's name — don't guess.) Send 1 email per paper, to the lead author; cc the senior author if you like.

---

## 1 — "Herd Behavior" team (UPenn) · the closest match to our result
Paper: *Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems* — arXiv 2505.21588
People: **Young-Min Cho** (lead), Sharath Chandra Guntuku, **Lyle Ungar** (senior). Emails on the PDF: https://arxiv.org/pdf/2505.21588

**Email — Subject:** Independent measurement of the herding threshold from your "Herd Behavior" setup

> Hi Young-Min,
>
> Your "Herd Behavior" paper pushed me to measure *where* the peer influence tips over, in a minimal
> model: each agent gets a private ~60%-accurate signal, sees k peers' answers, updates, acts.
> Collective accuracy goes ~100% (independent) → ~90% at one peer → ~64% at two — basically a single
> agent. The collapse is sharp and starts once observed answers outweigh an agent's own evidence
> (≈ k = own-weight + 1), and it's specific to *naive* updating: discount the redundancy in correlated
> answers (a peer's verdict already baked in what they saw), or pass evidence instead of verdicts, and
> it's back near 100% at the same k.
>
> One open-source file if you want to break it: github.com/DanceNitra/agora/tree/main/herdcheck — short
> writeup: [link]. Does the k≈2 onset line up with your controlled experiments? Genuinely curious.
>
> — Rastislav

---

## 2 — "Multi-Agent Teams Hold Experts Back" team (Stanford) · your fix matches their mechanism
Paper: *Multi-Agent Teams Hold Experts Back* — arXiv 2602.01011
People: **Aneesh Pappu** (lead; GitHub: github.com/apappu97), Batu El, Hancheng Cao, **James Zou** (senior). Emails on the PDF: https://arxiv.org/pdf/2602.01011

**Email — Subject:** A computable threshold for the "integrative compromise" in your experts paper

> Hi Aneesh,
>
> "Multi-Agent Teams Hold Experts Back" really landed — the "integrative compromise: averaging expert
> and non-expert views rather than weighting expertise" is exactly the mechanism I ended up measuring.
> In a minimal social-learning model the crowd collapses to single-member accuracy precisely when
> observed answers outweigh an agent's own evidence (threshold k = own-weight + 1) — and raising
> own-weight, or discounting redundant peers, restores ~100%. So "leveraging, not identification" shows
> up as a weighting threshold you can actually compute.
>
> One file: github.com/DanceNitra/agora/tree/main/herdcheck — writeup: [link]. I'd love to know whether,
> in your setup, weighting the expert above ~1 peer-equivalent recovers their solo performance.
>
> — Rastislav

---

## 3 — "Why Do Multi-Agent LLM Systems Fail?" / MAST team (UC Berkeley)
Paper: *Why Do Multi-Agent LLM Systems Fail?* — arXiv 2503.13657
People: **Mert Cemri** (lead), Melissa Z. Pan, … (UC Berkeley). Emails on the PDF: https://arxiv.org/pdf/2503.13657

**Email — Subject:** A minimal measured model for one MAST failure mode (herding)

> Hi Mert,
>
> MAST is the reference I keep coming back to. I tried to build the smallest *measured* model for one
> mechanism that might sit under your "inter-agent misalignment" cluster: collective accuracy collapses
> to single-agent the moment each agent observes ~2 peers' answers (threshold k = own-weight + 1),
> specific to naive updating; discounting redundancy restores it. It gives a knob (own-evidence weight)
> rather than just a label.
>
> One file: github.com/DanceNitra/agora/tree/main/herdcheck — writeup: [link]. Does this map onto a MAST
> failure mode, or is it orthogonal to the taxonomy? Would value your read.
>
> — Rastislav

---

## Also relevant (if the first 3 get traction, expand here)
- *Towards a Science of Collective AI: ... Need a Transition from Blind Trial-and-Error to Rigorous
  Science* — arXiv 2602.05289 (our whole "measure it" angle is their thesis — natural ally).
- *The PIMMUR Principles: Ensuring Validity in Collective Behavior of LLM Societies* — arXiv 2509.18052.
- Maintainers of agent frameworks (CrewAI, AutoGen, LangGraph) — find via their GitHub "issues"/maintainer
  list; frame it as "here's a measured failure mode + a one-file check," not a pitch.

## X version (drop as a REPLY when one of them — or anyone — posts about multi-agent reliability)
> measured this in a minimal model: collective accuracy collapses to ~a single agent the moment each
> agent sees ~2 peers (threshold ≈ own-weight + 1). but it's naive-updating-specific — discount redundant
> peers, or share evidence not verdicts, and it's back to ~100% at the same k. one file: [github link]

## Notes for Rasto
- Send the 3 emails. Success = a reply / a real conversation, not a sale.
- If someone engages: don't pitch anything. Ask about their work, compare notes. That's how reputation
  among researchers actually starts — and it's the warm channel that survives having zero followers.
- A researcher replying "interesting, here's a caveat" IS the win — it's real signal that the work lands
  with the people who'd know.
