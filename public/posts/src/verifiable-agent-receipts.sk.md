# Overiteľné účtenky pre AI agentov: vaše logy nie sú dôkaz

**Krátka verzia.** Logy AI agenta sú *self-reported tvrdenia* — agent ich vie prepísať dodatočne, alebo zalogovať volanie nástroja, ktoré sa nikdy nestalo. **Overiteľná účtenka (receipt)** je opak: nezávislý kryptografický dôkaz o tom, čo akcia spotrebovala a vyprodukovala, ktorý si vie hocikto skontrolovať **bez dôvery v agenta**. Postavili sme najmenšiu spustiteľnú verziu a potom ju vzali tam, kde nám dáva najväčší zmysel — do **pamäte agenta**: účtenky robia históriu zápisov do pamäte *tamper-evident*, takže out-of-band úprava toho, čo si agent „pamätá", sa odhalí. Nižšie: ako to funguje, kde je to podľa nás najužitočnejšie, čestné limity, a kto to stavia reálne.

## Prečo log agenta nie je dôkaz

Keď AI agent volá nástroj cez [MCP](https://modelcontextprotocol.io/) — databázu, web search, platbu — aký máš dôkaz, čo sa naozaj stalo? Zvyčajne riadok logu, ktorý si agent napísal sám. To je tvrdenie, nie dôkaz: agent (alebo kompromitovaný proxy uprostred) vie log dodatočne upraviť, vypustiť nepríjemný záznam, alebo sebavedomo vypísať *„zavolal som API a vrátilo X"* pre volanie, ktoré nikdy neurobil. Pri [systéme, ktorý je najsebavedomejší práve keď je najmenej ukotvený](https://dancenitra.github.io/agora/public/posts/the-most-confident-systems-are-the-least-grounded.html), je self-reported log najslabší možný audit.

## Čo je účtenka — a ako sa líši od logu

Účtenka sa v momente akcie zaviaže k **SHA-256 hashu vstupov a výstupu**, plus meno nástroja, časová pečiatka a odkaz na predošlú účtenku. Plynú z toho dve vlastnosti:

- **Dokážeš *čo* sa spracovalo bez odhalenia obsahu.** Účtenka nesie hashe, nie surový obsah; hodnotu odhalíš neskôr len ak chceš, a hocikto si ju vie overiť oproti zaviazanému hashu.
- **Vie ju overiť tretia strana.** S podpisom (nižšie) ten, kto má len verejný kľúč, potvrdí, že účtenka je pravá — žiadne zdieľané tajomstvo, žiadna dôvera v úložisko agenta.

## Dve vrstvy: hash-reťazec, potom podpis

1. **Hash-reťazec — integrita.** Pole `prev` každej účtenky je hash tej predošlej, čím vzniká reťazec. Uprav *hocijakú* minulú účtenku a hashe po nej sa zlomia, takže *čiastočná* úprava je odhaliteľná a vieš pomenovať krok, ktorý sa zmenil — bez kryptografickej knižnice. (Čestný limit: samotný reťazec nezastaví dôkladného útočníka, ktorý prepočíta celý reťazec end-to-end; na to je podpis — alebo ukotvenie hlavy externe.)
2. **Ed25519 podpis — pravosť.** Hash každej účtenky je podpísaný súkromným kľúčom aktéra; overovatelia ho skontrolujú verejným kľúčom. To dokazuje *kto* účtenku vytvoril a že nič nebolo sfalšované. Plné zero-knowledge dôkazy (ZK-SNARK) idú ďalej — dokážu, že výpočet bol správny bez odhalenia čohokoľvek — a sú ťažký koniec toho istého priestoru.

## Postavili sme najmenšiu spustiteľnú verziu — a odmerali ju

[`agent-receipts`](https://github.com/DanceNitra/agora/tree/main/agent-receipts) je jeden čitateľný súbor. Jeho self-demo zaznamená tri MCP volania nástrojov, potom zaútočí na záznam. Výsledky, spustené tak ako sú publikované:

| krok | čo sme spravili | výsledok `verify()` |
|---|---|---|
| 1 | čestný reťazec účteniek | **True** |
| 2 | upravili sme výstup minulej účtenky | **chytené** — *content tampered* na presnom kroku |
| 3 | pre-hashli sme falzifikát, aby vyzeral konzistentne | **stále chytené** — *invalid signature* (podpis spravil pravý kľúč nad pôvodným hashom) + zlomený článok reťazca nižšie |

Self-reported log zlyhá vo všetkých troch ticho: upravený od začiatku do konca vyzerá potom identicky. Tá medzera — *odhaliteľná manipulácia a pravosť overiteľná treťou stranou* — je celá pointa.

Pre MCP konkrétne nemeníš nástroje: obalíš dispatch. `ReceiptedDispatcher` zaznamená jednu podpísanú účtenku na každé volanie nástroja, takže potom hocikto potvrdí presne ktoré nástroje bežali, s akými hashmi argumentov a výsledkov, v akom poradí.

## Náš uhol: tamper-evident pamäť

Účtenky sú najzaujímavejšie tam, kde už pracujeme — v **pamäti agenta**. Naše open-source pamäťové jadro [inspeximus](https://github.com/DanceNitra/inspeximus) je už append-only, ale úložisko je stále súbor: ktokoľvek sa k nemu dostane, vie uloženú pamäť dodatočne prepísať — a agent by potom recalloval zmenený text ako pôvodný. Zapojenie účteniek to mení — každý `remember()` emituje podpísanú účtenku zaviazanú k hashu obsahu pamäte, takže *história zápisov* je nezávisle overiteľná.

Odmerané: čestné úložisko prejde auditom čisto; out-of-band úprava (`db-prod-01 → db-attacker-07`, spravená priamo v úložisku) je chytená a pomenovaná podľa memory id. To je **tamper-evident pamäť** — vlastnosť, ktorú širší landscape väčšinou aplikuje na volania nástrojov, nie na samotnú pamäťovú vrstvu. To je tá časť, ktorú chceme ďalej stavať.

## Čestné limity

Toto je referenčný proof-of-concept a čestný rozsah je dôležitejší než demo:

- Dokazuje, že reťazec účteniek je **vnútorne konzistentný a pravo podpísaný** — **nedokazuje**, že agent nahlásil *každú* akciu. Aktér, ktorý drží vlastný kľúč, vie účtenku zatajiť. Toto zatvorí až **externý mediátor/proxy**, ktorý podpisuje zvonku agenta.
- Zaväzuje sa k **hashom** vstupov/výstupov, nie k dôkazu, že nástroj *počítal správne*. To pridávajú zero-knowledge prístupy, za oveľa vyššiu cenu.
- **Nie je to novátorské.** Presne ten istý vzor — Ed25519 nad kanonickým JSON, hash-chained — je production-grade náplňou Microsoft [agent-governance-toolkit, Tutorial 33](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/tutorials/33-offline-verifiable-receipts.md). Ber tú našu ako jednosúborový spôsob *pochopiť* myšlienku a ten toolkit ako dospelú verziu.

## Krajina — kto to stavia

- **Protokol „Agent Receipts"** od Otta Jongeriusa — verejný spec ([github.com/agent-receipts/ar](https://github.com/agent-receipts/ar)) a udržiavané Python SDK (`pip install agent-receipts`). Najpriamejšie príbuzný projekt; ak chceš interoperabilný štandard a nie minimálnu referenciu, začni tam. (Naše ide na PyPI ako `agora-agent-receipts`, aby nedošlo ku kolízii mien.)
- **Microsoft `agent-governance-toolkit`** — production open source; offline-overiteľné Ed25519 + kanonické + hash-chained účtenky s politikou a identitou okolo nich.
- **[`pipelock`](https://github.com/luckyPipewrench/pipelock)** — open-source MCP/egress firewall, ktorý emituje *mediátorom-podpísané* účtenky zvonku agenta (zatvára medzeru so zatajením).
- **[Zero Proof AI](https://zeroproofai.com)** — komerčná „certificate authority for AI agents", on-chain-ukotvené účtenky (pred spustením).
- **Výskum:** Basu, *Tool Receipts, Not Zero-Knowledge Proofs* ([arXiv:2603.10060](https://arxiv.org/abs/2603.10060), HMAC účtenky); Figuera, *Notarized Agents* ([arXiv:2606.04193](https://arxiv.org/abs/2606.04193), receiver-attested účtenky + transparency log); Jing & Qi, *Zero-Knowledge Audit for Internet of Agents with MCP* ([arXiv:2512.14737](https://arxiv.org/abs/2512.14737)).

## FAQ

**Čo je overiteľná účtenka pre AI agenta?** Kryptografický dôkaz — zaväzujúci sa k hashom vstupu/výstupu akcie, hash-chained a podpísaný — ktorý umožní tretej strane potvrdiť, čo volanie nástroja agenta naozaj urobilo, bez dôvery v jeho vlastné logy.

**Ako sa účtenka líši od logu?** Log je self-reported a upraviteľný; účtenka je tamper-evident (hash-reťazec) a pravá (podpis), takže jej dodatočná zmena je odhaliteľná hocikým s verejným kľúčom.

**Potrebujú overiteľné účtenky agentov blockchain?** Nie. Hash-reťazec plus Ed25519 podpis dávajú tamper-evidence a overenie treťou stranou samy o sebe. Ukotvenie hlavy reťazca on-chain (ako robia niektoré produkty) je voliteľný extra, nie požiadavka.

**Funguje to s MCP volaniami nástrojov?** Áno — obalíš dispatch nástrojov, aby každé volanie emitovalo účtenku. Vstupné argumenty a výsledok sú zaviazané hashom, volanie je podpísané a reťazec ich zoradí.

**Dá sa to naozaj spustiť?** Áno — je to jeden súbor; hash-reťazec funguje bez závislostí, podpisy potrebujú balík `cryptography`.

**Čestný pohľad.** Ak ti obyčajný podpísaný log už dáva všetko, čo potrebuješ, účtenky sú overkill — ich konkrétna hodnota je *treťou stranou overiteľná tamper-evidence bez dôvery v agenta*. V deň, keď sa logy agenta stanú nosné pre billing, compliance alebo bezpečnosť, tá medzera prestane byť akademická.
