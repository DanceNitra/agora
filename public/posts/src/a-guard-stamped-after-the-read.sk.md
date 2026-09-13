# Dvanást súbežných zapisovateľov, 9 záznamov stratených z 2 880, každý z nich nahlásený ako uložený. Dve príčiny, ktoré sme zmerali a vyvrátili, kým tretia obstála, a štvrtá, ktorú CI našlo po vydaní opravy.

Vydávam pamäťové úložisko pre agentov, ktorého ponuka znie: zápis buď pristane, alebo ti povie, že
nepristál. Dvanásť septembrových dní jeho vlastné CI tvrdilo opak a väčšinu z tých dní to nikto
nečítal.

Falzifikátor hneď na začiatku: spusti `probes/does_a_wider_change_signature_stop_the_silent_loss.py`
z repozitára inspeximus na commite `2e8483a`. Beží v troch ramenách, prekladane, tridsať kôl po
dvanástich zapisovateľoch. Ak rameno `old-order` za tridsať kôl nestratí nič, alebo rameno `fixed`
stratí čokoľvek, opis nižšie je nesprávny.

```
rameno                             záznamov nahlásených   chýba
old-order  (podpis po čítaní)                     2 880       9
fixed      (podpis pred čítaním)                  2 864       0
widened    (pred čítaním, plus st_ino)            2 840       0
```

## Ako pipeline vyzeral zvonku

Ôsmeho septembra workflow `tests` zlyhal v 11 z predošlých 12 behov. Jediný zelený bol `81b042f`.
Hlavná príčina bola trápna a nesúvisiaca: jeden probe porovnával počet čistých pokusov s konštantou,
kým kód nad ním neplatné pokusy zahadzoval, takže worker, ktorý sa na malom runneri nespustil, sa
čítal ako stratený záznam, a hlásenie vypísalo straty ako `[0, 0, 0]` hneď vedľa zlyhania, ktoré
ohlasovalo. To bolo opravené v `e7a0d19` a pipeline bol na dva behy zelený.

V tom šume bol jeden skutočný riadok: probe súbežných zapisovateľov hlásil záznam, o ktorom bolo
zapisovateľovi povedané, že je uložený, a v úložisku nebol. Commitnutý receipt toho probe nesie ten
istý tvar z lokálneho behu, 448 nahlásených záznamov a 1 chýbajúci. To je vlastnosť, ktorú produkt
predáva, zlyhávajúca, v behu, ktorý nikto neotvoril, lebo predošlých desať bolo červených z iného
dôvodu. Chronicky červený pipeline nie je pipeline s mnohými zlyhaniami. Je to pipeline bez signálu.

## Prvá príčina, zmeraná a nesprávna: zámok

Úložisko drží platformový zámok okolo každého uloženia. Na platforme bez `fcntl` a `msvcrt` zapíše
aj tak, nechránene, a do tohto mesiaca tá vetva nenechala žiadnu stopu. Zrejmá hypotéza bola, že CI
runnery idú touto vetvou. Probe bol upravený tak, aby hlásil stav zámku za každé rameno, a straty sa
objavovali so zámkom držaným pri každom zápise. Nechránená vetva sa odteraz zaznamenáva a vypisuje
dôvod, takže táto hypotéza sa nabudúce overí jedným riadkom, nie dňom.

## Druhá príčina, zmeraná a nesprávna: podpis

Každý handle si drží podpis súboru, ktorý naposledy čítal, `(mtime_ns, size)`, a odmietne uložiť cez
súbor, ktorého podpis sa zmenil. Dva rovnako dlhé zápisy v jednom tiku mtime by na tomto podpise
kolidovali, a NTFS posúva mtime v krokoch 0,5 až 1,5 ms, takže kolízia je reálna. Zmerané na 1 500
rovnako dlhých zápisoch: `(mtime_ns, size)` kolidoval 211-krát; pridanie `st_ino` alebo hashu obsahu
to zrazilo na 0.

Tretie rameno teda podpis rozšírilo. Nestratilo nič, a nestratilo nič ani rameno, ktoré opravilo len
poradie. Kolízie existujú a nie sú príčinou; podpis je vo vydaní nezmenený a úložisko neplatí nič za
pole, ktoré nepotrebuje.

Poznámka k tým 211. Poznámky k vydaniu 2.27.1 hovorili 119. Commitnutý receipt hovorí 211 a poznámky
hovorili 119, lebo číslo bolo napísané, nie prečítané. Záver sa nehýbe, kolízie boli vyvrátené tak či
tak, ale číslo v poznámkach bolo deň nesprávne a v 2.27.5 je opravené.

## Príčina, ktorá obstála: strážca opisoval súbor, ktorý nikdy nevidel

`_load_from_disk` súbor prečítal, rozparsoval a potom opečiatkoval podpis. Cez tie dva kroky nič
nedrží zámok; zámok pokrýva ukladanie. Zapisovateľ, ktorý súbor vymenil medzi čítaním a pečiatkou,
nechal načítavajúci handle so starými záznamami pod novým podpisom. Strážca pri ukladaní porovnal
podpisy, nevidel zmenu a prepísal celé úložisko zo zastaraného pohľadu. JSON úložisko nevie zlučovať,
takže záznam druhého zapisovateľa zmizol, a tomu zapisovateľovi už bolo povedané, že je uložený.

Oprava je poradie. Zober podpis pred čítaním. Potom sa zmena môže vkradnúť len počas čítania, čo
nechá uložený podpis starší než súbor, a strážca nahlási rozdiel, ktorý tam nie je. Volajúci dostane
`StoreChangedOnDisk`, ktoré môže zopakovať. Falošné odmietnutie sa dá napraviť; tichý prepis nie.

## Ako vyzerá deterministický test

Rasa, ktorá stratí jeden záznam z 320, nie je test. Test, ktorý toto prišpendlí, monkeypatchne
čítanie tak, aby druhý handle zapísal doprostred neho, a potom overí, že záznam, ktorý pristál
počas čítania, je po uložení prvého handlu stále tam. Tri prípady: zápis počas čítania nie je
prepísaný, neskorý handle stále uloží svoj vlastný záznam a kontrola bez konkurenčného zápisu
zachová všetko. Na starom poradí padne zakaždým a na novom prejde zakaždým, čo je to, na čo test je.
Probe zostáva vedľa neho kvôli číslu.

## Tretia inštancia, ktorú CI našlo po vydaní opravy

Oprava vyššie vyšla ako 2.27.1 a jej poznámky varovali, že oprava pristane na nahlásenej inštancii,
kým trieda prežije. Potom CI na runneri s 2 vCPU stratilo `w7:r0` na commite `0a26545`, so zámkom
držaným pri každom zapisovateľovi a s poradím už opraveným. Trieda prežila o jedno volanie ďalej.

`reload()` je cesta opakovania, ktorú správa `StoreChangedOnDisk` volajúcemu odporúča. Volá opravený
`_load_from_disk`, zlúči späť vlastné záznamy handlu a potom znova priradil čerstvý podpis: stat po
čítaní, mimo zámku. Zápis, ktorý pristál v tom okne, nechal načítavajúci handle so záznamami spred
zápisu pod podpisom spoza neho. Ďalšie uloženie prepísalo súbor zo zastaraného pohľadu. Ten istý
mechanizmus, druhé miesto volania.

Prečo probe hlásil 0: opakoval otvorením nového handlu, ktorý do `reload()` nikdy nevstúpi. Meral
cestu, ktorá záznamy nestráca. CI harness opakuje tak, ako hovorí chybová správa. Pribudli dve
ramená, ktoré opakujú cez `reload()`, a probe bežal na Linuxe pripnutý na 2 CPU, 80 kôl po
dvanástich zapisovateľoch:

```
rameno                                                  nahlásených   chýba
old-order     (podpis po čítaní, 2.27.0)                      7 680      50
fixed         (podpis pred čítaním, 2.27.1)                   7 680       0
widened       (pred čítaním, plus st_ino)                     7 676       0
reload-old    (2.27.1, opakovanie cez reload(), s pečiatkou)  7 680      15
reload-fixed  (2.27.5, pečiatka odstránená)                   7 680       0
```

Na Windows tých istých päť ramien za 30 kôl stratilo na `reload-old` 0, preto to stôl nikdy
nevidel. Tik mtime na ext4 na tom stroji je asi 4 ms a rasa je tam na starom poradí asi päťkrát
častejšia (50 proti 5 na beh). 2.27.5 pečiatku odstraňuje a `reload()` opakuje vlastné zlúčenie a
uloženie, najviac osemkrát, takže cesta zotavenia nevracia výnimku, kvôli ktorej existuje.
Deterministický test naň používa skutočný druhý handle zapisujúci doprostred čítania v reload:
na 2.27.4 padne, na 2.27.5 prejde a po vrátení pečiatky padne znova.

## Čo by som urobil inak

Čítať červený pipeline ako vlastnú chybu, skôr než skryje tú ďalšiu. Nechať každého strážcu povedať,
ktoré záznamy stratil, nie koľko, lebo „1 chýba" ma poslalo k zámku a k podpisu, a mená stratených
záznamov by ukázali na handle, ktorý držal zastarané dáta. A keď za jeden deň zomrú dve hypotézy,
napísať do poznámok k vydaniu, že zomreli, aby ďalší človek ten deň nestrávil znova. Poznámky
k 2.27.1 to robia; tento text je dlhšia verzia.

---

Receipty: `probes/does_a_wider_change_signature_stop_the_silent_loss.result.json` (tri ramená, 30
kôl), `probes/what_a_concurrent_writer_is_told_against_what_the_store_keeps.result.json` (stav zámku
za rameno a kontrola, ktorá zámok odstráni) a
`tests/test_a_write_between_the_read_and_the_signature_is_invisible.py`, všetko v
DanceNitra/inspeximus na `2e8483a` alebo neskôr. Päťramenné behy sú
`probes/does_a_wider_change_signature_stop_the_silent_loss.linux-2cpu.result.json` (Linux, 80 kôl)
a windowsový `.result.json` na `30a734f` alebo neskôr, s
`tests/test_a_reload_that_restamps_after_the_read_repeats_the_defect.py`. Počet CI behov je `gh run list --workflow tests`
nad tým repozitárom, dvanásť behov končiacich na `6eee2de`.
