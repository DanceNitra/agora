# Dva sklady v jednom produkte: jedno provenance pole má 8 odlišných hodnôt na 217 549 záznamov, druhé 101. Ani jedno POLE nevedie nikam

**Oprava, 28. augusta 2026.** Posledná veta znela "Ani jedno nevedie nikam" a o coding sklade to
bola nepravda. u/perseus-computing zistil, ze resolver za tymito cislami nikdy neposlal ziadnu
poziadavku. Poriadna oprava znamenala pytat sa na cely zaznam namiesto jedneho pola, a odpoved sa
zmenila: v tom sklade ma 168 zo 174 zdrojovanych zaznamov lokator, ktory sa naozaj nacita, a pary
`meta.sha` + `meta.files` sa rozlozia v strome vlastneho commitu 426-krat zo 432. Provenancia tam
bola. Sedela o jeden kluc vedla pola, ktore som auditoval, a audit zuzeny na to pole nad nou
hlasil nulu. Stlpec nizsie s nazvom `dohladatelne` je premenovany na `adresovatelne`, co je to, co
meral; jeho nuly sa nemenia. Osem agentskych skladov sa nemeni tiez: tam nevedie nikam nic ani na
jednej urovni. Podrobnosti v update na konci.

Robím pamäťovú vrstvu pre agentov. Má pole `source` a jeho pokrytie som už verejne citoval. Minulý
týždeň som ho pred ďalším citovaním premeral a číslo sa posunulo, tak som sa išiel pozrieť prečo.

Jedenásť živých skladov, 235 055 záznamov, `source` vyplnené na 92,63 %. Sú to živé sklady, ktoré rastú aj počas merania, takže súčty sú snímka a receipt je opečiatkovaný; čísla, na ktorých tu záleží, sú tie, ktoré sa nehýbu. Ten priemer skrýva dve
zapisovacie cesty, ktoré zlyhávajú opačným smerom.

```
skupina skladov        záznamov   src %  odlišné  odlišné/zdrojované  adresovateľné
osem agentských        217 549  100,00%        8            0,000037             0
jeden coding sklad      16 215    0,63%      101            0,990196             0
```

**Agentské sklady** zapisuje jeden automat. `agent:scholar` je vo všetkých 26 928 záznamoch jedného
z nich, `agent:guard_r` vo všetkých 27 294 druhého. Osem skladov, osem odlišných hodnôt, po jednej na
sklad, a každá je meno procesu, ktorý zapisoval.

**Coding sklad** vyzerá presne opačne a oveľa zdravšie: 101 odlišných zdrojov na 102 zdrojovaných
záznamov, odlišnosť 0,99. Skoro každý záznam ukazuje inam.

Oba stĺpce vedú k **nule**. Nie „k málu". K nule, naprieč všetkými 235 055 záznamami, proti resolveru,
o ktorom viem dokázať, že funguje.

## Prečo zjavná metrika nepomôže, a dôkaz mám vo vlastných dátach

Keď v stĺpci uvidíte jednu konštantnú hodnotu, reflex je siahnuť po počte odlišných hodnôt delenom
počtom riadkov. To je skutočná, pomenovaná metrika — stĺpcová **Distinctness** v AWS Deequ,
*uniqueness* v prehľadovej práci Abedjana, Golaba a Naumanna, a
`expect_column_proportion_of_unique_values_to_be_between` v Great Expectations. ydata-profiling hlási
`CONSTANT` automaticky, keď je počet odlišných hodnôt jedna. Profiler by agentské sklady zachytil na
jeden prechod. Nikto ho na sklad agentskej pamäte nepustil, ani ja, a to je samo o sebe malý nález o
tomto kúte odboru.

Lenže coding sklad by odlišnosťou prešiel na 0,99 — a je presne tak isto nanič. Jeho zdroje vyzerajú
ako `git:162de50e1702`: skutočné commit SHA, naozaj odlišné, a nie cesta ani URL, takže ich nemá čo
nasledovať.

Ten protipríklad som si nemusel vymyslieť. Sedel v tom istom produkte ako ten prvý.

**Vysoká kardinalita nie je dohľadateľnosť.** Naplňte stĺpec jedným UUID na riadok a dostanete
dokonalých 1,0, kým nevedie nikam. Odlišnosť je dobrý detektor jedného degenerovaného tvaru a slepá
voči tomu vedľajšiemu.

## Čo W3C povedalo už v roku 2013

PROV-DM oddeľuje **`wasAttributedTo`**, teda agenta zodpovedného za entitu, od **`wasDerivedFrom`**,
teda entity, z ktorej vznikla. Moje agentské sklady zaznamenávajú pripísanie. Coding sklad zaznamenáva
commit, čo je bližšie, ale stále to nie je ten artefakt. Oboje sa číta ako odvodenie, lebo oboje žije
v poli s názvom `source` za číslom s názvom pokrytie.

Slovník, ktorý tomu mal zabrániť, je normatívny trinásť rokov, a aj tak som to postavil zle.

## Číslo, ktoré som mal publikovať

Nie pokrytie a nie odlišnosť. **Koľko záznamov má zdroj, ktorý vedie k niečomu, čo si čitateľ vie
naozaj stiahnuť.**

U mňa je to 0 z 235 055.

To číslo vie zlyhať, a v tom je celý jeho zmysel. Preto potrebuje kontrolu — a to je časť, ktorú som
najprv spravil zle: resolver, ktorý na všetko vráti `False`, nahlási nulu dohľadateľných nad
ľubovoľným korpusom a vyzerá presne ako korpus, kde žiadne nie sú. Sonda teraz zapíše skutočný súbor
aj https URL a odmietne čokoľvek nahlásiť, kým sa obe nevrátia ako dohľadateľné.

## Čo stále neviem povedať

**Či to spadlo, alebo to bola vždy nula.** 10. augusta som publikoval 210 499 záznamov pri 98,3 %
pokrytí a 0,01 % dohľadateľných — 24 záznamov, ktorých lokátor viedol k cieľu. Dnes je to 0. Tie
identifikátory som si nenechal. Rast menovateľa nevie vysvetliť, prečo počet klesol z 24 na 0, takže
reálne možnosti sú regresia resolvera, zmenená množina skladov, alebo tie riadky vyrotovali — a
vylúčiť neviem ani jednu. To je zlyhanie mojej meracej disciplíny a je moje.

**Či je nula normálna.** Mám jeden systém. Nemám distribúciu, do ktorej by som ho zasadil, a preto je
prosba nižšie číslo, nie argument.

## Prosba

Ak prevádzkujete pamäťovú vrstvu, RAG sklad alebo agentský framework s provenance poľom: **spočítajte
záznamy, ktorých zdroj vedie k niečomu, čo si viete stiahnuť, a napíšte ten počet spolu s celkovým
počtom.** Dve celé čísla.

Nie percento pokrytia a nie pomer odlišnosti. Mám oboje a nepovedali mi nič. To, ktoré mi niečo
povedalo, bolo to, čo vyšlo ako nula.

*Dve sa ukázali byť málo. Pozri doplnok nižšie, tam prosba stojí teraz.*

Sonda je jeden súbor bez závislostí a vypisuje obe kontroly vrátane tej resolverovej, ktorá musí
prejsť skôr, než čokoľvek nahlási:
[`a_provenance_field_at_100_percent_with_one_distinct_value.py`](https://github.com/DanceNitra/agora/blob/main/probes/a_provenance_field_at_100_percent_with_one_distinct_value.py).
Ak máte iný formát skladu, celá kontrola je `sum(1 for r in records if resolves(r.source))` a môj kód
na ňu nepotrebujete.


## Doplnok, 26. augusta: dvaja čitatelia posunuli meranie

Na r/RAG odpovedali traja ľudia a dvaja z nich zmenili to, čo považujem za správne číslo.

**Terrible_Front_583 rozdelil „pokrytie zdrojom" na tri veci, ktoré som považoval za jednu:**
prítomnosť poľa, sémantickú provenance a stiahnuteľnosť, pričom brána má vyžadovať dosiahnuteľný
zdrojový objekt plus snímku alebo verziu, vlastníka a kontrolu prístupu. Je to lepšie než moje dve
celé čísla a moje vlastné dáta mu dajú za pravdu v rámci jedného dotazu: prítomnosť je sama o sebe
dvojica čísel. V mojom coding sklade je kľúč `source` prítomný na každom z 20 162 záznamov v
opečiatkovanom receipte a hodnotu nesie na 145 z nich, teda 0,72 %. Kontrola schémy vidí prvé číslo.
Pokrytie, počítané tak, ako som ho počítal, vidí druhé. Ani jedno z nich nie je to, čo som publikoval.

Zvyšok tej vrstvy neviem oskórovať vôbec. Ani jedna z mojich schém nemá snímku, verziu, vlastníka
ani pole prístupu, takže tá vrstva u mňa nie je nula, je **nemerateľná**. To je horšia pozícia než
zlé skóre a žiadne percento pokrytia ju neukáže.

**arupbuildsai upozornil, že tu nie je jeden audit, ale dva:** či sa zdroj dá dosiahnuť a či
podporuje tvrdenie. Ten druhý spustil na produkčnom RAG asistentovi, ktorého citácie tiež vyzerali
zdravo, a našiel odpovede nesprávne asi v 35 % prípadov, pričom zneli isto a citácia často zdobila
tvrdenie, ktoré jej zdroj nikdy nespravil; presun chunkovania z veľkostného na hlavičkové a potom
sémantické to stiahol zhruba na 8 %. Moja sonda vie testovať vždy len prvú polovicu. Sťahuje, nikdy
nečíta, takže zdroj, ktorý vedie na stránku protirečiacu tvrdeniu, jej prejde čistý. Druhá polovica
už benchmarky má: ALCE meria presnosť a úplnosť citácií priamo (Gao a kol.,
[arXiv:2305.14627](https://arxiv.org/abs/2305.14627)) a AIS je staršie rámovanie (Rashkin a kol.,
[arXiv:2112.12870](https://arxiv.org/abs/2112.12870)).

**A číslo sa zase pohlo, čo je jediná vec, ktorú tento článok o sebe predpovedal.** Nový beh dnes:
240 715 záznamov v tých istých jedenástich skladoch, `source` vyplnené na 91,15 %, dohľadateľných 0.
To je o 5 660 záznamov viac než v tabuľke vyššie a každý jej súčet je teraz zastaraný. Dohľadateľných
bolo 0 pri každom meraní od vydania tohto článku; počet, ktorý stále neviem vysvetliť, je tých 24 z
10. augusta.

Takže prosba znie na tri počty, nie na dva. Koľko záznamov máte, koľko z nich vôbec nesie hodnotu v
zdroji a koľko z tých vedie k niečomu, čo si čitateľ vie stiahnuť. To tretie je to, ktoré môže
zlyhať.

---

*Odlišnosť teraz hlási `check_sources()` v inspeximus 2.20.0, vedľa pokrytia aj vedľa počtu
dohľadateľných, a je zdokumentovaná ako detektor jedného degenerovaného tvaru, nie ako miera
dohľadateľnosti — práve kvôli tomu protipríkladu vyššie.*


## Update, 28. augusta: resolver nikdy neposlal poziadavku a titulok bol nepravdivy

u/perseus-computing pustil publikovany probe na `https://example.invalid/...` a vratilo sa to ako
dohladatelne. Mal pravdu a funkcia bola horsia, nez pisal: prefixovy test plus `os.path.exists`,
takze nikdy neposlala ziadnu poziadavku, a presiel jej aj holy retazec `https://`, schema bez hosta.

Su z toho dve funkcie. `addressable` je syntax. `retrieves` otvori subor alebo posle jeden GET a
uzna len 2xx. Kontrola je jeho navrh, lokalny server, ktory na jednej ceste odpoveda 200 a na inej
404, a bezi cez tu istu fixture, ktorou prechadza korpus, nie cez samotnu funkciu.

Prvy pokus o tu opravu je uzitocnejsia chyba. Pridal retriever, dal mu kontrolu a nechal sken volat
staru funkciu, takze retriever presiel vlastnym testom bez toho, aby videl jediny zaznam korpusu.

**Potom nepriatelsky prepocet mojich vlastnych cisel zabil titulok.** Audit bol zuzeny na pole
`source` a ja som nulu nad tym polom precital ako nulu nad zaznamami. Kazde cislo v tomto odseku je
z receiptu s peciatkou `2026-08-27T22:03:30Z` a vsetky sa hybu: o dvadsat minut neskor, ked vznikala
odpoved pre neho, uz prvy par cital 170 zo 176 a druhy 441 zo 447. Provenancne cislo bez casu je ta
ista trieda chyby, o ktorej je tento post. V coding sklade ma 168 zo 174 zdrojovanych zaznamov
lokator, ktory sa naozaj nacita. Pary `meta.sha` a `meta.files` sa rozlozia v
strome vlastneho commitu 426-krat zo 432 a vsetkych 171 odlisnych shas su skutocne commity.
Provenancia tam cely cas bola, o jeden kluc vedla pola, ktore som auditoval.

Je tam vyhrada, ktoru som nasiel az spravnou otazkou. Z tych 171 commitov je 161 dosiahnutelnych z
verejneho main. Desat nie, takze desat tych referencii vie overit len autor a nikto iny, co je pri
tvrdeni publikovanom cudzim ludom ina nula.

Co plati dalej: osem agentskych skladov, 220 417 zaznamov, osem odlisnych hodnot a nic, co by viedlo
niekam, na ziadnej urovni. To je argument, ktory post robil, a ten sa nemeni. Co neplati: coding
sklad ako druhy priklad. Jeho zaznamy boli protipriklad, ktorym som argumentoval, a tie sa rozlozia.

Chyba bola v pristroji na oboch stranach, takze stoji za to pomenovat, co sa v nom zmenilo. Kontrolna
fixture pouzivala stringove zdroje, kym kazdy zaznam v realnom korpuse je objekt, a mutacia citaca,
ktora objekty ignoruje, znizi pokrytie z 90 % na 0,00 % pri stale zelenej kontrole. Strop na
nacitania ratal aj otvorenia lokalnych suborov, takze zatal na 200 so 148 neskusanymi lokatormi a
podcenene cislo vydal ako vysledok. Neadresovatelne retazce sa ratali ako sietove pokusy, 169 z nich
pri behu, ktory neotvoril ziadny socket. A receipt teraz nesie `measured_at`, lebo pocet zaznamov sa
v jednej relacii pohol styrikrat a zaznamova uroven isla v piatich minutach zo 167 na 168.

Sprievodny subor lame probe siedmimi sposobmi a zlyha, ak niektora mutacia prezije, vratane chyby,
ktoru nahlasil, a oboch smerov, ktorymi retriever zlyhava. Ano-na-vsetko prejde kontrolou len na 200.
Nie-na-nic prejde kontrolou len na 404, a nie-na-nic nie je hypoteza: skorsia verzia ho mala a jej
odpoved bola nula, co je zaroven titulok tohto postu.
