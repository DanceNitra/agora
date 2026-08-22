# Dva sklady v jednom produkte: jedno provenance pole má 8 odlišných hodnôt na 217 549 záznamov, druhé 101. Ani jedno nevedie nikam

Robím pamäťovú vrstvu pre agentov. Má pole `source` a jeho pokrytie som už verejne citoval. Minulý
týždeň som ho pred ďalším citovaním premeral a číslo sa posunulo, tak som sa išiel pozrieť prečo.

Jedenásť živých skladov, 234 971 záznamov, `source` vyplnené na 92,63 %. Ten priemer skrýva dve
zapisovacie cesty, ktoré zlyhávajú opačným smerom.

```
skupina skladov        záznamov   src %  odlišné  odlišné/zdrojované  dohľadateľné
osem agentských        217 549  100,00%        8            0,000037             0
jeden coding sklad      16 131    0,63%      101            0,990196             0
```

**Agentské sklady** zapisuje jeden automat. `agent:scholar` je vo všetkých 26 928 záznamoch jedného
z nich, `agent:guard_r` vo všetkých 27 294 druhého. Osem skladov, osem odlišných hodnôt, po jednej na
sklad, a každá je meno procesu, ktorý zapisoval.

**Coding sklad** vyzerá presne opačne a oveľa zdravšie: 101 odlišných zdrojov na 102 zdrojovaných
záznamov, odlišnosť 0,99. Skoro každý záznam ukazuje inam.

Oba stĺpce vedú k **nule**. Nie „k málu". K nule, naprieč všetkými 234 971 záznamami, proti resolveru,
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

U mňa je to 0 z 234 971.

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

Sonda je jeden súbor bez závislostí a vypisuje obe kontroly vrátane tej resolverovej, ktorá musí
prejsť skôr, než čokoľvek nahlási:
[`a_provenance_field_at_100_percent_with_one_distinct_value.py`](https://github.com/DanceNitra/agora/blob/main/probes/a_provenance_field_at_100_percent_with_one_distinct_value.py).
Ak máte iný formát skladu, celá kontrola je `sum(1 for r in records if resolves(r.source))` a môj kód
na ňu nepotrebujete.

---

*Odlišnosť teraz hlási `check_sources()` v inspeximus 2.20.0, vedľa pokrytia aj vedľa počtu
dohľadateľných, a je zdokumentovaná ako detektor jedného degenerovaného tvaru, nie ako miera
dohľadateľnosti — práve kvôli tomu protipríkladu vyššie.*
