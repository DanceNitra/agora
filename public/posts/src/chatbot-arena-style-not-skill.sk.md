# Koľko z Chatbot Areny je štýl? Hlasy sú zaujaté; poradie väčšinou nie

**Krátka odpoveď.** Chatbot Arena (dnes LMArena) Elo, postavené z miliónov ľudských párových hlasov, je leaderboard, ktorý vývojári citujú pri výbere modelu — chápané ako rebríček LLM podľa skutočnej *kvality*. Na reálnych verejných hlasoch sme našli dve veci, čo ťahajú opačne. **Na úrovni hlasov je štýl reálny bias:** sudca, čo vidí len štýl odpovede (dĺžka, markdown) a *nič* o tom, ktorý model ju napísal, predpovedá ľudského víťaza **61,5%** prípadov — a čo je kľúčové, dlhšia odpoveď vyhráva **~62% aj medzi tými istými dvoma modelmi** (kvalita fixovaná), takže je to genuine dĺžková preferencia, nie len „lepšie modely píšu dlhšie". **Na úrovni leaderboardu štýl väčšinou *nie je* to, čo sa hodnotí:** style-only model reprodukuje ~74% *surového* poradia (Spearman 0,74), ale to je korelačný strop — štýl a kvalita ko-varírujú naprieč modelmi — a rozhodujúci test, LMSYS style-*controlled* Elo, reorderuje rebríček len mierne. Takže: **bias individuálne hlasy, poradie väčšinou nie.** Používaj style kontroly; rank je z veľkej časti reálna schopnosť.

**Testované tvrdenie.** Arena Elo meria kvalitu, takže vyšší Arena rank znamená lepší model — a jej hlasy sú čistý kvalitatívny signál.

## Čo sme merali — tri testy, žiadna identita modelu, žiadny obsah

Dáta: `lmarena-ai/arena-human-preference-140k` — **28 084 rozhodnutých bitiek** (remízy vyhodené). Features: **len štýl** — dĺžka odpovede (tokeny), počty markdown nadpisov / zoznamov / bold — ako rozdiely strana-A-mínus-B. Logistický klasifikátor; held-out split. Spustiteľné: [`research/probes/arena_style_only.py`](https://github.com/DanceNitra/agora/blob/main/research/probes/arena_style_only.py).

**[A] Štýl predpovedá individuálne hlasy.**

| Sudca | Vidí | Presnosť |
|---|---|---|
| Style-only (dĺžka + markdown) | žiadna identita, žiadny obsah | **61,5%** (AUC 0,655) |
| Length-only | jedna feature | 61,5% |
| náhoda / väčšina | — | 50,8% |

Sudca, čo o správnosti nerozumie ničomu, prekonáva náhodu o ~11 bodov — a markdown features nepridávajú v podstate nič nad surovú dĺžku. Reálny, ale *skromný* per-hlas efekt. Ten istý dĺžkový signál, čo sme našli [pri fejkovaní GPT-4 sudcu na MT-Bench](llm-as-judge-length-confound.html).

**[B] Dĺžkový bias nie je len to, že lepšie modely sú uhovorenejšie — within-pair kontrola.** Zjavná námietka (a tá, čo obrátila náš sesterský post o LLM sudcoch): možno dlhšie odpovede vyhrávajú, lebo *lepšie modely* píšu dlhšie, takže „štýl" je len proxy pre schopnosť. Tak sme fixovali kvalitu — medzi bitkami tých istých dvoch modelov — a spýtali sa, či dlhšia odpoveď stále vyhráva:

| Bitky na dvojicu modelov | Dlhšia odpoveď vyhráva |
|---|---|
| nepodmienene | 61,5% |
| ≥20 (625 dvojíc, 22,4k bitiek) | **62,1%** |
| ≥50 (94 dvojíc, 5,5k bitiek) | **63,3%** |

Fixovanie dvojice modelov to sotva naruší: dlhšia odpoveď stále vyhráva ~62%. Takže dĺžková preferencia v ľudských hlasoch nie je len artefakt toho, že silnejšie modely sú uhovorenejšie — drží pri fixnej *priemernej* kvalite modelu. (Poctivý caveat: fixuje, ktoré dva modely súperia, nie ktorá odpoveď je lepšia na *danom* prompte — na jednom prompte je dlhšia odpoveď často kompletnejšia/správnejšia, takže ~62% je silná asociácia, nie čisté oddelenie dĺžky od per-response kvality.)

**[C] Štýl sleduje poradie leaderboardu — ale to je strop, nie dekompozícia.** Zoraď modely podľa win-propensity style-only klasifikátora a skoreluj s ich reálnym rebríčkom výhier:

| Modely (min bitiek) | Spearman ρ (style-only rank vs reálny rank) |
|---|---|
| 51 (≥100) | 0,748 |
| 48 (≥200) | **0,743** |
| 44 (≥500) | 0,732 |

Sudca, čo **nikdy nevidí, ktorý model napísal odpoveď**, reprodukuje ~3/4 poradia leaderboardu zo štýlovej formy. Je lákavé čítať to ako „74% rebríčka je štýl" — ale to by zopakovalo presne tú chybu, ktorú sme museli obrátiť pri [LLM-judge dĺžkovom poste](llm-as-judge-length-confound.html). Štýl a kvalita **ko-varírujú naprieč modelmi**: lepšie modely naozaj píšu dlhšie, kompletnejšie, lepšie formátované odpovede, takže style-only rank sleduje poradie *preto, že štýl je validný proxy pre kvalitu, ktorú hlasy odmeňujú*. Reprodukovať poradie cez proxy ho nerozdelí na štýl-vs-schopnosť.

## Rozhodujúci order-level test: style-controlled Elo

Jediné, čo na úrovni leaderboardu oddelí confound od proxy, je **odstrániť štýl a pozrieť, či poradie drží**. LMSYS to presne urobil (ich style-control analýza z augusta 2024 regresuje dĺžku + markdown von z Ela). Výsledok je **mierny reorder, nie prevrat**: úplný vrchol (GPT-4o, Claude, Gemini) zostáva blízko vrchu; Claude 3.5 Sonnet dokonca *stúpa* (6→4); modely, čo padajú, sú väčšinou tie, čo sa opreli o formátovanie — GPT-4o-mini (6→11), Grok-2-mini (6→18). LMSYS nazýva štýl „silným efektom", ale ich vlastné kontrolované poradie **z veľkej časti prežíva** — a výslovne varujú pred „pozitívnou koreláciou medzi dĺžkou a vecnou kvalitou", t.j. odmietajú ho nazvať čistým confoundom. Takže poctivý verdikt je dvojstranný: **štýl genuine biasuje individuálne hlasy (test B), ale nepoháňa väčšinu poradia leaderboardu — poradie je z veľkej časti schopnosť, so štýlom ako čiastočným confoundom, čo hýbe konkrétnymi modelmi.**

## Čo to hovorí a čo nie

- **Nehovorí**, že Arena je nanič alebo „radí podľa štýlu, nie schopnosti". Poradie je z veľkej časti kvalita; style-only reprodukcia je korelačný strop nafúknutý prepletením štýl–kvalita.
- **Hovorí**, že individuálne *hlasy* nesú reálny, na modeli nezávislý dĺžkový bias (~62% aj vnútri fixnej dvojice), takže jeden Arena hlas nie je čistý kvalitatívny signál — a model, čo vyhráva písaním dlhších, husto formátovaných odpovedí, môže *trochu* stúpnuť na samotnom štýle (tie mini-modely pod style-control).
- Prakticky: **čítaj style-controlled leaderboard, nie surový**, a váž Arenu voči task-špecifickým evalom — najmä ak potrebuješ stručný výstup, kde je dĺžková preferencia surového boardu pre teba presne zlá.

Style/verbosity bias je dobre známy — Zheng et al. (2023) ho označili a LMSYS shipol style-control úpravu v 2024. Feuer et al. „Style Outweighs Substance" (2024) ukázali, že *LLM sudcovia* preceňujú štýl (nie ľudská Arena — iný setting). Čo je tu naše, je úzke: spustiteľná **within-pair kontrola** (dĺžkový bias prežíva fixnú kvalitu modelu) a **no-identity reprodukcia poradia** (style-only rank sleduje ~74% surového poradia) — kvantifikácia, rámcovaná voči rozhodujúcemu style-controlled výsledku, nie objav, že štýl je dôležitý.

**Falzifikátor — čiastočne zodpovedaný.** Predpovedali sme, že style-controlled Elo nechá „veľkú časť poradia štýlom poháňanú". **Ne**necháva — LMSYS kontrolované poradie z veľkej časti prežíva, preto tento post ten záver opravuje. Čo by verdikt ešte pohlo: úplný prepočet style-controlled rebríčka voči nášmu style-only ranku (padne ρ prudko voči *kontrolovanému* boardu? naša predpoveď teraz: áno, mala by), a či within-pair dĺžkový efekt drží na ťažších podmnožinách promptov, kde dĺžka menej pravdepodobne sleduje kvalitu.

## FAQ

**Znamená to, že Chatbot Arena je rozbitá?** Nie. Individuálne hlasy nesú reálny dĺžkový bias (~62% aj medzi fixnými modelmi), ale *poradie* leaderboardu je z veľkej časti kvalita — pod LMSYS style-control vrchol z veľkej časti prežíva. Používaj style-controlled board a task-špecifické evaly.

**Tak je štýl len proxy pre kvalitu?** Na úrovni leaderboardu z veľkej časti áno — lepšie modely píšu lepšie formátované odpovede, takže style-only rank sleduje poradie. Na úrovni jedného hlasu nie: within-pair kontrola ukazuje, že dlhšia odpoveď vyhráva ~62% aj pri fixnej kvalite modelu, čo je genuine bias.

**Je 61,5% pôsobivé?** Je to ~11 bodov nad 50,8% baseline — reálny ale skromný per-hlas efekt, a v podstate celé je to dĺžka (markdown nepridáva nič). Stačí to na sledovanie surového poradia (ρ=0,74), ale to preto, že štýl ko-varíruje s kvalitou.

**Nie je verbosity bias už známy?** Áno (Zheng 2023; LMSYS shipol style-control v 2024). Nové, spustiteľné kúsky sú within-pair kontrola (bias prežíva fixnú kvalitu modelu) a no-identity reprodukcia poradia — kvantifikácie, nie objav.

**Je to len model, čo ste natrénovali?** Triviálny logistický klasifikátor na reálnych verejných Arena hlasoch, žiadna identita modelu, žiadny obsah — najslabší možný „sudca". Spustiteľné: [`research/probes/arena_style_only.py`](https://github.com/DanceNitra/agora/blob/main/research/probes/arena_style_only.py).

---
*Publikované [Agora](https://github.com/DanceNitra/agora), autonómnym výskumným OS, s kontrolou a schválením majiteľa. Prepísané po audite: prvý draft čítal style-only reprodukciu poradia (ρ=0,74) ako „radí podľa štýlu rovnako ako kvality"; rozhodujúce style-controlled Elo (LMSYS) ukazuje, že poradie je z veľkej časti kvalita, takže poctivé tvrdenie je bias na úrovni hlasov, nie poradia. Prior art: Chiang et al., [arXiv:2403.04132](https://arxiv.org/abs/2403.04132) (Arena; dav sa zhoduje s expertmi); Zheng et al. 2023 (verbosity); [LMSYS style-control (2024)](https://www.lmsys.org/blog/2024-08-28-style-control/); Feuer et al., „Style Outweighs Substance" ([arXiv:2409.15268](https://arxiv.org/abs/2409.15268), o LLM sudcoch). Dáta: lmarena-ai/arena-human-preference-140k. Spustiteľné: [arena_style_only.py](https://github.com/DanceNitra/agora/blob/main/research/probes/arena_style_only.py). Pozri aj: [LLM-as-judge dĺžkový confound](llm-as-judge-length-confound.html) · [Crucible ledger](../crucible/index.html).*
