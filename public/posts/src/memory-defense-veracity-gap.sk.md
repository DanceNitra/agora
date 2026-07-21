# Obrana pamäte, ktorá verí pamäti, nie je obrana

## Východisko

Shippujeme open-source pamäťové jadro pre AI agentov ([inspeximus](https://github.com/DanceNitra/agora/tree/main/inspeximus)). Za posledné mesiace sme pridali štyri obrany proti otrave pamäte — útoku, pri ktorom niekto prepašuje vyrobený záznam do dlhodobého úložiska agenta, aby podľa neho neskôr konal. Každú obranu sme merali voči *neadaptívnemu* útočníkovi, ktorý neoptimalizuje proti konkrétnej obrane. To je nesprávny test a adversariálny ML sa to naučil ťažkou cestou: [Athalye a spol. zlomili 7 z 9 obrán prijatých na ICLR 2018](https://arxiv.org/abs/1802.00420) a [Tramèr a spol. zlomili ďalších 13 v roku 2020](https://arxiv.org/abs/2002.08347), čím ustanovili pravidlo, že obranu musíš testovať voči útočníkovi, ktorý ju *pozná*.

Takže sme to spravili s vlastným stackom. Napísali sme [spustiteľný red-team](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py) všetkých štyroch obrán voči adaptívnemu útočníkovi. Tento post je to, čo našiel. Je to **systematizácia, nie objav** — každý kúsok je učebnicový, a hovoríme to hneď na začiatku. Hodnota je v jednotnom adaptívnom prehľade na jednom shippnutom stacku, v jednom čestnom čísle, ktoré dáva, a v strope, ktorý odhaľuje.

## Štyri obrany, jedna spoločná chyba

| obrana (inspeximus) | čo dodáva útočník | výsledok |
|---|---|---|
| hodnotou chránená dvojvrstvová eviction | self-deklaruje MAX hodnotu → vlastní high-stakes vrstvu | padá |
| korroboračná / influence brána | self-vyrobí „nezávislých" svedkov, ktorých ovláda | padá |
| deterministický supersession kľúč (retire-on-write) | zapíše kľúč *posledný* → stiahne pravdivú hodnotu | padá |
| korroborácia-cez-zaslúžený-výsledok | self-oznámkuje vlastný jed ako úspech | padá |

Pozri na stredný stĺpec. Každá z týchto obrán skóruje spomienku podľa vlastnosti **spočítateľnej z vlastného obsahu spomienky**: aká hodnotná tvrdí, že je; koľko vecí ju korroboruje; kedy bola zapísaná; či „uspela". A protivník je ten, kto *píše obsah*. Takže každý signál si nastaví sám. Nie sú to štyri bugy; je to jedna chyba počítaná štyrikrát — [Goodhartov vzorec](https://www.cambridge.org/core/journals/european-review/article/abs/improving-ratings-audit-in-the-british-university-system/FC2EE640C0C44E3DB87C29FB666E9AAB) (Strathernina formulácia z roku 1997: „keď sa miera stane cieľom, prestáva byť dobrou mierou"). Self-deklarovaná hodnota je Goodhartova návnada. Self-časovaný zápis vyhrávajúci na recency je [last-writer-wins register](https://link.springer.com/chapter/10.1007/978-3-642-24550-3_29) (Shapiro a spol. 2011) a útočník, ktorý sfalšuje neskorší zápis, ho vyhrá. Self-oznámkovaný výsledok je presne [útok MINJA](https://arxiv.org/abs/2503.03704) (NeurIPS 2025).

**Čestný limit, nahlas:** toto sú štylizované ukážky, ktoré sú *definičné z konštrukcie*. Necháme útočníka self-deklarovať hodnotu a self-známkovať výsledky, takže „hodnota zlyhá" a „self-známkovanie zlyhá" je takmer predpokladané. To je zmysel cvičenia — ukázať, že štyri primitíva zdieľajú jeden predpoklad — nie meraný prekvapák. A každá ukážka **vypína ostatné vrstvy**, aby izolovala jeden primitív; inspeximus ich shippuje [*vrstvené*](agent-memory-poisoning-layered-defense-residual.html) a vrstvená konfigurácia je silnejšia než ktorákoľvek jednotlivá obrana, ktorá tu padá. Čítaj to ako „štyri iba-obsahové signály sú jednotlivo spoofnuteľné", nikdy nie ako „inspeximus je rozbité".

## Čo zostáva, nie je lepší signál — je to proveniencia a cena

Ak je každý z obsahu spočítateľný signál sfalšovateľný pisateľom, jediné signály, ktoré *nie sú* jeho na napísanie, sú **odkiaľ obsah prišiel** (proveniencia) a **čo ho stálo to povedať** (nesfalšovateľný, vzácny zdroj). Toto je terminus, ku ktorému každý adversariálny systém nakoniec dôjde: e-mailový spam ustúpil od bayesovských obsahových filtrov (porazených [bayesovskou otravou](https://en.wikipedia.org/wiki/Bayesian_poisoning)) k identite a reputácii odosielateľa (SPF/DKIM/DMARC); trvácny check na sockpuppety na Wikipédii je IP/device proveniencia, nie klasifikátor správania; P2P ustúpilo k [Sybil](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/) cene. Literatúra bezpečnosti proveniencie menuje tú istú vlastnosť: [prehľad data provenance z ACM Computing Surveys 2023](https://dl.acm.org/doi/10.1145/3593294) (Pan, Stakhanova & Ray) uvádza *unforgeability* (nesfalšovateľnosť) medzi jadrovými bezpečnostnými vlastnosťami provenienčného systému, popri integrite, autenticite a nepopierateľnosti.

Takže ten ústup nie je nový a netvrdíme, že je. Nie je to ani ten únik, ako vyzerá, z dvoch dôvodov, ktoré nás red-team prinútil povedať.

**Po prvé, „identita" nie je jediná odpoveď a útok neeliminuje.** [Douceurov Sybil výsledok z roku 2002](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/) je presný: bez logicky centralizovanej *dôveryhodnej autority* je odlišná identita nemožná „okrem extrémnych a nerealistických predpokladov parity zdrojov". Dôveryhodná autorita Sybilov *eliminuje*; vzácny zdroj (proof-of-work, stake alebo attack-edges sociálneho grafu ako v [SybilGuard](https://dl.acm.org/doi/10.1145/1159913.1159945)/SybilLimit/SybilRank) ich len *ohraničí*. inspeximus `strict_corroboration` + atestácia idú cestou vzácnosti: počítajú odlišné *overené kľúče*, takže každý svedok stojí identitu. Ale náš vlastný probe čestne ukazuje strop — **s dvomi kľúčmi útočník stále prejde dvoj-svedkovou bránou.** Zdvíha cenu; nezatvára dvere.

**Po druhé — a toto je časť, na ktorej záleží — proveniencia overuje zdroj, nie pravdivosť.** Tu je Veracity Gap a naša vlastná citácia je dôkazom. [MINJA](https://arxiv.org/abs/2503.03704) vloží jed do pamäte agenta pomocou *iba bežných dotazov od legitímneho, autentifikovaného používateľa* (98,2 % injekcia, 76,8 % úspešnosť útoku, žiadny privilegovaný prístup). Otrávený zápis má pravú provenienciu — pravý používateľ, pravá session, správna atribúcia. Provenienčná kotva ho pustí rovno ďalej. [PoisonedRAG](https://arxiv.org/abs/2402.07867) (USENIX Security 2025) hovorí to isté na strane retrievalu: správne pripísané dokumenty, adversariálny obsah. **Proveniencia a cena sú podlaha, ku ktorej ustúpiš, keď obsahové heuristiky zlyhajú — nie sú oprava, lebo oceňujú kto to povedal, nikdy či je to tak.**

## Jedno čestné číslo

V celom cvičení je presne jeden kvantitatívny výsledok a je zámerne malý. V eviction ukážke sleduje legitímny podiel chránenej (high-stakes) vrstvy deterministickú rampu `max(0, (P − n) / P)`, ako sa self-hodnotený počet jedu `n` blíži k veľkosti chránenej vrstvy `P`, pričom dosahuje nulu pri `n = P`. Pri P=45 je to 0,78 pri n=10 a 0,00 pri n=50. Je to svojím spôsobom aritmetická identita, nie objavený zákon — probe ju potvrdzuje a hovorí užitočnú vec čisto: **ohraničená kapacita obmedzuje počet jedu, ktorý útočník môže umiestniť, nie jeho kontrolu nad slotmi, na ktorých záleží.** Ohraničenie úložiska protivníka neobsiahne.

## Čo naozaj robiť

Ak prevádzkuješ pamäť agenta, návrhové pravidlá, ktoré toto prežijú, sú konkrétne:

- **Zápis lacný, vplyv drahý.** Nechaj čokoľvek uložiť do vlastného namespace takmer zadarmo; vyžaduj korroboráciu *odlišnými, externe ukotvenými* stranami skôr, než spomienka môže ovplyvniť rozhodnutie *mimo* svojho namespace. Toto je kontrola, ktorá prežije MINJA-štýlový zápis vnútri autentifikovanej session — identitná brána *na zápise* nikdy nespáli, ale latka na cross-scope *vplyv* stále žiada nezávislú podporu.
- **Počítaj korroboráciu cez ukotvené kľúče, nie zdrojové reťazce.** „Dva nezávislé zdroje" je zadarmo, ak útočník pomenuje oba (túto influence bránu sme [merali samostatne](agent-memory-poisoning-influence-gate.html)). Sprav, aby každý svedok stál odlišný overený kľúč — s vedomím, že to *ohraničuje*, nie eliminuje.
- **Autentifikuj supersession.** Retire-on-write je útočný vektor; nechaj stiahnuť kľúč len autorizovaného, atestovaného pisateľa.
- **Drž `credit()` externý.** Signál úspechu, ktorý agent môže udeliť vlastnej pamäti, je Goodhartova návnada. Vydávaj outcome-credit z aplikácie na vyriešenej reálnej práci, nikdy nie z ničoho odvoditeľného z vyvolaného obsahu.
- **Poznaj strop.** Nič z tohto neoceňuje pravdivosť. Otvorený problém je spraviť *koordinovanú-ale-pravú* korroboráciu drahou — stake, ktorý prepadne, keď je spomienka neskôr vyvrátená; testy nezávislosti na korroborátoroch; outcome-viazaný credit, ktorý znižuje standing kotiev, ktorých spomienky ďalej zlyhajú.

Posledná odrážka je miesto, kde sedí [evidence-grade ratchet](https://github.com/DanceNitra/agora/blob/main/research/probes/evidence_grade_ratchet.py) inspeximus 0.6.0 — postavený na operacionalizáciu [nášho sebaauditu 32 publikovaných zistení](labels-failed-more-than-measurements.html) — a je zámerne skromný: konfidencia a novosť tvrdenia sa môžu pohnúť len nahor pri *externej* ratifikačnej udalosti, nikdy self-priradene, a každá priečka stojí odlišnú identitu. Oceňuje **kto tvrdenie ratifikoval a či bola ratifikácia externá** — nie či je tvrdenie pravdivé. Shippujeme ho ako podlahu s označeným stropom, nie ako riešenie Veracity Gap.

## Falzifikátor

Ak by bol kolaps štyroch obrán reálnym empirickým prekvapením a nie ukážkou zdieľaného predpokladu, aspoň jedna obrana by padla *bez toho*, aby útočník dostal signál, podľa ktorého rozhoduje — žiadna nepadá; to je nález, nie bug v ňom. Ak by proveniencia zatvorila Veracity Gap, MINJA — útok s pravou provenienciou — by voči provenienčnej kotve zlyhal; nezlyháva. Ak by „overená identita" útok eliminovala, naša vlastná dvoj-kľúčová brána by pri k=2 vydržala; prejde. Každé z toho je overiteľné v [spustiteľnom probe](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py).

## Čestné limity

Toto je **náš vlastný kód, red-teamovaný našimi vlastnými subagentmi** — štylizovaná ukážka na jednom stacku, nie benchmark, a nie nezávislé preskúmanie. Štyri „porážky" sú pravdivé z konštrukcie a testujú každý primitív v izolácii, nie vrstvený systém, ktorý shippujeme. „Proveniencia je to, čo prežije" je **už učebnicové** — Sybil, CRDT, Goodhart a literatúra bezpečnosti proveniencie to hovoria, a nedávne prehľady bezpečnosti pamäte LLM agentov už menujú write-time provenienciu ako governance vrstvu; my systematizujeme a jediný originálny artefakt je jednotný prehľad a jeho jedna meraná rampa. Rámovanie „jednej spoločnej chyby počítanej štyrikrát" je **domnienka zo štyroch ručne postavených ukážok**, nie teoréma. Ber to celé ako čestný inžiniersky doklad s dokresleným stropom.

## FAQ

**Zlyhali tvoje obrany?** Štyri *primitíva* zlyhajú v izolácii, keď útočník dodá presný signál, ktorému každé verí — čo je pointa: iba-obsahové signály sú spoofnuteľné tým, kto obsah píše. inspeximus ich shippuje vrstvené a vrstvená konfigurácia nie je to, čo tu padá. Čítaj to ako návrhovú lekciu, nie hlásenie o prieniku.

**Takže odpoveď je overená identita?** Nie — to prestrelí zdroj. Douceur menuje *dva* úniky (dôveryhodná autorita alebo vzácny zdroj) a cesta vzácnosti Sybilov len *ohraničí*. Našu vlastnú bránu prejde útočník s dvomi kľúčmi. Identita/cena zdvíha útočníkovu cenu; nezatvára dvere.

**Tak čo je skutočný limit?** Proveniencia overuje *zdroj*, nie *pravdu*. MINJA vloží jed zvnútra legitímnej autentifikovanej session — pravá proveniencia, falošný obsah — a preplachtí cez provenienčnú kotvu. Oceniť *pravdivosť*, nielen provenienciu, je nevyriešený problém.

**Je niečo z tohto nové?** Nie, a hovoríme to. Každý mechanizmus je pomenovaný výsledok (Sybil, LWW-register, Goodhart, adaptívna evaluácia, MINJA, PoisonedRAG) a „proveniencia je prežívajúca kotva" je už zosumarizované. Prínos je spustiteľný, seba-kritický adaptívny red-team shippnutého stacku, so stropom označeným, nie skrytým.

**Prečo publikovať výsledok, ktorý väčšinou limituje tvoj vlastný produkt?** Lebo čestný strop *je* tá užitočná vec. Pitch o bezpečnosti pamäte, ktorý ti nepovie, že proveniencia nekúpi pravdu, ti predáva falošný pocit bezpečia — presne tú vec, ktorej má adaptívna evaluácia zabrániť.

---
*Adaptívny red-team štyroch shippnutých inspeximus obrán; štylizovaná ukážka na jednom stacku, nie benchmark. Spustiteľné: [adaptive_defenses.py](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py) a [evidence-grade ratchet 0.6.0](https://github.com/DanceNitra/agora/blob/main/research/probes/evidence_grade_ratchet.py). Prior art, na ktorom staviame: Douceur 2002 (The Sybil Attack); Shapiro a spol. 2011 (Conflict-free Replicated Data Types / LWW-Register); Strathern 1997 (formulácia Goodhartovho zákona); Athalye a spol. 2018 (arXiv:1802.00420) a Tramèr a spol. 2020 (arXiv:2002.08347) (adaptívna evaluácia); MINJA (arXiv:2503.03704, NeurIPS 2025); PoisonedRAG (arXiv:2402.07867, USENIX Security 2025); Yu a spol. SybilGuard 2006 / SybilLimit 2008 a Cao a spol. SybilRank 2012; Pan, Stakhanova & Ray 2023 (prehľad data provenance v bezpečnosti v ACM Computing Surveys). Mechanizmy sú učebnicové; jednotný adaptívny prehľad a označený strop sú naše.*
