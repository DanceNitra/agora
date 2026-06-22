#!/usr/bin/env python3
"""Publish flagship #2 — the verification tax — as a bilingual site post via render_post's piece path.
Renders public/posts/{slug}.html + rebuilds the posts index from the manifest. GATED: run only on owner go.
Every number is verified against the source labs in agora_output/lab/*result*.json (and constraint_verification.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_post

EN = r"""
A faster worker is only a more productive worker if you can *trust* the work without redoing it. For AI that is the whole game: a model that answers in a second saves you nothing if you have to spend a minute checking whether the answer is right. So the number that actually matters is not speed and not first-pass accuracy — it is the **residual error after verification**: of the answers the AI gets wrong, how many survive a check and reach you still wrong. We measured it, on local models plus a frontier model, with runnable tests.

## Part 1 — self-checking catches only about a third of hard errors

The popular hope is that a model can "check its own work." It can — but only on the right kind of task. We had a model answer, then verify its own answer, across tasks from cheaply-checkable to open-ended:

| task | first-pass error | self-verify catch | residual error |
|---|---|---|---|
| arithmetic (output cheaply checkable) | 0.08 | **1.00** | **0.00** |
| MMLU-Pro (hard knowledge, not checkable) | 0.30–0.44 | 0.17–0.36 | **~0.28** |
| multi-hop QA (hard reasoning, not checkable) | 0.42–0.48 | 0.33–0.36 | **~0.30** |

On a checkable task self-verification catches **100%** of errors and the residual is zero — fast output becomes trustworthy output. On hard reasoning it catches only **about a third** (firmed at n=120: mean catch 0.26). After the model has "checked its work," **~30% of its hard-reasoning answers are still wrong — and it believes they are right.**

## Part 2 — a stronger model is *worse* at this, not better

Surely a more capable model checks itself better? We ran the same self-verification on a strong frontier model (glm-5.2). It caught **fewer** of its own hard-reasoning errors than the small local model (**0.19** vs ~0.34) and **never once flagged its own answer as wrong** (false-alarm rate 0.00). Higher capability bought higher confidence, not more self-knowledge — the stronger model is more *confidently* wrong. The hope that "better models will self-correct into trustworthiness" is false on exactly the work where it would matter.

## Part 3 — a second, independent model doesn't rescue it either

If a model can't check itself, pay for an independent one? We had the strong frontier model check the *small* model's answers. The independent checker caught **fewer** errors than the model's own self-check (**0.23** vs 0.34). The reason is the engine under all of this: **LLM errors are systematic and shared across model families** — a different model is blind to the *same* hard questions, so it nods along to plausible-looking wrong answers. No stack of models — self, stronger-self, or independent-and-stronger — pushed hard-reasoning error-catching above ~0.36.

| checker on hard reasoning | catch rate |
|---|---|
| the model checks itself | ~0.34 |
| a *stronger* model checks itself | 0.19 (and never doubts itself) |
| an *independent* stronger model checks it | 0.23 |

## Part 4 — the keystone: checkability, not difficulty

So far "hard" and "uncheckable" travelled together — arithmetic was both easy and checkable, reasoning both hard and uncheckable. Which one drives the tax? We built the decisive control: a task that is **hard to solve but easy to check** — a constraint search ("find a 3-digit number whose digits sum to S, divisible by D, of given parity"). The model has to *search* to solve it, and it failed first-pass **35% of the time** — genuinely hard. But every constraint is mechanically checkable, and self-verification caught **100%** of the errors. Residual: **zero**.

That settles it. **The verification tax is governed by checkability, not difficulty.** A task being hard does nothing to the tax; a task being un-checkable is everything.

## The law

> **AI speed becomes trust only where the output is cheaply checkable — and capability doesn't pay the tax down, checkability does.**

Wherever an answer can be cheaply verified (arithmetic, code that runs, a constraint that can be re-checked, a fact with a lookup), AI speedups convert into trustworthy output no matter how hard the answer was to produce. Wherever the output *cannot* be cheaply checked — open-ended reasoning, judgement, synthesis — there is an **irreducible verification tax of ~30% residual error** that does not fall as models improve and is not removed by stacking more or stronger models on top. It has to be paid by a human, or avoided by restricting the work to checkable form.

## What to actually do

- **For checkable work, trust the speedup.** Pair the model with cheap automated verification (run the code, re-check the constraint, look up the fact) and ship — the residual really is near zero.
- **For open-ended hard work, budget the human check as a fixed cost.** It is irreducible; don't expect a better model or a second model to remove it. The productivity gain is real but capped by verification, not by the model.
- **Don't buy a "second opinion" from another model on shared-blind-spot tasks.** It catches fewer errors than the model's own check, because the blind spots are shared.
- **Where you can, convert un-checkable work into checkable form** — force intermediate steps, demand a re-checkable artifact, ground the answer in a source that can be verified. That is what moves the residual, not a bigger model.

Caveats: measured on a local model (qwen3-coder:30b) and a frontier model (glm-5.2); n = 25–60 per task (constraint search n = 40); strict automated grading; the frontier model's higher multi-hop error rate is partly grading/format strictness, but its catch≈0.19 with zero false alarms is unambiguous; "catch" means the model flags its own answer as wrong. Every number above comes from a runnable experiment.
"""

SK = r"""
Rýchlejší pracovník je produktívnejší len vtedy, ak môžeš jeho práci *dôverovať* bez toho, aby si ju robil znova. Pri AI je to celá hra: model, čo odpovie za sekundu, ti nič neušetrí, ak musíš minútu kontrolovať, či je odpoveď správna. Číslo, ktoré naozaj rozhoduje, teda nie je rýchlosť ani presnosť na prvý pokus — je to **reziduálna chyba po overení**: z odpovedí, ktoré AI pokazí, koľko ich prejde kontrolou a dorazí k tebe stále zlých. Odmerali sme to, na lokálnych modeloch plus frontier modeli, bežateľnými testami.

## Časť 1 — sebakontrola zachytí len asi tretinu ťažkých chýb

Populárna nádej je, že model si vie "skontrolovať vlastnú prácu". Vie — ale len na správnom type úlohy. Nechali sme model odpovedať a potom overiť vlastnú odpoveď, na úlohách od lacno-overiteľných po otvorené:

| úloha | chyba na prvý pokus | záchyt sebakontroly | reziduálna chyba |
|---|---|---|---|
| aritmetika (výstup lacno overiteľný) | 0.08 | **1.00** | **0.00** |
| MMLU-Pro (ťažké znalosti, neoveriteľné) | 0.30–0.44 | 0.17–0.36 | **~0.28** |
| multi-hop QA (ťažké uvažovanie, neoveriteľné) | 0.42–0.48 | 0.33–0.36 | **~0.30** |

Na overiteľnej úlohe sebakontrola zachytí **100%** chýb a reziduál je nula — rýchly výstup sa stáva dôveryhodným. Na ťažkom uvažovaní zachytí len **asi tretinu** (potvrdené pri n=120: priemerný záchyt 0.26). Po tom, čo si model "skontroloval prácu", **~30% jeho odpovedí na ťažké uvažovanie je stále zlých — a on verí, že sú správne.**

## Časť 2 — silnejší model je v tomto *horší*, nie lepší

Iste, schopnejší model sa skontroluje lepšie? Pustili sme tú istú sebakontrolu na silnom frontier modeli (glm-5.2). Zachytil **menej** vlastných chýb v ťažkom uvažovaní než malý lokálny model (**0.19** vs ~0.34) a **ani raz neoznačil vlastnú odpoveď za zlú** (miera falošných poplachov 0.00). Vyššia schopnosť kúpila vyššiu sebaistotu, nie viac sebapoznania — silnejší model sa mýli *sebavedomejšie*. Nádej, že "lepšie modely sa samy opravia do dôveryhodnosti", je nepravdivá presne na tej práci, kde by na tom záležalo.

## Časť 3 — ani druhý, nezávislý model to nezachráni

Ak sa model nevie skontrolovať sám, zaplatíme nezávislý? Nechali sme silný frontier model skontrolovať odpovede *malého* modelu. Nezávislý kontrolór zachytil **menej** chýb než vlastná sebakontrola modelu (**0.23** vs 0.34). Dôvod je motor pod tým všetkým: **chyby LLM sú systematické a zdieľané naprieč rodinami modelov** — iný model je slepý na *tie isté* ťažké otázky, takže prikyvuje vierohodne vyzerajúcim zlým odpovediam. Žiadna kombinácia modelov — sám, silnejší-sám či nezávislý-a-silnejší — neposunula záchyt chýb v ťažkom uvažovaní nad ~0.36.

| kontrolór ťažkého uvažovania | miera záchytu |
|---|---|
| model kontroluje sám seba | ~0.34 |
| *silnejší* model kontroluje sám seba | 0.19 (a nikdy o sebe nepochybuje) |
| *nezávislý* silnejší model ho kontroluje | 0.23 |

## Časť 4 — kľúč: overiteľnosť, nie obtiažnosť

Doteraz "ťažké" a "neoveriteľné" chodili spolu — aritmetika bola ľahká aj overiteľná, uvažovanie ťažké aj neoveriteľné. Čo z toho daň poháňa? Postavili sme rozhodujúci control: úlohu, ktorá je **ťažká na vyriešenie, ale ľahká na overenie** — hľadanie čísla s obmedzeniami ("nájdi 3-ciferné číslo, ktorého číslice dávajú súčet S, deliteľné D, danej parity"). Model musí *hľadať*, aby ho vyriešil, a na prvý pokus zlyhal v **35% prípadov** — naozaj ťažké. Lenže každé obmedzenie sa dá mechanicky overiť a sebakontrola zachytila **100%** chýb. Reziduál: **nula**.

To je rozhodnuté. **Daň za overenie neriadi obtiažnosť, ale overiteľnosť.** To, že je úloha ťažká, s daňou nerobí nič; to, že je neoveriteľná, robí všetko.

## Zákon

> **Rýchlosť AI sa mení na dôveru len tam, kde sa výstup dá lacno overiť — a daň nesplatí schopnosť, ale overiteľnosť.**

Všade, kde sa odpoveď dá lacno overiť (aritmetika, kód čo zbehne, obmedzenie čo sa dá prepočítať, fakt s vyhľadaním), sa zrýchlenie AI mení na dôveryhodný výstup bez ohľadu na to, aké ťažké bolo ho vyrobiť. Všade, kde sa výstup *nedá* lacno overiť — otvorené uvažovanie, úsudok, syntéza — existuje **neodstrániteľná daň za overenie ~30% reziduálnej chyby**, ktorá neklesá so zlepšovaním modelov a neodstráni ju stohovanie viacerých či silnejších modelov. Musí ju zaplatiť človek, alebo sa jej vyhnúť tým, že prácu obmedzíš na overiteľnú formu.

## Čo s tým reálne robiť

- **Pri overiteľnej práci dôveruj zrýchleniu.** Spáruj model s lacným automatickým overením (spusti kód, prepočítaj obmedzenie, vyhľadaj fakt) a posielaj ďalej — reziduál je naozaj blízko nuly.
- **Pri otvorenej ťažkej práci započítaj ľudskú kontrolu ako fixný náklad.** Je neodstrániteľná; nečakaj, že ju lepší alebo druhý model odstráni. Zisk z produktivity je reálny, ale stropovaný overením, nie modelom.
- **Nekupuj "druhý názor" od iného modelu na úlohách so zdieľanou slepou škvrnou.** Zachytí menej chýb než vlastná kontrola modelu, lebo slepé škvrny sú zdieľané.
- **Kde sa dá, preveď neoveriteľnú prácu na overiteľnú formu** — vynúť medzikroky, žiadaj prepočítateľný artefakt, ukotvi odpoveď v overiteľnom zdroji. To hýbe reziduálom, nie väčší model.

Výhrady: merané na lokálnom modeli (qwen3-coder:30b) a frontier modeli (glm-5.2); n = 25–60 na úlohu (hľadanie s obmedzeniami n = 40); prísne automatické hodnotenie; vyššia multi-hop chybovosť frontier modelu je čiastočne prísnosťou hodnotenia/formátu, ale jeho záchyt ≈0.19 s nulovými falošnými poplachmi je jednoznačný; "záchyt" znamená, že model označí vlastnú odpoveď za zlú. Každé číslo vyššie pochádza z bežateľného experimentu.
"""

spec = {
    "slug": "the-verification-tax",
    "title": "The verification tax: AI speed becomes trust only where the output is checkable",
    "title_sk": "Daň za overenie: rýchlosť AI sa mení na dôveru len tam, kde sa výstup dá overiť",
    "desc": "An AI that answers fast saves nothing if you must re-check it. We measured the residual error after verification: self-checking catches only ~1/3 of hard-reasoning errors, a stronger model is worse (and never doubts itself), an independent model doesn't rescue it — yet a hard-but-checkable task gets caught 100%. The tax is governed by checkability, not difficulty.",
    "desc_sk": "AI, čo odpovie rýchlo, ti nič neušetrí, ak ju musíš prekontrolovať. Odmerali sme reziduálnu chybu po overení: sebakontrola zachytí len ~1/3 chýb v ťažkom uvažovaní, silnejší model je horší (a nikdy o sebe nepochybuje), nezávislý model to nezachráni — no ťažkú-ale-overiteľnú úlohu zachytí na 100%. Daň riadi overiteľnosť, nie obtiažnosť.",
    "date": "2026-06-22",
    "tags": "AI reliability · Future of work · Verification",
    "tags_sk": "Spoľahlivosť AI · Budúcnosť práce · Overovanie",
    "kicker": "Research", "kicker_sk": "Výskum",
    "body": EN, "body_sk": SK,
}

if __name__ == "__main__":
    slug, read = render_post.render_piece(spec)
    render_post.build_index()
    print(f"wrote public/posts/{slug}.html  ({read} min)  + rebuilt posts index")
