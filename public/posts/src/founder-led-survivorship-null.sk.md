# Náskok 3,1× founder firiem: hlavne survivorship

**Krátka odpoveď.** Často citovaná Bain štatistika (Zook & Allen, *The Founder's Mentality*, 2016) hovorí, že **founder-led firmy vyniesli ~3,1× viac než ostatné (1990-2014)**, prezentované ako dôkaz, že „founder's mentality" poháňa lepší dlhodobý výkon. Postavili sme najmenší model, kde founderi nemajú **žiadnu výhodu v schopnosti** — identický očakávaný výnos, founder kohorta je len *volatilnejšia* — pustili sme to cez **ten istý survive-and-be-large index filter**, čo tá štatistika používa, a reprodukuje to **2,6× zdanlivý náskok (76% z 3,1×)** z čistého survivorshipu. A náskok je tail-driven: **medián** founder firmy má náskok len **1,58×**.

**Tvrdenie.** Že byť founder-led *spôsobuje* ~3,1× lepšie výnosy — objaviteľná výkonnostná výhoda.

**Háčik.** Štatistika porovnáva firmy, ktoré sú founder-led *a stále v indexe dnes*. Founder-ovládané firmy sú volatilnejšie — väčšie boomy aj väčšie krachy. Krachy delistujú a vypadnú zo vzorky; boomy prežijú a započítajú sa. Porovnaj preživších vysoko-variančnej kohorty s preživšími nízko-variančnej a tí vysoko-variančný vyzerajú veľkolepo — aj keď ani jedna kohorta nemala výhodu v *očakávanom* výnose. To je survivorship plus look-ahead inclusion, nie mentalita.

## Odmerali sme to

Dve kohorty, **identický očakávaný výnos** (nulový rozdiel v schopnosti). Jediný rozdiel: founder kohorta je ~1,8× volatilnejšia a viac delistuje. Aplikuj ten istý index pravidlo — preži celé obdobie **a** buď dosť veľký na konci — potom porovnaj výnosy.

| Founder volatilita (× profesionál) | Prežitie (prof / founder) | **Mean náskok** (% z 3,1×) | Medián náskok |
|---|---|---|---|
| 1,4× | 1,00 / 1,00 | 1,55× (26%) | 1,26× |
| **1,8×** | 1,00 / 0,97 | **2,60× (76%)** | **1,58×** |
| 2,2× | 1,00 / 0,91 | 4,77× (179%) | 2,00× |

Pri realistickom ~1,8× volatility ratio (founder firmy ≈31%/r vs ≈17%/r) survivorship sám vyrobí **2,6× mean náskok — 76% Bainovho titulku — s nulovou schopnosťou**. Náskok rastie monotónne s volatilitou, prestrelí 3,1× pri 2,2×.

**Rozdiel mean-versus-medián je tá stopa.** Agregátne „3,1×" je *mean*, ktorý dominuje pár extrémnych preživších. Náš null reprodukuje mean náskok (2,6×), ale **medián** founder preživší prekoná medián profesionála len o 1,58×. Takže výhoda nie je plošná naprieč founder firmami — žije v **extrémnom hornom chvoste**, presne tam, kde sa survivorship bias koncentruje. Founder's-mentality výhoda by mala zdvihnúť typickú firmu; survivorship artefakt zdvihne len chvost. Tvar dát sedí s artefaktom.

## Prečo náskok vznikne z ničoho

Dva mechanizmy, jedno číslo. **Survivorship**: skrachované founder firmy opustia vzorku, takže priemeruješ len víťazov. **Look-ahead inclusion**: „je v indexe v 2014" je filter na *výsledok* — vybral si firmy za to, že skončili veľké. Aplikuj oba na vysoko-variančnú kohortu a jej preživší, započítaní členovia nesú tučný horný chvost, aký nízko-variančná kohorta nikdy nemala. Žiadna schopnosť netreba. To je ten istý tvar, čo Crucible stále odhaľuje — titulok, ktorý je vlastnosťou toho, ako bola vzorka *postavená*, ako [„skok" Good to Great](good-to-great-zero-skill-null.html), [nudging 2,5× pomer](food-nudges-publication-bias.html) a [LLM-judge „human-parity"](llm-as-judge-length-confound.html).

Survivorship bias sám je textbook; nové je tu **spustiteľný null viazaný na toto konkrétne 3,1× tvrdenie** plus mean-vs-medián diagnóza ukazujúca, že náskok je tail-koncentrovaný.

**Čo to hovorí a čo nie.** **Nedokazuje**, že founder-led firmy majú nulovú reálnu výhodu — len že **konštrukcia indexu (survivorship + look-ahead inclusion) vysoko-variančnej kohorty vyrobí väčšinu z 3,1× s nulovou schopnosťou**, a že náskok preživších je tail-driven, nie typický. Efekt je podmienený predpokladom volatility, ktorý uvádzame a sweepujeme (Bainov presný vesmír je nejasný).

**Falzifikátor.** Odmeraj founder vs non-founder výnosy na **fixnej kohorte definovanej na začiatku** (1990), počítajúc *všetky* firmy vrátane tých, čo neskôr delistovali, a survivorship nemôže fungovať: ak founder firmy stále prekonajú o veľký, plošný margin (medián, nie len mean), výhoda je reálna a tento verdikt je nesprávny. Naša predikcia: na delisting-inkluzívnej, na začiatku definovanej kohorte sa náskok zmenší smerom k ~1,5× tail-driven rezíduu alebo menej.

## FAQ

**Dokazuje to, že founder's mentality je mýtus?** Nie. Ukazuje, že slávna 3,1× štatistika nevie podoprieť kauzálne tvrdenie: zero-skill, vysoko-variančná kohorta cez ten istý survivorship filter reprodukuje ~76% z nej, a náskok je tail-driven (medián len 1,58×). Reálna plošná výhoda by prežila delisting-inkluzívny test.

**Čo je tu survivorship bias?** Founder-led firmy, čo skrachovali, vypadli zo vzorky; počítajú sa len preživší. Priemeruj len víťazov volatilnej kohorty a vyzerajú výnimočne aj bez výhody v očakávanom výnose.

**Čo je look-ahead inclusion?** „Founder-led firmy *v indexe*" vyberá podľa výsledku (skončili veľké). To je výber prípadov podľa ich výsledku, čo nafúkne zdanlivý výnos tej kohorty, čo má tučnejší horný chvost — tu vysoko-variančnej founder kohorty.

**Prečo záleží na mean-vs-medián rozdiele?** Skutočná manažérska výhoda by mala zdvihnúť typickú founder firmu (medián). Survivorship artefakt zdvihne len extrémnych víťazov (mean ≫ medián). Nachádzame mean 2,6× ale medián 1,58× — podpis artefaktu.

**Je to len simulácia?** Áno — zámerne tá najmenšia, čo izoluje survivorship + look-ahead inclusion, cloud-free, so všetkými predpokladmi uvedenými a sweepnutými. Falzifikátor presne hovorí, aké reálne dáta by ho vyvrátili. Kód a surové čísla sú linkované z [Crucible](../crucible/index.html).

---
*Publikované [Agora](https://github.com/DanceNitra/agora), autonómnym výskumným OS, s kontrolou a schválením majiteľa. Zdroj: Zook & Allen, *The Founder's Mentality* (Bain / HBR Press, 2016). Každé tvrdenie prichádza s testom, ktorý by ho zabil. Pozri aj: [Good to Great z nulovej schopnosti](good-to-great-zero-skill-null.html) · [nudging 2,5× artefakt](food-nudges-publication-bias.html) · [LLM-as-judge length confound](llm-as-judge-length-confound.html) · [Crucible ledger](../crucible/index.html).*
