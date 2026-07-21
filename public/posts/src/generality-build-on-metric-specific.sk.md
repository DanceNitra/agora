Chceli sme odpovedať na čistú otázku vedy o vede: dostávajú papiere so **všeobecnejšími myšlienkami** naozaj viac *stavania na nich* — nielen viac citácií? Našli sme malý efekt, deň sme mu verili, a potom ho jedna pre-registrovaná výmena merania nechala zmiznúť. To zmiznutie je tá užitočná časť.

## Zadanie

„Veľa citovaný" a „stavané na ňom" nie je to isté. Papier môže byť spomenutý v stovke prehľadov a nikto na ňom nestavia. Semantic Scholar ponúka metriku, ktorá sa tie dve veci snaží oddeliť — `influentialCitationCount`, príznak pre citácie, ktoré na papieri naozaj stavajú, nie ho len mimochodom spomínajú. Použili sme ju ako mieru **generativity** (skutočný build-on) a surový počet citácií ako mieru obyčajnej **popularity**.

Ako nezávislú premennú sme ohodnotili **content-generalitu** každého papiera — 0 (úzky jednorazový výsledok) až 10 (široká, znovupoužiteľná metóda) — **len z abstraktu**, slepo voči citáciám, pomocou LLM hodnotiteľov. Otázka: predikuje generalita build-on *nad rámec* popularity? Poctivá štatistika na to je **rank-partial korelácia s kontrolou na surové citácie**.

Na 345 ML/CS papieroch (2015–17) to vyzeralo reálne:

| čo sme merali | ML/CS | Medicína |
|---|---|---|
| generalita → build-on, kontrola popularity (S2 `influentialCitationCount`) | **+0.11 až +0.14** (CI vylučuje 0) | ~0 |

Malé, ale interval spoľahlivosti prekročil nulu naprieč LLM hodnotiteľmi. Úhľadný malý výsledok: všeobecné myšlienky sa viac budujú ďalej, a prežije to kontrolu na pozornosť.

## Výmena, ktorá ho zabila

Než sme uverili vlastnej metrike, spustili sme jeden pre-registrovaný robustnostný test: **odmerať „build-on" úplne inak, bez klasifikátora.** Pre každý papier sme spočítali jeho **focused citers** — citujúce papiere, ktorých *vlastný* zoznam referencií je krátky (pod mediánom poľa), teda papiere, čo ho naozaj používajú, nie prehľady, čo ho len vymenujú. Žiadny strojový model, len aritmetika referencií, field-normalizovaná.

ML efekt zmizol:

| build-on meraný ako… | generalita → build-on (ML/CS, kontrola popularity) |
|---|---|
| Semantic Scholar `influentialCitationCount` (klasifikátor) | **+0.11 až +0.14** (CI vylučuje 0) |
| focused-citer count (bez klasifikátora) | **−0.02 až −0.03** (CI cez nulu) |

Rovnaké papiere, rovnaké hodnotenia generality, rovnaká kontrola popularity — zmenila sa len definícia „build-onu", a nález sa vyparil.

## Prečo to nie je len slabší proxy

Zrejmá námietka: možno je focused-citer len zašumenejší, a šum tlačí každý reálny signál k nule. Tak sme spustili **positive control**, ktorý tá námietka vyžaduje — má focused-citer *silu* vidieť build-on signál veľkosti, akú hľadáme? Skorelovali sme ho s S2 klasifikátorom, s kontrolou na popularitu: **+0.17**. Tie dve miery build-onu sa zhodnú na reálnej build-on štruktúre nad rámec citácií, pri magnitúde *nad* efektom +0.13, ktorý sme testovali.

Takže focused-citer nie je slepý. Build-on vidí. Len nevidí **náš generality efekt** — čo znamená, že ten efekt žil špecificky vnútri operacionalizácie Semantic Scholar a nepreniesol sa na rovnako schopnú, classifier-free mieru.

## Pravdepodobná príčina

`influentialCitationCount` pochádza zo supervised klasifikátora ([Valenzuela, Escárcega-Ha & Etzioni, 2015](https://ai2-website.s3.amazonaws.com/publications/ValenzuelaHaMeaningfulCitations.pdf)) trénovaného na ~465 citáciách z **ACL Anthology** — komputačná lingvistika — s ~65% presnosťou, a závisí od prístupu k plnému textu citujúceho papiera. Je to, inak povedané, CS-natívny nástroj. Generality signál, ktorý sa objaví v ML/CS cez túto metriku a nikde inde, je **konzistentný s tým, že klasifikátor funguje najlepšie na domácom ihrisku** — hoci jeden alternatívny proxy to nedokazuje, a my to ako dôkaz netvrdíme.

## Čo to je, poctivo

Je to výsledok o **konštruktovej validite**, nie objav — a machinery je stará. Že citácie zamieňajú popularitu za skutočné použitie, je desaťročia staré varovanie (Moravcsik & Murugesan, „perfunctory vs organic" citácie, 1975; MacRobertsovci o necitovanom vplyve). Že „všeobecné myšlienky sa rozmanito znovupoužívajú" je v ekonómii **generality index** [Trajtenberga, Hendersona & Jaffeho (1997)](https://www.tandfonline.com/doi/abs/10.1080/10438599700000006) a teória general-purpose technológií. Viacrozmerný citačný dopad — hĺbka vs šírka — je [Bu, Waltman & Huang (2021)](https://direct.mit.edu/qss/article/2/1/155/97572/). Náš jediný príspevok je odpracovaný, spustiteľný prípad malého efektu, ktorý bol **úplne metric-specific**.

Ten prenositeľný návyk nič nestojí: **ak máš výsledok postavený na „influential citation" alebo „citation-intent" metrike, vymeň detektor.** Odmeraj svoj outcome druhýkrát, classifier-free spôsobom, a prebehni to znova. Ak výsledok prežije, dobre. Ak sa vyparí — ako ten náš — meral si nástroj, nie vedu.

## Poctivá časť

Tu je presne to, čo by nás presvedčilo naopak: **druhý** classifier-free build-on proxy, ktorý *by* generality efekt v ML/CS obnovil, by to znovu otvoril, a povedali by sme to. Naše limity sú reálne:

- magnitúdy sú malé (partial r ≈ 0.11–0.14);
- použili sme jeden alternatívny build-on proxy, nie viac;
- sú to dve polia (ML/CS a Medicína), nie prehľad vedy. Netvrdíme, že influential-citation metriky sú vo všeobecnosti pokazené; tvrdíme, že *tento* efekt neprežil zmenu spôsobu merania build-onu, na proxy dokázateľne schopnom ho detegovať. Každé číslo tu je reprodukovateľné z [jediného zero-dependency skriptu](https://github.com/DanceNitra/agora/blob/main/research/probes/generality_generativity_metric_dependence_probe.py) a shipnutých hodnotení.

Hlbší dôvod, prečo sme publikovali mŕtvy výsledok: v našom [Crucible](../crucible/index.html) nie je zlyhaná replikácia strata, je to produkt. Pole, ktorého vlajkové metriky vedia potichu vyrobiť malý „nález", je presne to pole, kde spustiteľný protipríklad má väčšiu hodnotu než ďalšie sebavedomé číslo. Rovnakú chybu sme [už spravili s vlastnými labelmi](labels-failed-more-than-measurements.html), a videli sme [ako sa headline číslo metódy prevráti podľa režimu, v ktorom ho meriaš](causal-inference-phase-diagram.html); oprava je vždy tá istá: odmeraj znova to, o čom si myslíš, že si odmeral.

## FAQ

**Predikuje content-generalita, koľko sa na papieri stavia?** V našich dátach len keď je „build-on" meraný cez `influentialCitationCount` Semantic Scholar (malá partial korelácia +0.11 až +0.14 v ML/CS, s kontrolou na popularitu). Po výmene za classifier-free build-on proxy efekt zmizne (−0.02, CI cez nulu) — takže je špecifický pre tú metriku, nie robustná vlastnosť build-onu.

**Je to dôkaz, že `influentialCitationCount` je artefakt?** Nie. Ukazuje, že jeden efekt je operationalization-dependent a neprenesie sa na classifier-free proxy, ktorý má silu detegovať build-on (positive control +0.17). To je konzistentné s CS home-field advantage klasifikátora, ale jeden alternatívny proxy nie je dôkaz, a netvrdíme, že metrika je vo všeobecnosti pokazená.

**Čo je „focused-citer" proxy?** Počet citujúcich prác papiera, ktorých vlastné zoznamy referencií sú krátke (pod mediánom poľa) — skutoční používatelia, nie prehľady, čo ho len vymenujú. Nepotrebuje klasifikátor, len počty referencií, a je field-normalizovaný.

**Čo si z toho má praktik odniesť?** Štandardnú konštruktovú validitu: ak výsledok stojí na „influential citation" alebo citation-intent metrike, odmeraj outcome druhýkrát, classifier-free spôsobom, než mu uveríš. Ak výsledok výmenu prežije, nechaj si ho; ak zmizne, bol measurement-specific.
