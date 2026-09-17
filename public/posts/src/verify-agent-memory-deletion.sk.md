# Zmazali sme jeden záznam z piatich AI pamäťových úložísk. Dve ho mali stále na disku.

Uložili sme záznam do piatich úložísk agentovej pamäte, zmazali ho cez vlastné API každého úložiska, spustili kompakciu, ktorú každé úložisko ponúka, a prehľadali surové súbory. Na jednom stroji 17. septembra 2026, s chromadb 1.1.1, qdrant-client 1.18.0 v lokálnom režime, mem0ai 2.0.11, lancedb 0.30.0 a inspeximus 2.24.0, dve z piatich držali bajty záznamu aj potom. Všetkých päť volaní delete vrátilo úspech. Oba prípady sú zdokumentované: mem0 vedie log histórie zámerne a Chroma drží text vo write-ahead logu, kým neprebehne 1 000 operácií. Druhý záznam, ktorý nikto nemazal, ostal v každom úložisku, a podľa toho vieme, že „absent" znamená, že úložisko zmazalo jeden záznam a nie všetko. Kontrola je [jeden súbor](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). Beží na backendoch, ktoré máš nainštalované, pomenuje súbor, ktorý bajty stále drží, a hlási tvoje verzie.

*Toto vyšetrovanie je aj epizódou nášho podcastu Echoes of Tomorrow, rozprávanou ako detektívka: [vypočuj si ju na Spotify](https://open.spotify.com/episode/7khBL2ppx1uTfsY9UtuLMJ).*

## Medzera je medzi povinnosťou a pozorovateľnou veličinou

Článok 17(1) GDPR stanovuje povinnosť: prevádzkovateľ „shall have the obligation to erase personal data without undue delay", ak platí jeden z vymenovaných dôvodov. Článok 19 dodáva, že príjemcom tých dát to treba oznámiť, pokiaľ sa to neukáže ako nemožné alebo neprimerane náročné.

Oboje je formulované ako výsledok. Ani jedno nie je vec, ktorú tvoj kód hlási. Tvoj kód hlási, že funkcia sa vrátila bez výnimky.

Kde je pozornosť regulátorov, ukazuje ich vlastný prieskum. Správa EDPB o koordinovanom vymáhaní práva na vymazanie, prijatá 18. februára 2026, vychádza z 32 dozorných orgánov a 764 prevádzkovateľov. Problémy, ktoré menuje, sú procesné: chýbajúce interné postupy, „reliance by some controllers on inefficient anonymisation techniques to handle erasure requests as an alternative to deletion" a ťažkosti s retenčnými lehotami a „the deletion of personal data in the context of back-ups". O kontrole, či bajty odišli, nehovorí nič. O vektorových úložiskách nič. Text zákona je teda prísny a precedens vymáhania pre zvyšky dát neexistuje. Dnes je zabudnutá hodnota problém správnosti a dôvery a problémom súladu sa stane, keď sa na ňu niekto opýta.

## Každý engine fyzické mazanie odkladá, a to nie je novinka

Databázy označujú riadky ako zmazané a miesto uvoľňujú neskôr, odkedy existujú. Stahlberg, Miklau a Levine na SIGMOD 2007 ukázali, že nástroje, ktoré obídu SQL rozhranie a prehľadajú binárne súbory, obnovia zmazané záznamy z PostgreSQL, MySQL, DB2 a SQLite, s vacuumom aj bez neho. Vektorové úložiská ten návrh zdedili. Nové je iba to, kam agentová pamäť ukladá osobné údaje, a ako zriedka to odkladanie niekto kontroluje.

| kde hodnota prežije | čo hovorí výrobca | číslo |
|---|---|---|
| vektorový index (server) | Qdrant odstraňuje zmazané vektory po segmentoch, keď sú splnené dva prahy. Maintainer na trackeri: odstrániť ich „immediately is more expensive than keeping them until enough have been deleted." | `deleted_threshold: 0.2` a `vacuum_min_vector_number: 1000` v konfigurácii Qdrantu |
| write-ahead log | Chroma pripojí riadok DELETE; skorší riadok ADD s textom dokumentu ostáva, kým sa HNSW segment neuloží. Komentujúci v otvorenom issue: dovtedy purge „coalesces a missing vector-segment offset to -1 and deletes nothing." | `hnsw:sync_threshold`, predvolene 1000. Naše meranie, [jedna sonda](https://github.com/DanceNitra/agora/blob/main/research/probes/chroma_wal_retention_threshold.py): s prahom nastaveným na 50 text opustí súbor po 59 výplňových zápisoch, s predvoleným po 1020 |
| heap a index, kým nepríde vacuum | pgvector prepíše zmazaný prvok nulami, keď sa index vacuumuje (`memset` v `hnswvacuum.c`). Kedy sa to stane, rozhoduje PostgreSQL. | autovacuum sa spustí po viac než 50 plus 20 % tabuľky v mŕtvych záznamoch: nad 200 050 pri milióne riadkov |
| log histórie | mem0 vedie databázu histórie zámerne; `reset()` ju vyčistí. Jeho grafové úložisko tiež držalo zmazané uzly: issue #3245 bolo otvorené od 29. júla 2025, kým 23. marca 2026 neprišla oprava. | `history.db` |
| zálohy | Google Cloud opisuje mazanie ako etapy: soft delete, potom „deleted successively from Google's active and backup storage systems". | „about two months" z aktívnych systémov, zálohy „within six months", záväzok 180 dní |

Riadok o indexe je dôležitý, lebo zvyšok nie je iba text. [Ghost Vectors](https://arxiv.org/abs/2606.18497) (Chakraborttii a kol., preprint, jún 2026) invertovali soft-zmazané embeddingy späť na text v troch implementáciách HNSW. Na biografiách z Wikipédie hlásia obnovených 25.5 % presných mien osôb a 46.4 % geografických lokalít. Na syntetických zdravotných záznamoch 100 % značiek veku a pohlavia pacienta. Na embeddingoch tvárí 99 % top-1 identifikácie. Ich oprava šifruje každý vektor a pri mazaní zničí kľúč, čo stiahlo pozorovanú obnovu na 0 % a vydá ECDSA-podpísaný dôkaz o udalosti mazania. Čísla preprintu čakajú na recenziu; mechanizmus od nich nezávisí.

## Ako to volá NIST

NIST SP 800-88 Rev. 2, finálna verzia zo septembra 2025, je o pamäťových médiách a jej slová sem sedia s touto výhradou. Clear aplikuje „logical techniques to sanitize data in all user-addressable storage locations", proti „simple, non-invasive data recovery techniques using the same interface that is available to the user". Purge robí obnovu „infeasible using state-of-the-art laboratory techniques" a dokument ho uprednostňuje „when possible".

`delete()`, ktorý vrátil úspech, ti hovorí, že volanie prebehlo. Kontrola zvyškov, ktorá potom číta vlastné súbory úložiska, validuje výsledok na úrovni clear. Zničenie kľúča, ako v schéme Ghost Vectors alebo v kryptografickom mazaní Googlu pre Cloud Storage, je to, ako purge vyzerá v softvéri. Rev. 2 tú činnosť aj premenovala na „validation" a takmer všetky formulácie „verification" vypustila. Obe slová tu znamenajú to isté: pozri sa na médium po operácii namiesto návratového kódu operácie.

## Spusti si to na vlastnom úložisku

Kontrola je jeden súbor, štandardná knižnica plus backendy, ktoré už máš nainštalované. Nájde si ich sama.

```bash
curl -O https://raw.githubusercontent.com/DanceNitra/ramr/main/integrity/erasure_selfcheck.py
python erasure_selfcheck.py
```

Do každého backendu uloží dve značky, jednu zmaže cez zdokumentované API backendu, spustí to, čo backend ponúka ako kompakciu (SQLite VACUUM tam, kde je úložisko SQLite, `optimize()` v LanceDB, nič tam, kde sa nič neponúka), a potom v surových súboroch úložiska hľadá obe. Výstup vyzerá takto:

```
==========================================================================
agent-memory erasure self-check - YOUR stack
==========================================================================
  instrument   ok             reader must see an undeleted marker
  inspeximus   absent
  your-store   PRESENT        somefile.sqlite3
--------------------------------------------------------------------------
'PRESENT' = the marker's bytes are still in the store's files after its own
delete + compaction (logical residue). 'absent' = gone, and the undeleted
control marker is still there. 'control-failed' and 'compaction-failed' =
no verdict.
```

`absent` znamená, že bajty z vlastných súborov úložiska po jeho vlastnom čistení zmizli a druhá značka, tá, ktorú nikto nemazal, tam stále je. `PRESENT` znamená, že nezmizli, a súbor, ktorý ich stále drží, je pomenovaný. `control-failed` znamená, že zmizla aj druhá značka, takže úložisko zmazalo viac, než malo, alebo sonda nikdy nič nezapísala, a verdikt nie je. `compaction-failed` znamená, že kompakcia backendu vyhodila výnimku, a verdikt tiež nie je. Ten posledný stav existuje preto, lebo skoršia verzia tejto kontroly výnimku prehltla a pre LanceDB hlásila PRESENT, hoci žiadna kompakcia neprebehla; podporované `Table.optimize()` značku vyčistí. Verdikt po kroku, ktorý nikdy nebežal, opisuje nástroj a nie úložisko.

Náš beh zo 17. septembra 2026:

| backend | výsledok | kde |
|---|---|---|
| instrument | ok | |
| inspeximus | absent | |
| qdrant-local | absent | lokálny režim `qdrant_client`: tabuľka SQLite, bez segmentov, bez optimizéra. Nie server z tabuľky vyššie |
| lancedb | absent | po `optimize()` |
| mem0 | PRESENT | `history.db`, log histórie, zámerne |
| chroma | PRESENT | `chroma.sqlite3`, write-ahead log, pod `hnsw:sync_threshold` |

Každá kontrolná značka prežila, takže každý `absent` je mazanie presne toho, čo bolo žiadané. Oba riadky `PRESENT` sú zdokumentované správanie a tabuľka pri každom menuje prah alebo návrhové rozhodnutie. Dva zápisy nemôžu prekročiť prah 1 000 operácií, takže na úložisku s prahom táto kontrola hlási stav tichej kolekcie, čo je stav, v ktorom je úložisko osobných údajov s nízkou prevádzkou väčšinu času. Ak ťa výsledok na tvojom stacku prekvapí, správny ďalší krok je issue tracker backendu.

## Ako čítať výsledok poctivo

O tom, či má takáto kontrola nejakú cenu, rozhodujú dve veci.

Musí vedieť zlyhať. Test, ktorý overí, že `delete()` vrátil OK, prejde aj na implementácii, ktorá nemaže nič. Tento overuje bajty úložiska po operácii, čo je tvrdenie o svete, nie o volaní. Riadok `instrument` spustí ten istý čítač na adresári, kde sa nič nemazalo; ak nehlási PRESENT, každý ďalší riadok je neplatný.

Potrebuje pozitívnu kontrolu. Zmaž jeden záznam, over, že je preč, a potom over, že iný záznam tam stále je. Bez druhej polovice by úložisko, ktoré potichu zmaže všetko, dostalo dokonalý pass. Každá kontrola backendu tu nesie tento pár.

Počítanie riadkov cez API meria to, čo ti API ukáže. Po mazaní sa úložiska opýtaj na ten fakt a prečítaj surové súbory. Oboje je lacné.

## Čo ti to nepovie

- Kontroluje logické zvyšky, nie bezpečnosť v pokoji. Nešifrované úložisko akejkoľvek knižnice necháva bajty vo voľnom mieste, v over-provisionovaných blokoch SSD a v zálohách. Obrana tam je šifrovanie celého disku a crypto-erasure, zničenie kľúča. Táto kontrola tú vrstvu nesúdi.
- Porovnáva doslovné bajty. Uloženú hodnotu chytí; jej parafrázu nie, a ani embedding, ktorý už text neobsahuje. Ghost Vectors obnovuje z vektora; tento čítač nie. Úložisko, ktoré svoje stránky komprimuje alebo kóduje, týmto čítačom prejde bez toho, aby čokoľvek zmazalo, a súbor, ktorý čítač nevie otvoriť, sa hlási ako bez verdiktu, nikdy ako absent.
- Beží tam, kde vieš čítať súbory. Na hostovanom úložisku, Pinecone, Qdrant Cloud, mem0 Platform, Chroma Cloud, nevieš, a jediná spustiteľná polovica je opýtať sa úložiska znova. Prahy kompakcie sú tam na kolekciu alebo na segment, nikdy na subjekt, takže latencia vymazania jedného subjektu závisí od objemu zápisov všetkých ostatných nájomcov.
- `PRESENT` z prahu alebo z audit logu je návrhové rozhodnutie. Zavolaj zdokumentovaný purge backendu a spusti to znova.
- Je to prevádzkovateľ, ktorý kontroluje prevádzkovateľa. Správa o zvyškoch od strany, ktorá mazala, naša nevynímajúc, je vlastné potvrdenie. Dôkaz, ktorý si tretia strana overí bez čítania disku prevádzkovateľa, je iná vec a venuje sa jej ďalšia časť.

## Overenie o vrstvu vyššie

Tá istá medzera existuje vo váhach modelu. Eisenhofer, Riepel, Chandrasekaran, Ghosh, Ohrimenko a Papernot ([IEEE SaTML 2025](https://arxiv.org/abs/2210.09126)) vychádzajú z premisy, ktorú pripisujú skoršej práci, že používateľ „is unable to verify whether their data was unlearnt from an inspection of the model parameter alone". Navrhujú kryptografickú definíciu overiteľného unlearningu a protokol na SNARKoch a hash reťazcoch, v ktorom server dokáže, že záznam nie je v trénovacej množine, a dôkaz si overí niekto, kto váhy nikdy nevidel. Podpis ECDSA v Ghost Vectors aj naša správa o zvyškoch sú podpísané stranou, ktorá mazala, takže ukazujú, že k aktu došlo, ale cudziemu človeku to potvrdiť nedovolia. Pre vektorové úložisko tú vzdialenosť ešte nikto nezavrel.

## Čo s tým robíme my

Overiteľné mazanie je os, na ktorej je postavená naša vlastná knižnica. `inspeximus` pri `forget()` obsah odstráni, pre každé mazanie zapíše hash-reťazený tombstone bez obsahu a vráti správu o zvyškoch: koľko záznamov prešlo, aké hodnoty sa hľadali, čo sa našlo, a výhradu vyššie, že porovnanie podreťazcov chytí uloženú hodnotu a minie parafrázu. Nástroj tlačí vlastné limity vo vlastnom výstupe.

Spusti si kontrolu najprv na vlastnom stacku. Čistý výsledok ťa stojí minútu a povie ti niečo, čo si nevedel.

## Susedia a predchodcovia

Na tú istú otázku stavali nástroje aj iní a zaslúžia si kredit. `vector-forget` (PyPI, júl 2026) tvrdo maže a overuje vymazanie v pgvectore. `forgetlayer` (PyPI, júl 2026) kaskádovo maže záznam cez surové záznamy, embeddingy a súhrny a pri mem0 hlási, že text pamäte prežije v tabuľke histórie SQLite. MemoryProof (GitHub, august 2026) vkladá kanárikov s cieľovým a kontrolným subjektom a dodáva adaptér na nadmerné mazanie. Tombstone (GitHub, september 2026) sleduje subjekt naprieč RAG stackom a hlási logický pass vedľa fyzického fail. Sebastian Mondragon v [príspevku zo 6. augusta 2026](https://particula.tech/blog/vector-database-gdpr-erasure-hnsw-soft-delete) prešiel engine po engine to isté odkladanie so skriptmi na uvoľnenie miesta. Čo tento súbor pridáva, je riadok instrument, päť stackov v jednom skripte a nameraná séria prahov Chromy.

## FAQ

**Maže mazanie z vektorovej databázy naozaj dáta?**
Nie okamžite, zámerne. Server Qdrantu čaká, kým segment drží 20 % zmazaných vektorov a aspoň 1 000 vektorov. Chromin log drží text, kým sa HNSW segment neuloží, predvolene po 1 000 operáciách; namerali sme 1 020 výplňových zápisov. pgvector vynuluje vektor pri vacuume a PostgreSQL vacuumuje po viac než 50 plus 20 % tabuľky v mŕtvych záznamoch. Volanie delete vráti úspech na začiatku toho oneskorenia.

**Ako overím mazanie v pamäti svojho agenta?**
Zapíš dve známe značky, jednu zmaž cez vlastné API backendu, spusti jeho vlastnú kompakciu, potom prečítaj surové súbory úložiska a hľadaj obe. Zmazaná musí chýbať a druhá musí stále byť. Ak sú bajty zmazanej značky stále prítomné, mazanie ich z disku ešte neodstránilo.

**Sú embeddingy osobné údaje podľa GDPR?**
Závisí to od toho, či sa embedding dá spätne spojiť s osobou, a Ghost Vectors hlási, že na soft-zmazaných vektoroch je to spojenie prakticky schodné. Právnu otázku rozhodne tvoj DPO. Kontrola vyrieši tú predchádzajúcu: či vektor a jeho text sú stále na disku.

**Stačí soft delete na právo na vymazanie?**
Soft delete skryje záznam pred dopytmi a nechá ho v úložisku. Či to spĺňa článok 17, je otázka pre tvojho DPO a tvojho regulátora; správa EDPB z roku 2026 sa tým nezaoberá. Nevieš to posúdiť, kým nevieš, ktorú z tých dvoch vecí tvoj stack robí. Táto kontrola ti to povie.

*Spustiteľný receipt na všetko vyššie: [`integrity/erasure_selfcheck.py`](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). Je deterministický, beží offline a testuje iba backendy, ktoré už máš nainštalované.*

*Aktualizované 17. septembra 2026: pridaný beh na piatich backendoch, prahy výrobcov s ich zdrojmi, slovník NIST SP 800-88 Rev. 2, správa EDPB, časová os mazania Googlu, článok zo SaTML 2025 a susedné nástroje. Kontrola dostala pozitívnu kontrolu, riadok instrument a odmietnutie verdiktu, keď kompakcia nemôže bežať.*
