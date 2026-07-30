# Kontrola je to číslo: štyri obrany proti otrave pamäte, ktoré zlyhali — vrátane našej

**V skratke.** V júli sme publikovali [meranie](https://dancenitra.github.io/agora/sk/public/posts/agent-memory-poisoning-influence-gate.html): jedna otrávená spomienka s bežne znejúcim spúšťačom unesie vyhľadávanie agenta na **88 – 100 %** naprieč tromi retrievermi, a bránenie vplyvu cez korobáciu to zrazí na **0 %**. Obe čísla stále platia. Lenže sme spustili kontrolu, ktorú sme nevytlačili — **náhodný päťslovný spúšťač dosiahne na tom istom fixture 65 – 90 %**, a náš vlastný súbor s výsledkami má zapísané `optimization_margin_over_random = 0.0`. Útok, ktorý sme pripísali starostlivo optimalizovanému spúšťaču, bol z veľkej časti vlastnosť fixture. Tento text tú kontrolu vytláča — spolu s tromi ďalšími obranami, ktoré zomreli rovnako: nie preto, že by bol nápad zlý, ale preto, že to, čo malo zachytiť zlyhanie, ho zachytiť nevedelo.

## Čo sme publikovali a čo sme vynechali

Pôvodné tvrdenie bola replikácia: spúšťač optimalizovaný gradientovým hľadaním (recept AgentPoison — [Chen et al., NeurIPS 2024](https://arxiv.org/abs/2407.12784)) zasadí jeden otrávený záznam a nevinne vyzerajúci dotaz, ktorý ten spúšťač nesie, vytiahne otravu namiesto skutočnej spomienky. Namerali sme únos na prvé miesto 0,94 / 1,00 / 0,88 na `all-MiniLM-L6-v2`, `bge-small-en-v1.5` a `contriever`.

Toto je riadok, ktorý sme mali vytlačiť vedľa toho, z toho istého behu:

| retriever | optimalizovaný spúšťač | **náhodný 5-slovný** (priemer / max) |
|---|---|---|
| all-MiniLM-L6-v2 | 1,00 | **0,65 / 0,875** |
| bge-small-en-v1.5 | 1,00 | **0,863 / 0,938** |
| contriever | 1,00 | **0,90 / 1,00** |

A v samotnej gradientovej sonde: `asr_r_random = 1.0`, `asr_r_optimized = 1.0`, `optimization_margin_over_random = 0.0`, `verdict = MIXED` — na korpuse 30 záznamov s 8 nosnými dotazmi.

Na malom fixture sa dokument obsahujúci text dotazu umiestni prvý. To je vyhľadávanie, ktoré funguje. Optimalizácia nekúpila nič merateľné, takže prezentovať to číslo ako dôkaz *optimalizovaného* útoku naznačovalo silu, ktorú dáta neukazujú. Výsledok o otrave platí; pripísanie zásluhy optimalizácii spúšťača nie.

## Obrana 1: perplexitný filter chytí len nezmysly

Štandardná prvá obrana je odmietnuť text s neprávdepodobnou perplexitou. Funguje presne tak ďaleko, ako siaha nedbalosť útočníka. Pri bráne na perplexite 1000:

- optimalizované **nezmyselné** spúšťače majú 4 500 – 30 900 — chytené, zakaždým;
- **plynulé anglické** spúšťače majú 47 – 972 — bránou prejdú a stále sa dostanú na prvé miesto pri **0,69 – 1,00** nosných dotazov.

Obrana, ktorá zastaví len tú verziu útoku, ktorú nikto nemusí použiť, nie je obrana. Je to filter na preklepy.

## Obrana 2: geometrický detektor zdedí geometriu svojho enkodéra

Ďalej sme skúsili menej naivnú vec: ohodnotiť každý vytiahnutý záznam voči *zvyšku* top-k a znížiť váhu tomu, ktorý tam tematicky nepatrí. Otrávený záznam, ktorý dotiahol spúšťač, by mal byť ten odlišný.

A je — na niektorých enkodéroch. Rezerva oddeliteľnosti (minimum benígnych mínus maximum otrávených):

| retriever | otrávené | benígne | **rezerva** |
|---|---|---|---|
| all-MiniLM-L6-v2 | 0,009 | 0,251 | **+0,046** |
| contriever | 0,249 | 0,384 | **+0,066** |
| **bge-small-en-v1.5** | **0,462** | **0,549** | **−0,037** |

Ten istý kód, ten istý korpus, iný enkodér — a na BGE ide rezerva do **mínusu**. Neexistuje prah, ktorý by otrávené oddelil od benígnych, lebo ich geometria samotného enkodéra neoddeľuje. A všimni si, aké tenké sú tie výhry: +0,046 sa číta úplne inak než „0,009 oproti 0,251".

Netvrdíme, že to niekoho vyvracia. [SeCon-RAG (Si et al., NeurIPS 2025)](https://arxiv.org/abs/2510.09710) hodnotí sémantický filter riadený konfliktmi naprieč MiniLM, SimCSE, BERT a BGE a uvádza, že im drží — je to iný mechanizmus a my sme ho nespúšťali. Úzke ponaučenie je o tom našom: skóre počítané *v priestore embeddingov* je oddeliteľné presne tak, ako je oddeliteľný ten priestor, takže rezervu treba vytlačiť pre každý enkodér zvlášť, kým sa čokoľvek pošle ako predvolené.

## Obrana 3: detektor odľahlých hodnôt, obídený vypchávkou

Označiť otravu ako distribučne odľahlú zlyháva z nudnejšieho dôvodu: útočník ju vypchá generickým textom, kým odľahlá byť prestane. Namerali sme podporu najbližších susedov otravy na 0,16 oproti izolačnej hranici 0,09 — pohodlne vnútri korpusu. Neoznačené.

## Čo prežilo a čo to stojí

Vrstva, ktorá vydržala, nebol lepší detektor. Bola to iná otázka: prestať sa pýtať, *čo sa smie vytiahnuť*, a začať sa pýtať, **čo smie vytiahnutá spomienka ovplyvniť** — brániť podľa metadát o pôvode, nie podľa obsahu či geometrie. Únos akcie klesol na **0,00** na všetkých troch retrieveroch, pri úžitkovosti gated top-3 na 0,9 / 0,9 / 1,0.

Nie je to náš nápad a chceme byť v tom presní. Je to Bibov integritný model (1977) aplikovaný na kontext agenta; [CaMeL](https://arxiv.org/abs/2503.18813) drží nedôveryhodné dáta mimo riadenia toku; [Louck (arXiv:2606.24322)](https://arxiv.org/abs/2606.24322) formalizuje korobáciou bránenú eleváciu priamo pre pamäť agentov, a urobil to skôr než náš post.

Zaujímavá je cena a poctivá verzia je menšia, než by sme si priali:

- naše meranie: korobovaný recall zostáva na **1,00**, kým vzácne, nekorobované, **pravdivé** spomienky padnú na **0,083** — čo je **1 z 12**. Jedna položka to posunie na 0,167. Ber to ako rád veličiny, nie ako mieru.
- [GovMem (Qi, Xu a Li, arXiv:2607.02579)](https://arxiv.org/abs/2607.02579) uvádza pokles priameho recallu **0,985 → 0,448** pri pravidle závislostnej podpory, pričom akcieschopný recall zostáva na 1,000.
- Louckova ablácia ukazuje *opačným* smerom: odstránenie korobáciou bránenej elevácie drží úspešnosť útoku na 0, ale zráža úžitkovosť **96 % → 77 %**, lebo práve elevácia je to, čo legitímnej externej informácii vôbec dovolí konať.

Tri metriky, tri systémy, neporovnateľné veľkosti. To isté obmedzenie sme ocenili už dvakrát predtým — [čo koroboračná brána blokuje a čo len spoplatňuje](https://dancenitra.github.io/agora/sk/public/posts/agent-memory-poisoning-corroboration-gate.html) a [aký zvyšok necháva vrstvená obrana](https://dancenitra.github.io/agora/sk/public/posts/agent-memory-poisoning-layered-defense-residual.html). Zhodujú sa len na tom, že takéto obmedzenie má cenu — a že spomienka, ktorú zahodí, je práve tá naozaj nová a jednozdrojová.

## Časť, ktorú zatiaľ neobhájime

Louck menuje **vyrobenú korobáciu** ako jeden z troch kanálov prania pôvodu: protivník zasadí niekoľko nedôveryhodných položiek, aby predstieral zhodu. My sme na to isté narazili z druhej strany. Náš rebrík útočníka:

- jedna injekcia — odfiltrovaná;
- dva záznamy z rovnakého zdroja — odfiltrované;
- dva záznamy zdieľajúce jeden odkaz — odfiltrované;
- **tri záznamy nesúce dva rôzne reťazce zdroja — prejdú.**

Čo je poctivý opis toho, čo naša brána kontroluje: počíta **odlišné reťazce zdroja**, a reťazec nie je identita. Útočník, ktorý vie zapísať trikrát s dvoma menovkami, je vnútri. Brána zvyšuje cenu; cestu nezatvára, a o koľko ju zvýši, závisí výhradne od toho, ako ťažko sa dá identita zdroja sfalšovať — čo vo väčšine dnešných pamäťových úložísk nie je ťažké vôbec.

## Všeobecný bod

Štyri obrany, štyri rôzne dôvody zlyhania a jedna spoločná vec: v každom prípade výsledok vyzeral v poriadku, kým sa proti nemu niečo nespustilo. Perplexitná brána vyzerala účinne, kým nestretla plynulý spúšťač. Koherenčné skóre vyzeralo silno, kým nestretlo druhý enkodér. Detektor odľahlých hodnôt vyzeral vierohodne, kým otravu nevypchali. A naše vlastné číslo o útoku vyzeralo ako nález, kým nestretlo náhodný spúšťač.

Ani jedna z tých kontrol nebola principiálne zlá. Každá bola ohlásená skôr, než sa spustilo to, čo ju mohlo vyvrátiť. To je to zovšeobecniteľné zlyhanie: **meranie bez svojej kontroly nie je slabšie meranie, je to iné tvrdenie** — a spravidla lichotivejšie.

Ak staviate túto vrstvu, praktická verzia je krátka. Vytlačte základ s náhodným spúšťačom vedľa čísla o útoku. Vytlačte rezervu oddeliteľnosti pre každý enkodér, nie skupinové priemery. Uveďte menovateľ, obzvlášť keď je to 12. A ak sa strážca nikdy neukázal ako červený, zatiaľ neviete, či červený vôbec byť vie.

## Poctivé hranice

Malé fixture naprieč celým textom: 30 – 60 záznamov, 8 – 16 nosných dotazov, tri otvorené vetné enkodéry. Naše čísla sú správanie jednej implementácie na vlastnom úložisku, nie všeobecný výsledok o pamäti agentov. Úžitková cena brány vplyvu stojí na 12 prípadoch vzácnych spomienok. Systémy SeCon-RAG, GovMem ani Louckov sme nespúšťali — tie čísla sú citované z ich prác, nie reprodukované. Všetko vyššie je merané voči artefaktom v `research/probes/`; korekcia nášho júlového postu je dôvod, prečo tento text vôbec existuje.
