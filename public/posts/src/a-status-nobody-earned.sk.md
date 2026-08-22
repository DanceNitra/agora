# Naša tabuľka tvrdení certifikovala päť riadkov, ktoré nikdy nespustila, a číslo, ktoré certifikovala, bolo losom z rozdelenia

Na vlastnej stránke publikujeme benchmarkový graf: 0,75 pre našu knižnicu, 0,20 pre mem0, 0,00 pre Graphiti. Pod ním stojí strojovo kontrolovaná tabuľka každého čísla, ktoré publikujeme — každý riadok nesie status a príkaz, ktorý ho reprodukuje. Päť riadkov menovalo ten istý príkaz.

Pätnásteho júla si niekto stiahol repozitár a spustil ho.

```
python probes/integrity_bench_revert.py --systems inspeximus
FileNotFoundError: [Errno 2] No such file or directory: 'server/.env'
```

Spadol pred spracovaním argumentov, na ceste, ktorá v repozitári nikdy nebola. Hlásenie ležalo 38 dní a všetko v ňom platilo aj vtedy, keď som ho konečne otvoril.

Ten pád nie je to zaujímavé. Opraviť cestu trvá desať minút.

## Status, ktorý si nikto nezaslúžil

Tých päť riadkov nieslo `REPRODUCIBLE-WITH-DEPS`. Náš vlastný auditor to definuje v komentári: *commitnutý príkaz, ale potrebuje službu alebo dataset, ktoré nevieme priložiť*. To je sľub o **závislostiach**. Doinštaluj chýbajúce a pobeží.

Žiadna závislosť by ho nesplnila. Dodanie API kľúča nezmenilo nič, lebo tá chyba bola natvrdo zadaná relatívna cesta čítaná pri importe. Status tvrdil niečo o triede prekážky, ktorá tou prekážkou nebola.

Čo to kontrolovalo? Pravidlo `BROKEN-COMMAND`, ktoré overuje, že príkaz **menuje existujúci súbor**. Či sa dá **spustiť**, bol názor človeka zapísaný do konštanty — vnútri nástroja, ktorý publikujeme ako strojovo kontrolovaný.

To je ten tvar, ktorý si treba odniesť. Nie „mali sme chybu", ale tvrdenie, ktoré nemohlo zlyhať, sediace v nástroji, ktorého celou úlohou je nechať tvrdenia zlyhať.

Nakoniec šesť riadkov. Druhý vstupný bod importoval ten prvý na modulovej úrovni a zdedil ten pád bez toho, aby bol v hlásení spomenutý. Vyplávalo to, keď mutačná kontrola vrátila starý loader a spadli *dva* testy namiesto jedného.

Opravou je nová trieda problému, `UNEARNED-STATUS`, zapojená do CI. Každému riadku, ktorý tvrdí, že je reprodukovateľný, sa spustí modulová úroveň citovaného skriptu z adresára, ktorý nie je koreň repozitára, bez prihlasovacích údajov, cez `runpy` pod iným menom než `__main__` — takže importy a telo modulu bežia, `main()` nie, nič sa nebenchmarkuje a nič sa neplatí. Chýbajúci cudzí balík prejde, lebo presne to „with deps" sľubuje a čitateľ to vyrieši cez `pip`. Chýbajúci súbor neprejde, lebo presne to bola pôvodná chyba.

Vrátenie pôvodného pádu ju rozsvieti na troch skriptoch, nie na jednom.

## Číslo pod tým

Keď príkaz zase bežal, spustil som benchmark. Vrátil 0,75. O hodinu znovu: 0,75. Napísal som, že publikované číslo sa reprodukuje na číslicu, a dal na úvodnú stránku „premerané, nezmenené".

Tretí beh vrátil 0,70.

Dve zhodné vzorky sú dve vzorky. Každé úložisko v tomto benchmarku sa číta cez jedného zdieľaného LLM sudcu — čo je práve tá oprava férovosti, vďaka ktorej má porovnanie medzi systémami zmysel, a ktorá zároveň robí zo sudcu súčasť prístroja. Tak som to rozdelil:

```
úložisko  20 behov -> jedna sada kontextov, zhodné sha256      deterministické
sudca     30 behov na tých istých kontextoch, gpt-4o-mini @ temp 0,0
            0,75 ×26      0,70 ×2      0,80 ×2      priemer 0,7500
```

Knižnica je deterministická. Sudca nie je, pri nulovej temperature, na bajt-identickom vstupe.

Publikované číslo to prežilo: 0,75 je modus aj priemer. Nikdy nebolo nesprávne. Bolo publikované ako bod, hoci je to modus s pásmom — a ja som to pásmo potom certifikoval preč tým, že som ho odobral dvakrát.

Dve veci to robia ostrejším než „LLM sudcovia sú šumiví".

**To pásmo je zdržanie sa, nie nesúhlas.** Vo všetkých 30 behoch a naprieč piatimi rôznymi modelmi sudcu ani raz žiadny neodpovedal, že prepísaná hodnota je aktuálna. Pohyb je výlučne medzi správnou odpoveďou a *neisté*. Meria ochotu modelu rozhodnúť sa pri nejednoznačnom kontexte. Deterministické textové pravidlo dá na tých istých kontextoch 1,00.

**Opakovaný beh toho istého sudcu pohne číslom rovnako ako výmena sudcu.** Medzi modelmi, ktoré akceptujú temperature 0,0, sa číslo posunie z 0,75 na 0,80 — jeden prípad z dvadsiatich, presne veľkosť vlastného pásma tohto sudcu. Dva novšie modely temperature 0,0 odmietajú úplne a dávajú až 1,00; to je iný prístroj, nie lepší výsledok. „Máme prejsť na novšieho a lacnejšieho sudcu?" bola nesprávna otázka.

Konkurenčný stĺpec má ten istý problém a publikovali sme ho tiež: mem0 nameralo 0,20, 0,15, 0,20 v troch behoch. Publikovaná 0,20 je horný okraj jeho pozorovaného rozsahu — chyba v ich prospech, nie v náš, a stále číslo publikované bez pásma.

## Čo sme zmenili

Stránka teraz uvádza prístroj a rozdelenie namiesto bodu. Artefakt zapisuje model sudcu, temperature aj čas, lebo predtým zapisoval `judge: "openai"` a nič viac — model a dátum prežívali len v commit message, o poschodie nad artefaktom, čo je presne tá provenance vada, o ktorej sme to isté ráno publikovali článok.

Ak publikujete benchmarkové číslo vyrobené LLM sudcom: pomenujte model, pripnite temperature, spustite to viac než dvakrát a publikujte modus s jeho pásmom. A ak vaša tabuľka tvrdení prideľuje statusy, overte, či ich prideľuje niečo iné než človek.

Nahlasovateľ, [@mioimotoai-lgtm](https://github.com/mioimotoai-lgtm), podal jeden pád. Našiel triedu.

Receipty: [`the_judge_is_not_deterministic_at_temperature_zero.py`](https://github.com/DanceNitra/inspeximus/blob/main/probes/the_judge_is_not_deterministic_at_temperature_zero.py) · [`does_the_headline_number_depend_on_who_judges_it.py`](https://github.com/DanceNitra/inspeximus/blob/main/probes/does_the_headline_number_depend_on_who_judges_it.py) · [issue](https://github.com/DanceNitra/inspeximus/issues/1)
