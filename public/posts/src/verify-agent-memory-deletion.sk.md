# Zmazal si používateľove dáta. Vieš dokázať, že sú preč?

**Krátka verzia.** Pamäť tvojho agenta má `delete()`. Vráti úspech. To ti hovorí, že volanie prebehlo — nie že dáta odišli. Vo väčšine stackov žije hodnota na viac ako jednom mieste: vo vektore, v payloade alebo metadátach vedľa neho, a často aj v histórii či audit logu. Mazanie, ktoré vyčistí jedno a nie ostatné, vráti presne ten istý úspech. **[Táto voľná kontrola](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py)** vloží do tvojho úložiska unikátnu značku, zavolá *tvoj* backend a jeho vlastné mazanie aj kompakciu, potom prečíta surové súbory a povie ti, či sú bajty tej značky stále tam. O ničom cudzom netvrdí nič. Dá ti receipt na tvoj vlastný stack.

## Medzera je medzi povinnosťou a pozorovateľnou veličinou

Článok 17(1) GDPR je o povinnosti jednoznačný: prevádzkovateľ „shall have the obligation to erase personal data without undue delay". Článok 19 dodáva, že príjemcom tých dát treba oznámiť, že k vymazaniu došlo.

Oboje je formulované ako výsledok. Ani jedno nie je vec, ktorú tvoj kód hlási. Tvoj kód hlási, že funkcia sa vrátila bez výnimky.

V tej medzere žije overovanie a v ekosystéme agentovej pamäte ju takmer nič nevypĺňa. Textov o tom, *ako byť v súlade*, je dosť. O tom, *ako to skontrolovať*, skoro nič.

## Prečo úspešné mazanie môže dáta nechať na mieste

Tri miesta, kde hodnota prežije mazanie, ktoré ohlásilo úspech:

| kde | prečo prežije |
|---|---|
| **vektorový index** | štruktúry pre približných najbližších susedov (HNSW, IVF) často uzol označia ako odstránený namiesto prestavby grafu. Vektor zostáva v súbore dosiahnuteľný až do prestavby |
| **payload alebo metadáta** | mnohé úložiská držia pôvodný text vedľa embeddingu. Zmazanie vektorového záznamu nemusí zmazať riadok, ktorý niesol text |
| **história alebo audit log** | niektoré backendy zaznamenávajú každý zápis a mazanie zámerne. Je to vlastnosť, nie chyba — ale hodnota je stále na disku, a compliance čitateľ to bude čítať ako zadržanie |

To prvé nie je folklór a čísla sú horšie, než ten mechanizmus znie. [Ghost Vectors](https://arxiv.org/abs/2606.18497) (Chakraborttii a kol., 2026) otestovali tri HNSW implementácie a z mäkko zmazaných embeddingov obnovili **pôvodný text** — čítaním surových index súborov na úrovni úložiska, úplne mimo API, a inverziou vektorov. Na wikipedijnom biografickom datasete obnovili **25,5 % presných mien osôb** a **46,4 % geografických lokalít**. Na štruktúrovaných zdravotných záznamoch **100 % veku a pohlavia pacienta**. Na tvárových embeddingoch **99 % identity**. Ich navrhovaná oprava šifruje každý vektor a pri mazaní zničí kľúč, pričom vydá ECDSA-podpísaný dôkaz o tom vymazaní — čiže výskum konverguje k tej istej odpovedi: overiteľné mazanie poráža deklarované.

Nič z toho neznamená, že tvoj stack je pokazený. Znamená to, že otázka „zabralo to mazanie?" má odpoveď, ktorú si nezmeral.

## Spusti si to na vlastnom úložisku

Kontrola je jeden súbor, štandardná knižnica plus tie backendy, ktoré už máš nainštalované. Nájde si ich sama.

```bash
curl -O https://raw.githubusercontent.com/DanceNitra/ramr/main/integrity/erasure_selfcheck.py
python erasure_selfcheck.py
```

Do každého nájdeného backendu zapíše značku, zavolá jeho dokumentované `delete`, spustí jeho dokumentovanú kompakciu a potom prehľadá surové súbory úložiska na bajty tej značky. Výstup vyzerá takto:

```
==========================================================================
agent-memory erasure self-check - YOUR stack
==========================================================================
  inspeximus   absent
  your-store   PRESENT        somefile.sqlite3
--------------------------------------------------------------------------
'PRESENT' = the marker's bytes are still in the store's files after its own
delete + compaction (logical residue).
```

`absent` znamená, že bajty sú po vlastnom upratovaní úložiska preč. `PRESENT` znamená, že nie sú — a súbor, ktorý ich stále drží, je pomenovaný, aby si sa mohol pozrieť sám.

Publikujeme nástroj, nie rebríček. Ak ťa nejaký výsledok prekvapí, správny ďalší krok je issue tracker toho backendu cez bežné koordinované zverejnenie — nie blogový článok, a nie tento.

## Ako výsledok čítať poctivo

O tom, či taká kontrola za niečo stojí, rozhodujú dve veci.

**Musí vedieť zlyhať.** Test, ktorý tvrdí, že `delete()` vrátil OK, prejde aj na implementácii, ktorá nemaže nič. Tento tvrdí niečo o bajtoch v úložisku po tom — čo je tvrdenie o svete, nie o volaní.

**Potrebuje pozitívnu kontrolu.** Zmaž jeden záznam, over, že je preč — a potom over, že **iný** záznam tam stále je. Bez tej druhej polovice by úložisko, ktoré ticho zmazalo všetko, dostalo plný počet. Každý test mazania, ktorý si napíšeš sám, by mal niesť tú dvojicu; náš ju nesie a je to prvá vec, ktorú treba hľadať v cudzom.

## Čo ti to nepovie

Rozsah, povedaný rovno, lebo overovací nástroj, ktorý svoj dosah nadhodnocuje, je horší než žiadny.

- **Kontroluje logický zvyšok, nie bezpečnosť v pokoji.** Plaintextové úložisko *ktorejkoľvek* knižnice necháva bajty vo voľnom priestore, v over-provisioned blokoch SSD a v zálohách. Obranou je tam šifrovanie celého disku a krypto-vymazanie, čiže zničenie kľúča. Túto vrstvu kontrola neposudzuje a ani nemôže.
- **Porovnáva doslovné bajty.** Uloženú hodnotu chytí, jej parafrázu nie. Čistý výsledok je dôkaz, nie istota.
- **`PRESENT` z audit logu je dizajnové rozhodnutie, nie chyba.** Niektoré backendy históriu držia zámerne. Zavolaj ich dokumentovaný purge a spusti to znova.

## Čo s tým robíme my

Overiteľné mazanie je os, na ktorej je naša knižnica postavená, takže je férové povedať konkrétne, čo to znamená. `inspeximus` maže obsah, nie ho označuje náhrobkom, a každé vymazanie vracia správu o zvyšku: koľko záznamov sa prehľadalo, aké hodnoty sa hľadali, čo sa našlo — a tú istú výhradu, čo je vytlačená vyššie, že porovnanie podreťazcov chytí uloženú hodnotu a minie parafrázu. Nástroj si svoje limity vypisuje vo vlastnom výstupe.

To je celá dizajnová pozícia. Mazanie, ktoré sa nedá skontrolovať, je sľub. Mazanie, ktoré vráti receipt overiteľný bez toho, aby si nám veril, je kontrola.

Spusti si tú kontrolu najprv na svojom. Ak vyjde čisto, dozvedel si sa zadarmo niečo, čo stojí za vedenie.

## Časté otázky

**Zmaže mazanie z vektorovej databázy dáta naozaj?**
Nie vždy. Vektorové indexy často záznam označia ako odstránený namiesto prestavby, a pôvodný text býva v payloade alebo metadátach, ktorých sa mazanie vektora nedotkne. Volanie aj tak vráti úspech.

**Ako overím vymazanie v pamäti svojho agenta?**
Zapíš známu značku, zmaž ju cez vlastné API backendu, spusti jeho kompakciu, potom prečítaj surové súbory úložiska a hľadaj tú značku. Ak sú bajty stále prítomné, mazanie ich z disku neodstránilo.

**Sú embeddingy osobné údaje podľa GDPR?**
Ak embedding vzniká z textu obsahujúceho osobné údaje a dá sa spätne spojiť s identifikovateľnou osobou — cez uložené páry, metadáta alebo re-identifikáciu — zaobchádza sa s ním ako s osobným údajom. Tým sa vektor sám dostáva do rozsahu článku 17.

**Stačí na právo na vymazanie mäkké mazanie?**
Mäkké mazanie skryje záznam pred dopytmi a nechá ho v úložisku. Či to spĺňa článok 17, je otázka na tvojho DPO a regulátora — ale praktický bod je skorší: kým nevieš, ktoré z tých dvoch tvoj stack robí, nemáš z čoho súdiť. Táto kontrola ti to povie.

*Spustiteľný receipt ku všetkému vyššie: [`integrity/erasure_selfcheck.py`](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). Je deterministický, beží offline a testuje len tie backendy, ktoré už máš nainštalované.*
