# Gate: publikovať naše vlastné defekty výmazu?

**VERDIKT: KILL na navrhované rámovanie. REFRAME na erasure bunku v leaderboarde, ktorý už vlastníme.**

Gate: VALIDATE → STORM (5 šošoviek) → AUDIT → VERIFY (4 verifikačné klastre, 24 citácií).
Tally: **0 vymyslených, 6 opravených, 3 degradované na preprint/odhad.**

---

## 1. Čo gate zabil

**„Vydali sme verziu, ktorá mazala dáta nesprávnej osoby — tu je náš postmortem."**

Tri nezávislé dôvody, každý sám o sebe dostatočný:

**(a) Ten nález už publikoval niekto iný.** Nie podobný — ten istý.
- **MemLeak** (arXiv 2606.29788) otvára vetou *„current memory systems usually delete the text entry and
  report success"* a meria 12,0 % / 18,3 % zvyškovej obnoviteľnosti.
- **GateMem** (arXiv 2606.18829) benchmarkuje aktívne zabúdanie po explicitných žiadostiach o zmazanie a
  zisťuje, že metódy *„still leak unauthorized or deleted information"*.
- **Zep/Graphiti to má vo vlastnej dokumentácii:** *„deleting a source and everything derived from it, and
  nothing else"*.

Keby sme to vydali ako objav, bolo by to nepravdivé a overiteľne.

**(b) Žáner je nasýtený a sme v ňom štvrtí najlepší príklad.** GitLab 2017 živě streamoval 6-hodinovú
obnovu po strate dát; SQLite má trvalú verejnú CVE stránku; Jepsen existuje výlučne na publikovanie cudzích
chýb correctness. Čitateľ nečíta „prísny dodávateľ", číta „dodávateľ, ktorého produkt zmazal dáta
nesprávnej osoby, a chce za to potlesk".

**(c) Skeptikova najostrejšia veta, a je pravdivá:** *„to nie je nález, to je priznanie, že nikto netestoval
vydávané API"*. Publikovanie meraní nedokazuje prísnosť — **datuje jej príchod** a dáva hornú hranicu na to,
ako dlho existuje.

---

## 2. Čo gate naopak vyvrátil — v náš prospech

**Právne riziko: NEPLATÍ tak, ako bolo formulované.** Skeptik tvrdil Art.33 expozíciu. Overené proti
primárnym zdrojom:

- Autor knižnice, ktorý sám nespracúva žiadne osobné údaje, **nie je ani prevádzkovateľ, ani spracovateľ**
  — EDPB 07/2020 §83 vrátane priamo príkladu „IT-špecialista opravujúci softvérovú chybu".
- Art.33(1) kladie 72-hodinové hodiny **výlučne na prevádzkovateľa**. My žiadnu oznamovaciu povinnosť nemáme
  a publikovaním nevzniká oznámiteľné porušenie.
- **Nenašiel sa žiadny precedens** DPA pokutujúcej dodávateľa za zverejnenie defektu vo vlastnom produkte.
- Nasadzovatelia, ktorí bežali na 1.86.0/1.87.0, povinnosť majú — ale **na základe faktov, nie našej
  publikácie**. Zverejnenie ich informuje; mlčanie ju neruší.

To odstraňuje najsilnejší dôvod nepublikovať. Prekážka je vecná, nie právna.

---

## 3. Na čom sa zbieha všetkých päť šošoviek

> **Článok je news cycle. Nástroj je aktívum.**

- **Historik:** Jepsen, TH3, FoundationDB simulátor — každý prežil produkty, ktoré zosmiešnil.
  *„Publikuj defekty, ale conformance suite nech je spustiteľný proti konkurencii, s ich skóre v tej istej
  tabuľke. Disclosure je news cycle; scoreboard, na ktorom sú iní známkovaní, je inštitúcia."*
- **Ekonóm:** ako **súťažiaci** je to čistá deštrukcia marže. Ako **rozhodca** sa to invertuje — Vanta má
  4,15 mld. USD valuáciu na vrstve dôkazov, Jepsen dostáva zaplatené od dodávateľov, ktorých zahanbí.
- **Skeptik (ten istý, čo to zabil):** *„credibility aktívum je test-surface coverage report do budúcna —
  publikuj ten a defekt sa stane poznámkou pod čiarou namiesto titulku."*
- **Praktik:** MCP ekosystém si **sám** postavil `modelcontextprotocol/conformance`, lebo testy knižníc
  nestačili.
- **Akademik:** per-endpoint testy nemajú menovateľa nad „záznamy, ktoré mali byť zasiahnuté".

---

## 4. A tu je vec, ktorú som skoro prehliadol

**Ten nástroj už máme a už sme v pozícii rozhodcu.**

`dancenitra.github.io/agora/public/leaderboard/` — Agent-Memory Integrity Leaderboard, live od 2026-07-22,
zámerne na integritnej osi (nie na recall, kde sme len ďalší súťažiaci). Bunky: value-obscuring revert,
echo resurrection. Dáta z RAMR canonical, submission cez PR.

Takže **nestaviame nový artefakt**. Rozširujeme ten, ktorý vlastníme, o os, ktorú dnešná noc dokázala.

**A práve tá os je jediná overená diera:** GateMem aj MemLeak testujú **metódy**, nie **produkty**. Každé
publikované porovnanie (Mem0/Zep/Letta/Cognee) skóruje recall a latenciu. **Verejný conformance suite ani
leaderboard, ktorý skóruje menované vydávané produkty na korektnosti výmazu, neexistuje.**

Že je diera skutočná, potvrdzujú otvorené issues tretích strán:
mem0 [#5696](https://github.com/mem0ai/mem0/issues/5696) (osirotené entity),
[#4863](https://github.com/mem0ai/mem0/issues/4863), [#6627](https://github.com/mem0ai/mem0/issues/6627) ·
cognee [#3526](https://github.com/topoteretes/cognee/issues/3526) (`forget()` zmaže, `recall()` to vráti) ·
graphiti [#1651](https://github.com/getzep/graphiti/issues/1651).

---

## 5. Implementačný proces (nie článok)

### Fáza 1 — Erasure bunka do RAMR, tri metriky
Presne tie tri režimy, ktoré noc odmerala a pre ktoré máme spustiteľné probe:

| metrika | otázka | naše čísla, ktoré už existujú |
|---|---|---|
| **over-erasure** | zmaže žiadosť na subjekt, ktorý v store nie je, cudzí záznam? | 1.86.0 `erased 1` → 1.87.0 `0` |
| **under-erasure** | prežije po výmaze AKTUÁLNA hodnota subjektu? | 1.86.0/1.87.0 `survives True` → 1.88.0 `False` |
| **surface reach** | zasiahne DSAR to, čo produkt zapísal cez svoj vlastný povrch? | 1.86.0 MCP `0/0/0` vs knižnica `1` |

Harness už existuje: `research/probes/validate_surface_blindness_claim.py` sťahuje wheely z PyPI a beží
proti nim. Zovšeobecniť na adaptér-per-produkt, presne ako RAMR robí pre revert/echo.

### Fáza 2 — Vlastný riadok ako PRVÝ, a s históriou verzií
Nie „inspeximus PASS". **`1.86.0 FAIL · 1.87.0 PARTIAL · 1.88.0 PASS`**, s dátumami a odkazmi na commity.

To je celý ťah. Board, na ktorom sa objavíme až v momente, keď vyhrávame, je board, ktorý sme si postavili,
aby nám lichotil — a to je presne to, čo si pri echo bunke (`všetci 0.00`, tie, vedený zámerne) už raz
odmietol. Naša vlastná zlyhaná história je najsilnejší dôkaz, že tá tabuľka nie je marketing.

### Fáza 3 — Konkurenti cez native config, s ich vlastnými tvrdeniami vedľa skóre
Zep má cascade claim vo vlastnom blogu → citovať doslova a zmerať ho. mem0 tvrdí *„satisfies user erasure
(GDPR/CCPA)"* → zmerať. Otvorené issues sú kontext, nie dôkaz — meriame my.

### Fáza 4 — Až potom text, a s iným titulkom
Nie „naše chyby". **„Nikto neskóruje produkty na korektnosti výmazu. Tu je tabuľka. Naše prvé skóre bolo
FAIL."** Cituje GateMem a MemLeak ako predchodcov na úrovni metód a **netvrdí prvenstvo v náleze** — len
v tom, že je to zmerané na vydávaných produktoch.

---

## 6. Čo si nechať zapísané ako riziko

**RethinkDB.** Jepsen-testovaný, chyby nájdené a opravené, a potom zavretý. Zakladateľ: *„vybrali sme si
príšerný trh a optimalizovali na nesprávne metriky dobra."* Byť preukázateľne správny na trhu, ktorý
správnosť nekupuje, zabíja podľa harmonogramu.

Proti tomu stojí, že mem0 vyzbieral 24 mil. USD na distribúcii, nie na correctness. Takže: erasure bunka je
**distribučný ťah cez pozíciu rozhodcu**, nie produktová stávka na to, že správnosť sa predáva. Ak po dvoch
mesiacoch nepohne ničím, je to lacná prehra a treba to povedať nahlas.

---

## Opravy, ktoré verifikácia vynútila

Zapísané, lebo číslo bez opravy je číslo, ktorému sa nedá veriť:

- **Vanta rast 63 %, nie 69 %** (firemná tlačová správa).
- **Drata: 98 mil. USD ARR je odhad Sacra**, firma sama uvádza „prekročenie 100 mil."; valuácia 2 mld. je
  z decembra 2022, teda 3,5 roka stará.
- **Cognee: 7,5 mil. USD, nie EUR** — európska tlač to prepočítala.
- **Elasticsearch straty ~33 % (2014) a ~22 % (2015)**, nie „~10 %" — pôvodné číslo bolo podlaha.
- **Leave No Data Behind: kontaktovaných bolo všetkých 90 služieb**, 83 aktívne potvrdilo výmaz.
- **Perry & Evangelist: 66 % je z práce z roku 1985**, aktualizácia 1987 uvádza 68,6 %.
- **arXiv 2604.01332 existuje, ale záver je užší**, než ako ho skeptik použil: self-reporty zlyhávajú ako
  *samostatné* hodnotiace nástroje, nie ako také.
- Preprinty (nie peer-review): GateMem, MemLeak, Ghost Vectors, arXiv 2604.01332.
