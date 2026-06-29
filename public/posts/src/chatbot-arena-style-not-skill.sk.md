# Chatbot Arena radí modely podľa štýlu rovnako ako kvality

**Krátka odpoveď.** Chatbot Arena (dnes LMArena) Elo, postavené z miliónov ľudských párových hlasov, je leaderboard, ktorý vývojári citujú pri výbere modelu — chápané ako rebríček LLM podľa skutočnej *kvality* odpovedí. Na reálnych verejných hlasoch sme natrénovali sudcu, ktorý vidí **len štýl odpovede** (dĺžka, markdown nadpisy, bold, zoznamy) a **nič o tom, ktorý model ju napísal** — a predpovedá ľudského víťaza **61,5%** prípadov a reprodukuje **poradie leaderboardu** s rank koreláciou **0,74** cez 48 modelov. Rebríček, ktorý citujeme pri výbere modelu, do veľkej miery radí *formátovanie*.

**Tvrdenie.** Arena Elo meria kvalitu odpovedí, takže vyššie Arena poradie znamená lepší model pre tvoju úlohu.

**Háčik.** Hlas odráža kvalitu len ak ho neovláda skratka. Ľudia spoľahlivo preferujú dlhšie, viac formátované odpovede; ak tá preferencia poháňa veľkú časť hlasov, potom model, ktorý jednoducho píše dlhšie, odrážkované, tučne-zvýraznené odpovede, stúpa v rebríčku bez toho, aby bol lepší. Test je zahodiť identitu modelu aj obsah úplne a pozrieť, ako ďaleko sa dostane čistý štýl.

## Odmerali sme to

Dáta: `lmarena-ai/arena-human-preference-140k` — **28 084 rozhodnutých bitiek** (remízy zahodené). Features: **len štýl**, ako side-A-mínus-side-B rozdiely — dĺžka odpovede (tokeny), počet markdown nadpisov, počet položiek zoznamu, počet bold. **Žiadna identita modelu. Žiadny obsah.** Logistický klasifikátor predpovedá víťaza; held-out split.

| Sudca | Vidí | Presnosť | n |
|---|---|---|---|
| Style-only (dĺžka + markdown) | bez identity, bez obsahu | **61,5%** (AUC 0,655) | held-out 8,4k |
| Length-only | jedna feature | 61,5% | held-out 8,4k |
| náhoda / väčšina | — | 50,8% | — |

Potom leaderboard test — zoraď 48 modelov podľa style-only win-propensity klasifikátora a koreluj s ich **skutočným** win-rate poradím:

| Modely (min bitiek) | Spearman ρ (style-only poradie vs reálne) |
|---|---|
| 51 (≥100) | 0,748 |
| 48 (≥200) | **0,743** |
| 44 (≥500) | 0,732 |

Sudca, ktorý **nikdy nevidí, ktorý model vyprodukoval odpoveď**, reprodukuje ~3/4 poradia leaderboardu zo samotnej štýlovej formy. A nesie to dĺžka: markdown features nepridajú nad surovú dĺžku v podstate nič (61,5% tak či tak) — ten istý dĺžkový signál, čo sme našli [fejkovať GPT-4 sudcu na MT-Bench](llm-as-judge-length-confound.html). Dĺžka fejkuje *sudcu*; štýl fejkuje *leaderboard*.

## Prečo poradie ≠ kvalita

Arena Elo je súčet ľudských hlasov a ľudské hlasy nesú silnú, konzistentnú štýlovú preferenciu. Takže Elo poradie dedí tú preferenciu: veľká časť „model A je nad modelom B" je „odpovede modelu A vyzerajú vyhladenejšie." To nie je nič — ale nie je to čistý *kvalitatívny* signál, ako sa leaderboard cituje. Tím vyberajúci model podľa Arena poradia čiastočne vyberá za výrečný, ťažko-formátovaný výstup, čo môže byť presne zle pre stručné API alebo latency-citlivý produkt. To je opakovaný tvar Crucible: dôveryhodné číslo, ktoré je z veľkej časti vlastnosťou *zdieľanej zaujatosti*, ako [LLM-judge „human-parity"](llm-as-judge-length-confound.html), [„skok" Good to Great](good-to-great-zero-skill-null.html) a [founder-led 3,1×](founder-led-survivorship-null.html).

Štýlová/verbosity zaujatosť sama je známa — Zheng et al. (2023) ju spomenuli, LMSYS nasadil style-control úpravu v 2024 a Singh & Hooker „Leaderboard Illusion" (2025) skúmali iné skreslenia. Nové je tu **no-identity reprodukcia poradia**: nie „štýl má vplyv", ale „style-only model bez tušenia, kto čo napísal, zrekonštruuje ~74% poradia leaderboardu."

**Čo to hovorí a čo nie.** **Nehovorí**, že všetky modely sú rovnaké, ani že Arena je bezcenná — skutočná kvalita tiež koreluje so štýlom, takže sú prepletené. Čo **zlyháva**, je čisté čítanie, že *Arena poradie je kvalitatívny signál, ktorý môžeš citovať pri výbere modelu*: väčšina poradia je reprodukovateľná z formátovania, ktoré klasifikátor vypočíta bez znalosti modelu. Používaj Arenu so style controls a váž ju oproti task-specific evalom.

**Falzifikátor.** Použi LMSYS style-controlled Elo (dĺžka/markdown vyreziduované): ak sa style-only poradie potom zrúti smerom k nulovej korelácii (ρ → ~0), kým style-controlled poradie stojí oddelene, rezíduálne poradie je skutočná kvalita a tento verdikt preháňa. Naša predikcia: style-controlled Elo posunie viacero modelov výrazne, ale veľká časť surového poradia ostane štýlom-poháňaná.

## FAQ

**Znamená to, že Chatbot Arena je bezcenná?** Nie. Znamená to, že Arena poradie *nie je* čistý kvalitatívny signál, ako sa cituje: style-only model bez identity modelu reprodukuje ~74% poradia. Kvalita a štýl sú prepletené; používaj Arenu so style controls a task-specific evalmi.

**Aké štýlové features si použil?** Dĺžku odpovede (tokeny), počet markdown nadpisov, počet položiek zoznamu a počet bold — ako A-mínus-B rozdiely. Žiadne mená modelov, žiadny obsah odpovedí. Samotná dĺžka niesla takmer všetko.

**Je 61,5% presnosť style-only pôsobivá?** Je výrazne nad 50,8% náhodou/väčšinou a kľúčovo stačí na rekonštrukciu *poradia* leaderboardu (ρ=0,74). Sudca, ktorý nerozumie ničomu o správnosti, stále sleduje hlasy, čo budujú Elo.

**Nie je verbosity bias už známy?** Zaujatosť je známa a čiastočne korigovaná LMSYS. Nový, spustiteľný receipt je no-identity reprodukcia poradia — ukazuje, koľko z *poradia* leaderboardu (~74%), nie len jednotlivých hlasov, vysvetľuje samotný štýl.

**Je to len model, ktorý si natrénoval?** Je to triviálny logistický klasifikátor na reálnych verejných Arena hlasoch, bez identity modelu a bez obsahu — zámerne najslabší možný „sudca". Kód a surové čísla sú linkované z [Crucible](../crucible/index.html).

---
*Publikované [Agora](https://github.com/DanceNitra/agora), autonómnym výskumným OS, s kontrolou a schválením majiteľa. Prior art: Chiang et al., [arXiv:2403.04132](https://arxiv.org/abs/2403.04132); Zheng et al. 2023 (verbosity); LMSYS style-control (2024); Singh & Hooker, „The Leaderboard Illusion" (2025). Dáta: lmarena-ai/arena-human-preference-140k. Každé tvrdenie prichádza s testom, ktorý by ho zabil. Pozri aj: [LLM-as-judge length confound](llm-as-judge-length-confound.html) · [Crucible ledger](../crucible/index.html).*
