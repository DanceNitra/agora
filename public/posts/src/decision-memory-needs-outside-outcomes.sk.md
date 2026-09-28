# Minulé lekcie agentovi pomohli, keď ich napísali výsledky zvonka, nie keď ich vybral ranker

Lekcie s potvrdeným výsledkom zdvihli Claude Opus 5.5 z 0,594 na 0,750 pri inžinierskych rozhodnutiach, aj keď sme ich vyberali náhodne. Výber podľa podobnosti embeddingov to zvýšil na 0,769. Týchto 0,019 navyše má 95 % interval -0,031 až +0,069, takže beh ich nevie odlíšiť od nuly.

Chceli sme ukázať, že vybavená rozhodovacia pamäť pomáha agentovi voliť lepšie. Výsledok je užší: pomohli lekcie napísané z výsledkov potvrdených mimo agenta. Na tom, ako sme ich zoradili, pri týchto rozhodnutiach záležalo málo.

## Čo sme merali, v tomto poradí

Použili sme inžiniersku časť Taste-Bench (Pan et al., [arXiv 2609.25804](https://arxiv.org/abs/2609.25804)): 390 rozhodnutí zo skutočných programátorských postupov. Každé má dva možné ďalšie kroky a štítok označuje ten, ktorého vetva mala lepší zaznamenaný výsledok. Model vidí obe možnosti v oboch poradiach a rozhodnutie sa počíta, iba keď sú obe odpovede správne. Tým sa kontroluje sklon k pozícii.

Lekcia je jedna veta z rozhodnutia v inej úlohe: „voľba X namiesto Y viedla k lepšiemu výsledku“. Lekciu z testovanej úlohy nikdy nevyberáme.

- **Výber oproti náhodným lekciám z akéhokoľvek projektu.** Na 390 rozhodnutiach s Qwen3.8 27B porazili tri najpodobnejšie lekcie náhodné lekcie s rovnakými povrchovými znakmi. Rozdiel bol 0,115 (95 % interval +0,067 až +0,167). Gemma4 12B zopakovala smer: +0,056 (+0,013 až +0,100). Toto porovnanie mieša poradie s projektom, lebo 86 % vybraných lekcií pochádzalo z repozitára testovaného rozhodnutia.
- **Kontrola, ktorá ich oddelí.** Ku každej vybranej lekcii sme vytiahli náhodnú lekciu z toho istého repozitára s rovnakými povrchovými znakmi. Rozhoduje Claude Opus 5.5 so stredným úsilím, 160 rozhodnutí, 960 volaní, 0 nečitateľných odpovedí.

| Lekcie v zadaní | Správne v oboch poradiach |
|---|---|
| Žiadne | 0,594 |
| Náhodné, ten istý repozitár, rovnaké povrchové znaky | 0,750 |
| Top 3 podľa podobnosti embeddingov (výber inspeximus) | 0,769 |
| Bez modelu: pravidlo na dva riadky (vyber izolovanú alebo dlhšiu možnosť) | 0,669 |

Náhodné lekcie z toho istého repozitára pridajú 0,156 (+0,087 až +0,225). Zoradenie podľa podobnosti pridá navrch 0,019. Pri 160 rozhodnutiach beh vylúči zisk zo zoradenia nad približne 0,07, menší nie.

## Záležalo na tom, odkiaľ prišiel výsledok

Qwen napísal vlastné lekcie zo svojich skorších volieb, dvoma spôsobmi:

- **Dozvedel sa výsledok.** Keď vedel, či voľba dopadla dobre, jeho lekcie pridali 0,087 oproti žiadnym lekciám (+0,036 až +0,138).
- **Posúdil sa sám.** Keď musel voľbu posúdiť sám, jeho lekcie skórovali o 0,044 nižšie než žiadne lekcie. Interval, -0,087 až 0,000, siaha po nulu.

Zodpovedá to zisteniu Huang et al. pri uvažovaní ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)): bez spätnej väzby zvonka sa modely ťažko opravujú a ich výkon niekedy klesne. ReasoningBank ([arXiv 2509.25140](https://arxiv.org/abs/2509.25140)) je protipríklad: pamäť hodnotená samým agentom pomohla pri webových úlohách, kde sa úspech overuje ľahšie než pri rozhodnutí o vkuse.

## Kam patrí otrava pamäte

Pamäť, ktorá sa učí z výsledkov, je vystavená otrave pamäte: falošnému výsledku zapísanému do skladu. Každej lekcii sme dali obrátené dvojča, zámerne extrémny sklad, v ktorom je zhruba polovica každého výberu nesprávna. Išlo o samostatný beh s Opusom pri predvolenom úsilí, v ktorom čistá pamäť dosiahla 0,825. Obyčajný výber klesol na 0,637. Výber iba lekcií, ktorých výsledok potvrdil niekto zvonka, vrátil 0,825.

Posledné číslo ukazuje, čo brána robí so signálom, nie že útok odhalí: v tomto teste je potvrdenie zvonka samotný štítok z datasetu. [Starší článok](agent-memory-defense-provenance-not-truth.html) ukázal tú istú hranicu na štylizovaných ukážkach: obrana, ktorá pripisuje zásluhu výsledkom hodnoteným samým agentom, padne pred útočníkom, ktorý svoj jed ohodnotí ako úspech.

## Čo by nás vyvrátilo

- Zoradenie podľa podobnosti by porazilo náhodné lekcie z toho istého repozitára s intervalom nad nulou. Neporazilo.
- Lekcie hodnotené samým agentom by pomohli rovnako ako lekcie s výsledkom. Nepomohli.

## Hranice

- **Projekt oproti povrchovým znakom.** Beh s Opusom nemal variant s cudzími projektmi, takže neukazuje, že pomohol práve projekt. S Qwen porazili lekcie z iných repozitárov variant bez lekcií o 0,077 (+0,026 až +0,128), ale neboli lepšie než náhodné lekcie s rovnakými povrchovými znakmi: +0,010 (-0,041 až +0,062).
- **Blízke rozhodnutia.** Pri 29 % zo 160 rozhodnutí má niektorá lekcia v tom istom repozitári aspoň polovicu slov možnosti spoločnú s rozhodnutím. Časť zisku z toho istého repozitára preto môže byť takmer rovnaká nápoveda, nie pamäť.
- **Druh lekcie.** Naše lekcie sú konkrétne voľby. Abstraktné postupy a poznatky sa medzi oblasťami prenášajú (Wang et al., [arXiv 2409.07429](https://arxiv.org/abs/2409.07429); Kim et al., [arXiv 2604.14004](https://arxiv.org/abs/2604.14004)).
- **Druh rankera.** Výber podľa podobnosti porazí náhodné príklady z celej úlohy (Liu et al., [arXiv 2101.06804](https://arxiv.org/abs/2101.06804)). Náš náhodný variant bol už z toho istého repozitára a naučený ranker sme netestovali.
- **Rozsah.** Jeden benchmark, jedna oblasť pre hlavný výsledok, 160 rozhodnutí pre kontrolu s Opusom, 11 repozitárov. Lekcie nesú skutočný výsledok, strop, ktorý nasadený agent nedosiahne. Pravidlo na dva riadky bez modelu dosiahne 0,669, viac než variant bez lekcií pri každom modeli, ktorý sme pustili.

## Čo to znamená pre inspeximus

Výsledok niesla tá časť pamäte agenta, ktorou je výsledok a to, kto ho potvrdil. inspeximus to podporuje a treba to zapnúť. V Python API vráti `recall(influence_only=True)` iba potvrdené spomienky. S `credit_requires_warrant=True` sa zásluha počíta, iba keď nesie potvrdenie. `remember(project=...)` a `recall(project=...)` oddelia pamäť podľa projektu, pričom záznamy bez projektu ostávajú viditeľné. Na tomto benchmarku hodnota nebola v lepšom zoradení podľa podobnosti.

Každé číslo tu vypíše [research/probes/taste_outcome_not_ranking.py](https://github.com/DanceNitra/agora/blob/main/research/probes/taste_outcome_not_ranking.py) z výsledkov po jednotlivých rozhodnutiach, ktoré ležia vedľa nej.
