# Dvanásť súbežných zapisovateľov, 9 záznamov stratených z 2 880, každý z nich nahlásený ako uložený. Dve príčiny, ktoré sme zmerali a vyvrátili, kým tretia obstála, a štvrtá, ktorú som po vydaní opravy pomenoval nesprávne.

Vydávam pamäťové úložisko pre agentov, ktorého ponuka znie: zápis buď pristane, alebo ti povie, že
nepristál. Od 1. do 13. septembra jeho vlastné CI tvrdilo opak a väčšinu z tých dní to nikto nečítal.

Pravidlo, ktoré bolo porušené, je staré. Emacs, `importlib` v CPythone aj index gitu berú stat súboru
pred čítaním, cargo si zapíše čas začiatku buildu skôr, než rustc číta zdrojáky, a git dôvod
dokumentuje pod [racy-git](https://git-scm.com/docs/racy-git). Pravidlo som poznal a napísal som opačné poradie. Pravidlo je
staré. Tento text pridáva meranie: dve príčiny, ktoré vyzerali správne a boli vyvrátené, tú, ktorá
obstála, a štvrtú, ktorú som po vydaní opravy pomenoval nesprávne.

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

Ôsmeho septembra workflow `tests` zlyhal v 13 behoch za sebou, raz prešiel na `81b042f` a zlyhal
znova. Hlavná príčina bola trápna a nesúvisiaca: 8 z posledných 11 červených behov padlo na probe
o inštalácii hookov. Ďalšie tri padli na probe zámku, ktorý porovnával počet čistých pokusov s
konštantou, kým kód nad ním neplatné pokusy zahadzoval, takže worker, ktorý sa na runneri nespustil,
sa čítal ako stratený záznam, a v poslednom z nich hlásenie vypísalo straty ako `[0, 0, 0]` hneď
vedľa zlyhania, ktoré ohlasovalo. To bolo opravené v `e7a0d19`. Beh na tom commite bol zelený na
druhý pokus. Prvý pokus stratil 1 z 84 záznamov na defekte, o ktorom je tento text, a opakovanie to
zo zoznamu vymazalo.

V tom šume bol jeden skutočný riadok: probe súbežných zapisovateľov hlásil záznam, o ktorom bolo
zapisovateľovi povedané, že je uložený, a v úložisku nebol. Commitnutý receipt toho probe nesie ten
istý tvar z lokálneho behu, 448 nahlásených záznamov a 1 chýbajúci. To je vlastnosť, ktorú produkt
predáva, zlyhávajúca, v behu, ktorý nikto neotvoril, lebo predošlých desať bolo červených z iného
dôvodu. Po desiatich červených behoch za sebou jedenásty nikto neotvorí, takže pipeline už vtedy neniesol
žiadny signál.

## Prvá príčina, zmeraná a nesprávna: zámok

Úložisko drží platformový zámok okolo každého uloženia. Na platforme bez `fcntl` a `msvcrt` zapíše
aj tak, nechránene, a do tohto mesiaca tá vetva nenechala žiadnu stopu. Zrejmá hypotéza bola, že CI
runnery idú touto vetvou. Probe bol upravený tak, aby hlásil stav zámku za každé rameno, a straty sa
objavovali so zámkom držaným pri každom zápise. Nechránená vetva sa odteraz zaznamenáva a vypisuje
dôvod, takže táto hypotéza sa nabudúce overí jedným riadkom, nie dňom.

## Druhá príčina, zmeraná a nesprávna: podpis

Každý handle si drží podpis súboru, ktorý naposledy čítal, `(mtime_ns, size)`, a odmietne uložiť cez
súbor, ktorého podpis sa zmenil. Dva rovnako dlhé zápisy v jednom tiku mtime by na tomto podpise
kolidovali, a na tomto NTFS stroji sa mtime v tom istom receipte posúval v krokoch 0,5 až 1,5 ms, takže
kolízia je reálna. Zmerané na 1 500
rovnako dlhých zápisoch v receipte na `2e8483a`: `(mtime_ns, size)` kolidoval 211-krát; pridanie `st_ino` alebo hashu obsahu
to zrazilo na 0.

Tretie rameno teda podpis rozšírilo. Nestratilo nič, a nestratilo nič ani rameno, ktoré opravilo len
poradie. Kolízie existujú a túto stratu nespôsobili. Podpis je vo vydaní nezmenený.

Tá veta je užšia, než vyzerá, a nepriateľské opakovanie probe našlo jej hranu. Každý zapisovateľ v
tejto záťaži pridáva, takže každý pristátý zápis je väčší než súbor, proti ktorému bol overený, a dva
rôzne stavy nikdy nezdieľajú veľkosť. V tejto záťaži `(mtime_ns, size)` nemôže kolidovať inak než cez
samotný defekt poradia, preto v opakovaní stratil aj podpis len z veľkosti 0 z 1 432 a podpis len z
mtime 0 z 1 416. Prepisy rovnakej veľkosti v jednom tiku mtime, 1 ms na tomto NTFS a 4 ms na ext4,
sú režim, kde by rozšírenie záležalo, a ten je tu nezmeraný.

Poznámka k tým 211. Poznámky k vydaniu 2.27.1 hovorili 119. Commitnutý receipt hovorí 211 a poznámky
hovorili 119, lebo číslo bolo napísané, nie prečítané. Záver sa nehýbe, kolízie boli vyvrátené tak či
tak, ale číslo v poznámkach bolo deň nesprávne a v 2.27.5 je opravené.

## Príčina, ktorá obstála: strážca opisoval súbor, ktorý nikdy nevidel

`_load_from_disk` súbor prečítal, rozparsoval a potom opečiatkoval podpis. Cez tie dva kroky nič
nedrží zámok; zámok pokrýva ukladanie. Zapisovateľ, ktorý súbor vymenil medzi čítaním a pečiatkou,
nechal načítavajúci handle so starými záznamami pod novým podpisom. Strážca pri ukladaní porovnal
podpisy, nevidel zmenu a prepísal celé úložisko zo zastaraného pohľadu. JSON úložisko nevie zlučovať,
takže záznam druhého zapisovateľa zmizol, a tomu zapisovateľovi už bolo povedané, že je uložený.

Oprava je poradie: zober podpis pred čítaním. Potom sa zmena môže vkradnúť len počas čítania, čo
nechá uložený podpis starší než súbor, a strážca nahlási rozdiel, ktorý tam nie je. Volajúci dostane
`StoreChangedOnDisk`, ktoré môže zopakovať. Falošné odmietnutie stojí jedno opakovanie. Tichý
prepis stojí záznam, o ktorom nikto nevie, že chýba.

## Ako vyzerá deterministický test

Rasa, ktorá stratí jeden záznam z 320, nie je test. Test, ktorý toto prišpendlí, monkeypatchne
čítanie prvého handlu tak, aby druhý, skutočný handle zapísal doprostred neho, a potom overí, že záznam, ktorý pristál
počas čítania, je po uložení prvého handlu stále tam. Tri prípady: zápis počas čítania nie je
prepísaný, neskorý handle stále uloží svoj vlastný záznam a kontrola bez konkurenčného zápisu
zachová všetko. Na starom poradí padne zakaždým a na novom prejde zakaždým. Probe zostáva vedľa neho kvôli
číslu.

## Oprava vyšla, CI stratilo ďalší záznam a ja som mu pomenoval nesprávnu príčinu

Oprava poradia vyšla ako 2.27.1 a jej poznámky varovali, že oprava pristane na nahlásenej
inštancii, kým trieda prežije. Potom CI na `ubuntu-latest`, ktorý GitHub dáva verejnému repozitáru
so 4 vCPU, stratilo `w7:r0` na commite `0a26545`, so zámkom držaným pri každom zapisovateľovi a s
poradím už opraveným.

Pri jeho hľadaní som našiel skutočný defekt. `reload()`, cesta opakovania, ktorú správa
`StoreChangedOnDisk` odporúča, volá opravený loader cez `_merge_with_disk`, ktorý potom znova
priradil čerstvý podpis: stat po čítaní, mimo zámku. Do probe pribudli dve ramená, ktoré opakujú
cez `reload()`, a na ext4 pripnutom na 2 CPU, 80 kôl po dvanástich zapisovateľoch:

```
rameno                                                  nahlásených   chýba
old-order     (podpis po čítaní, 2.27.0)                      7 680      50
fixed         (podpis pred čítaním, 2.27.1)                   7 680       0
widened       (pred čítaním, plus st_ino)                     7 676       0
reload-old    (2.27.1, opakovanie cez reload(), s pečiatkou)  7 680      15
reload-fixed  (2.27.5, pečiatka odstránená)                   7 680       0
```

To vyšlo ako 2.27.5, s deterministickým testom, a poznámky k vydaniu hovorili, že to CI chytilo.
Mýlili sa a našla to overovacia pasáž nad týmto textom, tým, že čítala CI harness namiesto môjho
opisu. Harness `reload()` nikdy nevolá. Reopenuje, ako probe. Beží na predvolenom riadkovom
úložisku, ktorého save sa k tej istej pečiatke dostane, ale to úložisko zapisuje iba id, ktorých sa
dotklo, a mazania odvodzuje z baseline prečítanej pri tom istom otvorení, takže zastaraný podpis
tam susedov riadok zmazať nemôže. Zmerané na CI ceste, riadkové úložisko a reopen pri odmietnutí, s
vrátenou pečiatkou: 0 z 7 548 stratených na 2 CPU a 0 z 7 248 na 4, kým kontrola so starým
poradím stratila 40 a 41. Defekt v `reload()` je skutočný a opravený, a nie je to to, čo CI zasiahlo.

Dve straty CI boli `w7:r0` a `w1:r0`, prvý záznam zapisovateľa obakrát, a ten tvar bol v logoch od
prvej z nich. Probe s 8 zapisovateľmi po jednom zázname, v dvoch podmienkach, ext4 na 4 CPU, 200 kôl
každá:

```
podmienka                                            prvých zápisov nahlásených   chýba
súbor pri štarte zapisovateľov neexistoval                                1 600       3
súbor existoval s jedným záznamom                                         1 600       0
```

Rasa pri vytváraní. `sqlite3.connect` vytvorí súbor skôr, než prvý commit zapíše hlavičku SQLite.
Druhý handle, ktorý sa otvorí v tom okne, vidí súbor, ktorý existuje a nevyzerá ako riadkové
úložisko, prečíta ho ako JSON úložisko bez záznamov, skonvertuje to nič na riadky a výsledok
položí cez `os.replace` na cestu, mimo akéhokoľvek zámku. Prvému zapisovateľovi už bolo povedané,
že jeho záznam je uložený. 2.27.6 tú konverziu robí pod zámkom úložiska a vnútri znova prečíta
hlavičku, takže úložisko, ktoré medzitým vytvoril sused, sa načíta, nie nahradí: 0 z 1 600 na tom
istom probe. Deterministický test okno reprodukuje bez časovania a na 2.27.5 padne 2 z 3.

Poznámky k 2.27.5 teraz nesú opravu vedľa viet, ktoré boli nesprávne, rovnako ako poznámky k
2.27.1 nesú tých 119. Dve vydania za sebou opravili každé niečo skutočné a každé na jednom mieste
nesprávne opísalo vlastný dôkaz, a obakrát bol receipt, ktorý to ukázal, taký, ktorý som nečítal.

## Čo by som urobil inak

Čítať červený pipeline ako vlastnú chybu, skôr než skryje tú ďalšiu. Nechať každého strážcu povedať,
ktoré záznamy stratil, nie koľko, lebo „1 chýba" ma poslalo k zámku a k podpisu, a mená stratených
záznamov by ukázali na handle, ktorý držal zastarané dáta. A keď za jeden deň zomrú dve hypotézy,
napísať do poznámok k vydaniu, že zomreli, aby ďalší človek ten deň nestrávil znova. Poznámky
k 2.27.1 to robia; tento text je dlhšia verzia.

Nepriateľské opakovanie nechalo aj účet. Na Windows pri tejto záťaži asi jedno otvorenie zo sto
vyhodí `PermissionError`, lebo loader číta súbor, kým ho sused vymieňa, a neopakuje. Ten
zapisovateľ neuloží nič a povie to, čo je poctivá polovica ponuky, a stále je to defekt. Je ďalší na
rade.

---

Receipty: `probes/does_a_wider_change_signature_stop_the_silent_loss.result.json` (tri ramená, 30
kôl), `probes/what_a_concurrent_writer_is_told_against_what_the_store_keeps.result.json` (stav zámku
za rameno a kontrola, ktorá zámok odstráni) a
`tests/test_a_write_between_the_read_and_the_signature_is_invisible.py`, všetko v
DanceNitra/inspeximus na `2e8483a` alebo neskôr. Päťramenné behy sú
`probes/does_a_wider_change_signature_stop_the_silent_loss.linux-2cpu.result.json` (Linux, 80 kôl)
a windowsový `.result.json` na `30a734f` alebo neskôr, s
`tests/test_a_reload_that_restamps_after_the_read_repeats_the_defect.py`. Ramená CI cesty sú
`.rows-linux-2cpu.result.json` a `.rows-linux-4cpu.result.json` a rasa pri vytváraní je
`probes/is_the_first_write_of_a_fresh_handle_the_one_that_goes_missing.py` s jeho `.linux-4cpu.result.json`
(2.27.5) a `.linux-4cpu.fixed.result.json` (2.27.6), plus
`tests/test_a_peer_creating_the_store_is_not_migrated_over.py`, všetko na tagu `v2.27.6`. Počet CI behov je `gh run list --workflow tests`
nad tým repozitárom, behy od 6. do 8. septembra končiace na `6eee2de`.
