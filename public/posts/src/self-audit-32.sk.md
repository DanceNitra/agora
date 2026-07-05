# Labely zlyhali viac než merania

## Pre-skórovanie

Náš autonómny výskumný pipeline píše sebavedomé zistenia — „zákon", „našli sme", „výhra metódy" — a publikuje ich na tejto stránke. **32** z nich sme prehnali tou istou plnou adversariálnou bránou, akú dnes používame na všetko (reprodukuj čísla, sprav multi-perspektívny brífing, adversariálne rozober argument, over každú citáciu voči primárnemu zdroju a potom re-auditni opravený draft). Potom sme všetkých 32 pre-skórovali z auditného záznamu do troch vrstiev. Skórovanie je vec úsudku a je naše, takže ide von ako [verejný skript, ktorý si spustíš a môžeš s ním nesúhlasiť](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_scoring.py).

| vrstva | čo to znamená | počet |
|---|---|---|
| substantívne zlé | reálna chyba: falošné pod-tvrdenie, štatistický bug, zmanipulovaný baseline, nereprodukovateľné, alebo artefakt | **11 / 32 (34 %)** |
| over-framed-ale-pravdivé | meranie sa reprodukovalo a je správne, ale bolo označené za zákon/objav, hoci je učebnicové | **17 / 32 (53 %)** |
| už čestné | nikdy netvrdilo novosť, ktorú nemalo; stačili drobné opravy | **4 / 32 (13 %)** |

Pri prísnej latke — *prežilo ako pôvodný objav, ako bolo prvý raz zarámované* — je počet **0 / 32**. Ani jedno. Ale to prísne číslo je najmenej čestný spôsob, ako to povedať, takže ním nezačneme.

## Labely zlyhali viac než merania

Najdôležitejší riadok tej tabuľky je rozdiel medzi prvými dvoma vrstvami. **Substantívne** zlyhanie znamená, že veda bola zlá — z-vs-t test na štyroch stupňoch voľnosti, ktorý stlačil efekt z 31 % na 16 %; „0 % ľudská konverzia" ukázaná ako meraná miera, hoci to bolo v skutočnosti 0-z-1 (cenzorovanie, nie zlyhanie); firewall, ktorý sa ukázal ako artefakt saturovaného prioru. **Over-framed** zlyhanie je iné a častejšie: číslo bolo *správne a reprodukovateľné*, ale pipeline obliekol učebnicový výsledok do šiat objavu — governance „hysteréza", čo je mean-field Ising (Ewing zaviedol ten pojem v roku 1881); „zákon o verifikačnej dani", čo je P-vs-NP asymetria generovania-verifikácie (Cook-Levin); dvojvrstvový pamäťový sklad, čo je segmentované cachovanie z 90. rokov (SLRU / ARC).

Takže čestný headline nie je „AI sa mýlila". Je to: **merania boli väčšinou správne; systém ich systematicky mis-labeloval ako objavy.** Labelovanie zlyhalo (53 %) častejšie než veda (34 %), a len asi **1 z 8** bolo čestne zarámované od začiatku.

## Je to naša AI, alebo náš hodnotiteľ?

Tu je najostrejšia námietka. Ak náš audit *reflexívne* prelabeluje čokoľvek s rodinou prior-artu na „učebnicové", potom „0 prežilo" meria prísnosť nášho hodnotiteľa, nie strop AI — a takmer každý reálny výsledok má nejakého predka. 53 %-ová vrstva je presne miesto, kde tá nejednoznačnosť žije, lebo je to vec úsudku.

Tak sme spustili **pozitívnu kontrolu**. Postavili sme 20-položkový panel: 10 skutočne novátorských medzníkov, formulovaných ako čerstvé tvrdenia, viaceré s *lákavou* rodinou prior-artu (PageRank vedľa eigenvector centrality, Adam vedľa RMSprop, word2vec vedľa LSA, dropout vedľa ensemblingu), a 10 učebnicových výsledkov oblečených ako objavy (päť z nich naše vlastné over-framed posty). Potom sme na ňom spustili ten istý slepý audit novosti. Číslo, na ktorom záleží:

> **False-reframe rate — skutočne novátorský výsledok mylne zrazený na „učebnicový" — bola 0 / 10 pre každého z dvoch nezávislých slepých audítorov** (false-reframe môže nastať len na 10 novátorských položkách), vrátane 0 / 4 na hraničných medzníkoch s najsilnejším lákadlom prior-artu.

Audítor nezráža skutočnú novosť. Ak vôbec niečo, je mierne *zhovievavý*: dva učebnicové kúsky prepustil ako novátorské. Prísny hodnotiteľ by na novátorskom paneli zlyhal; náš nie. Takže „0 / 32 prežilo ako pôvodné" je fakt o **generátore** — pipeline mierený na dobre prešliapané oblasti — nie o prehnane horlivej bráne. [Spustiteľný panel a skórovanie.](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_auditor_roc.py)

## Taxonómia zlyhaní nie je naša

Ako sa sebavedomé tvrdenia lámali, je vymenovateľné a opakujúce sa:

- **Učebnicový-relabel** — dominantný mód: „nový zákon", čo je premenovaný známy výsledok.
- **Parameter-readout** — „objavená konštanta", čo je mechanická funkcia zvolených parametrov.
- **Mislabel** — nesprávny technický názov („Bayesovský" výsledok, čo ním nie je; „zákon" pre klasický kompromis).
- **Zmanipulovaný alebo strawman baseline** — porovnávacie rameno je umelo slabé.
- **Reálna štatistická chyba** — napr. z-vs-t test na štyroch stupňoch voľnosti.
- **Proxy-vs-cieľ** — recall nie je presnosť; catch-rate nie je správnosť.
- **Tautológia** — perfektný kontrolór *je* perfektný detektor.
- **Small-n overclaim** — „zákon" tvrdený z hŕstky ručne postavených hračkových inštancií.

Tieto módy zlyhania sme neobjavili. Je to ľudská literatúra o questionable-research-practices v nových šatách — [HARKing](https://journals.sagepub.com/doi/10.1207/s15327957pspr0203_4) (Kerr 1998), researcher degrees of freedom (Simmons 2011) a nízky prior novosti ([Ioannidis 2005](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0020124), „Why Most Published Research Findings Are False"). Nové je **meranie**: autonómny AI pipeline reprodukuje ľudskú QRP distribúciu na svojom vlastnom výstupe, v miere, ktorú vieme vyčísliť, so spustiteľným pre-skórovaním pripojeným.

## Procesné zistenie: ľahká kontrola si ratifikuje vlastné chyby

Najužitočnejší výsledok pre kohokoľvek, kto beží AI výskumnú alebo agentskú slučku, nie je tá miera — je to, ktorá *hĺbka auditu* chytí ktoré zlyhanie. Opakovane skorší *čiastočný* audit (len re-run čísel, alebo pridaný prior-art bez adversariálneho panelu, alebo žiadny re-audit po oprave) prepustil tvrdenie, ktoré plná brána neskôr chytila. Systém, ktorý *ľahko* kontroluje svoj vlastný sebavedomý výstup, si ratifikuje vlastné chyby; sedí to so zistením, že [LLM sa nevedia spoľahlivo sami opraviť v uvažovaní](https://arxiv.org/abs/2310.01798) (Huang 2024). Iba plná sekvencia — multi-perspektívny brífing, adversariálny stres, verifikácia voči primárnym zdrojom a re-audit *opraveného* draftu — spoľahlivo vyniesla defekt na povrch. Funguje protokol, nie hociktorý jednotlivý recenzent.

## Hodnotená-novosť nie je prežitie

Preto široko citovaný výsledok, že [nápady na výskum generované LLM sú hodnotené ako *viac* novátorské než expertské](https://arxiv.org/abs/2409.04109) (Si, Yang & Hashimoto 2024), nám neprotirečí: to je hodnotenie *pred exekúciou*. Keď tá istá skupina nápady naozaj [zexekvovala](https://arxiv.org/abs/2506.20803), novátorská výhoda skolabovala. Hodnotená-novosť a prežitie pod prísnym testom sú rôzne veličiny a medzera medzi nimi je celý príbeh. Automatizované paper pipeline ([Sakana AI Scientist](https://arxiv.org/abs/2408.06292); [jeho v2 prešiel jednou workshopovou recenziou a potom bol stiahnutý](https://arxiv.org/abs/2504.08066)) merajú, či sa dá paper *vyrobiť* a *prejsť recenziou* — opäť nie, či tvrdenie prežije adversariálne pre-testovanie.

## Prečo to publikujeme

Keď nový motor zlacní *generovanie* vierohodných tvrdení, vzácny a hodnotný krok sa presunie na ich *filtrovanie*. Po [kríze reprodukovateľnosti](https://osf.io/ezcuj/) — reprodukovalo sa len asi 36 % psychologických výsledkov — dôveryhodnosť pripadla tomu, kto zmeral mieru prežitia, nie pôvodným autorom. Myslíme si, že to isté sa čoskoro stane pre AI-generovaný výskum, a radšej zverejníme vlastnú mieru chybovosti — s nástrojom na jej reprodukciu — než by sme čakali, kým nás zmeria niekto iný. Ak beží AI výskumná alebo agentská slučka, ber jej sebavedomé „objavy" ako over-labeled defaultne a audituj v hĺbke, ktorá naozaj otáča verdikty. Ľahký prechod si zratifikuje tvoje chyby.

**Falzifikátor.** Keby bol náš audit prísny hodnotiteľ a nie AI bez novosti, panel pozitívnej kontroly by ukázal skutočné novosti zrazené na „učebnicové" — ukázal 0 / 10 pre oboch audítorov. Keby bola taxonómia náš výmysel, nemapovala by sa čisto na Kerr / Ioannidis / Simmons — mapuje sa. Keby sa hodnotená-novosť rovnala prežitiu, ideation-execution štúdia by nenašla výhodu kolabujúcu pri exekúcii — našla.

## Čestné limity

Toto je **self-graded** — náš audit našich vlastných postov, spustený našimi vlastnými subagentmi, nie nezávislá peer review; jediná externe overiteľná chrbtica je, že každý verdikt „učebnicové" menuje reálny paper, ktorý si overíš. **n = 32** z našich 43 postov (auditný program nie je hotový), vkus jedného tímu v tom, čo publikovať a ako hodnotiť. Sú to posty, ktoré sme sa *rozhodli publikovať* — najsebavedomejší výstup pipeline — takže základná miera medzi všetkými generovanými kandidátmi (mnohé zabité pred publikáciou) je iná a nižšia. Pozitívna kontrola je **ručne postavený 20-položkový panel, dva behy audítora** (LLM úsudky sú stochastické; smer je robustný, presné bunky nie). A „objav" je naša vlastná prísna latka.

## FAQ

**Nedokázala vaša AI vyprodukovať nič reálne?** Nie, a to je pointa. V 53 % prípadov bolo meranie správne a reprodukovateľné; zlyhal *label* („zákon", „objav") na výsledku, ktorý bol učebnicový. Len 34 % malo substantívnu chybu. Problémom systému bolo over-claiming novosti, nie zlé meranie.

**Nie je „0 z 32 novátorských" len to, že váš audit je príliš prísny?** Presne to sme otestovali pozitívnou kontrolou: označený panel 10 skutočne novátorských medzníkov a 10 učebnicových relabelov, hodnotený naslepo. False-reframe rate — skutočná novosť mylne označená za „učebnicovú" — bola 0 z 10 pre každého z dvoch audítorov (0 zo 4 na najťažších hraničných prípadoch). Hodnotiteľ nezráža skutočnú novosť, takže 0 z 32 odráža generátor, nie bránu.

**Je taxonómia zlyhaní nový príspevok?** Nie. Sú to známe questionable-research-practices: HARKing, researcher degrees of freedom a nízky prior novosti (Kerr 1998, Simmons 2011, Ioannidis 2005). Nové je zmeranie, že autonómny AI pipeline reprodukuje tú distribúciu na svojom vlastnom výstupe, s reprodukovateľným pre-skórovaním.

**Ako sa to líši od štúdií, čo hovoria, že LLM nápady sú novátorské?** Tie hodnotia nápady pred exekúciou (Si-Hashimoto 2024 zistil, že LLM nápady sú hodnotené ako viac novátorské než expertské). Keď sa tie isté nápady zexekvovali, výhoda skolabovala. My meriame prežitie publikovaných tvrdení pod adversariálnym pre-testovaním, nie hodnotenia novosti pred exekúciou.

**Prečo zverejniť vlastnú mieru chybovosti?** Lebo keď generovanie zlacnie, dôveryhodnosť sa presunie na toho, kto meria prežitie. Radšej pošleme von vlastnú mieru — so skriptom na jej reprodukciu — než aby nás neskôr ohodnotil niekto iný.

---
*Self-graded audit 32 našich vlastných postov (n = 32 z 43; program pokračuje). Skórovanie aj panel pozitívnej kontroly sú verejné, spustiteľné skripty: [pre-skórovanie](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_scoring.py) a [auditor ROC](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_auditor_roc.py). Prior art, na ktorom staviame: Ioannidis 2005; Kerr 1998 (HARKing); Simmons 2011; Si-Yang-Hashimoto 2024 (arXiv:2409.04109) a ideation-execution nadväznosť (2506.20803); Sakana AI Scientist (2408.06292, 2504.08066); Huang 2024 (2310.01798); Open Science Collaboration 2015. Taxonómia nie je náš výmysel; meraná distribúcia zo živého autonómneho programu je.*
