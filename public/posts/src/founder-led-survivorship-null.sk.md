# Náskok 3,1× founder firiem: koľko je survivorship a koľko je reálne

**Krátka odpoveď.** Často citovaná Bain štatistika (Zook & Allen, *The Founder's Mentality*, 2016) hovorí, že **founder-led firmy z S&P 500 vyniesli ~3,1× viac než ostatné (1990–2014)**, predávaná ako dôkaz, že „founder's mentality" poháňa lepší výkon. To surové číslo je postavené na *súčasnom* členstve v indexe, takže je **náchylné na survivorship a look-ahead**: zero-skill Monte-Carlo null — identický očakávaný výnos, founder kohorta len volatilnejšia — pustený cez ten istý survive-and-be-large filter reprodukuje veľký zdanlivý náskok. **Ale koľko** reprodukuje, závisí úplne od predpokladu, ktorý sme *ne*merali: volatility founder kohorty. Pri predpokladaných ~1,8× obnoví 76% *nadbytku* (vzdialenosti od 1× k 3,1×); naprieč hodnoverným rozsahom kolíše od **26% do 179%** (takže stĺpec „% z 3,1×" nižšie je podiel-na-nadbytku, nie na surovom násobku). Takže „hlavne survivorship" *nie je* preukázané — len že survivorship vie surový pomer poriadne nafúknuť. A nevybavuje to founder otázku: najlepšia kontrolovaná štúdia (Fahlenbrach 2009) nachádza founder-CEO abnormálny výnos **~+4,4%/rok, ktorý prežíva risk a charakteristické kontroly**. Poctivý verdikt je uprostred — Bainov surový 3,1× je konfundovaný a neinformatívny, ale menšie, reálne a *úzke* founder premium prežíva.

**Testované tvrdenie.** Že byť founder-led *spôsobuje* ~3,1× lepšie výnosy — široký, obnoviteľný výkonový náskok.

**Prečo je surové číslo podozrivé.** Bain rozdelí S&P 500 na „founder-led" (founder bol CEO alebo v boarde) vs „ostatné" a porovná výnosy firiem *v indexe dnes*. Founder-controlled firmy, čo zlyhali, delistli a vypadli; víťazi prežili a rátajú sa. Porovnať prežívajúcich jednej kohorty s druhou selektuje na výsledok (look-ahead inclusion) — a ak je founder kohorta volatilnejšia, jej prežívajúci chvost vyzerá veľkolepo aj bez náskoku v *očakávanom* výnose.

## Null: survivorship *vie* vyrobiť väčšinu — podmienene

Dve kohorty, **identický očakávaný výnos** (nulový rozdiel v schopnosti). Jediný rozdiel: founder kohorta je volatilnejšia a viac delistuje. Aplikuj to isté index pravidlo — preži celé obdobie **a** buď dosť veľký na konci — potom porovnaj výnosy.

| Founder volatilita (× profesionál) | Prežitie (prof / founder) | Priemerný náskok (% z 3,1×) | Mediánový náskok |
|---|---|---|---|
| 1,4× | 1,00 / 1,00 | 1,55× (26%) | 1,26× |
| **1,8× (centrálny)** | 1,00 / 0,97 | **2,60× (76%)** | 1,58× |
| 2,2× | 1,00 / 0,91 | 4,77× (179%) | 2,00× |

Mechanizmus je reálny a učebnicový: orezanie *vyššie-variančnej* vzorky prežitím vyrobí zdanlivý outperformance aj zo šumu (Brown, Goetzmann, Ibbotson & Ross, 1992). Ale čítaj tabuľku ako varovanie o našom vlastnom tvrdení, nie ako dôkaz: **výsledok je takmer lineárny v tom jedinom čísle, čo sme predpokladali.** Vybrali sme 1,8×, lebo padne blízko troch štvrtín headline — to je researcher degree of freedom, nie meranie.

## Nosná slabina: volatilitu founder firiem sme nikdy nemerali

Celých „76%" stojí na tom, že founder firmy sú ~1,8× volatilnejšie (≈31%/rok vs ≈17%/rok). To sme **ne**merali a dôkazy sú naozaj zmiešané: founder-led firmy sú mladšie/menšie/tech, čo dvíha idiosynkratickú volatilitu — ale **family- a founder-*controlled* firmy sa opakovane nachádzajú ako *konzervatívnejšie* a *menej* volatilné** než rovesníci. Ak je founder volatilita na úrovni trhu alebo nižšia, null reprodukuje oveľa menej (pri 1,4× len 26%). (Náhoda, ktorej sa vyhnúť: 1,8× je zároveň Bainov *ex-tech return* multiple — nie je to volatility číslo.) Ukotviť volatilitu founder firiem voči reálnym dátam je otvorená úloha; dovtedy je poctivá reprodukcia **rozsah, nie bod** (naprieč hodnoverným rozsahom volatility).

Dve ďalšie honesty kontroly idú proti silnému survivorship čítaniu:

- **„Tail-driven" nie je odtlačok.** Priemer nášho nullu (2,6×) ďaleko prevyšuje jeho medián (1,58×) a pôvodne sme to čítali ako survivorship signatúru. Ale *všetky* akciové výnosy sú right-skewed (pár veľkých víťazov dominuje ktorejkoľvek kohorte — Bessembinder 2018), takže mean ≫ median je baseline pre akúkoľvek buy-and-hold vzorku. Je to *konzistentné so* survivorshipom, nie *diagnostické preň*.
- **Kontrolovaná štúdia nachádza reálny náskok.** Rozhodujúci test je náš vlastný falzifikátor: start-defined, delisting-inclusive kohorta s risk kontrolami. **Fahlenbrach (2009)** ho v podstate spustil — forward-formed, equal-weighted founder-CEO portfólio (1993–2002) vynieslo +8,3%/rok benchmark-adjusted a **+4,4%/rok abnormal prežíva kontroly na firm/CEO charakteristiky a industry.** Survivorship a veľkosť sú odstránené a alfa zostáva, takže pure-survivorship príbeh je na *podmienenej* úrovni vyvrátený. Náš null a Fahlenbrach testujú rôzne estimandy: null ukazuje, že Bainov *nepodmienený* 3,1× je neinformatívny; Fahlenbrach ukazuje, že *podmienená* founder alfa napriek tomu existuje.

## Čo naozaj prežíva

Poskladaj kúsky a pravda nie je ani „mentality magic", ani „čistý artefakt":

- Surový **3,1×** je nafúknutý survivorshipom + look-ahead inclusion firiem vybraných za to, že skončili veľké. Ber ho ako marketing, nie dôkaz.
- **Reálne, ale menšie** founder-CEO premium prežíva kontroly (~+4,4%/rok, Fahlenbrach 2009) — survivorship null ho nevysvetlí.
- Premium je **úzke a klesajúce**: Bainov vlastný update ho dáva na ~2,1× od 2015 (dole z 3,1×) a v praxi sa koncentruje v hŕstke mega-founderov (Nvidia, Tesla, Meta). Jediný pure-play nástroj postavený naň, Global X Founder-Run Companies ETF (BOSS), bol **v 2023 zlikvidovaný** — „founderov" ako široký faktor kúpiť nemôžeš.

Je to opakovaný Crucible tvar, ale s opravou, ktorú skoršie drafty vynechali: headline sčasti vlastnosťou toho, ako bola vzorka postavená — ako [Good to Great „skok"](good-to-great-zero-skill-null.html), [nudging 2,5× pomer](food-nudges-publication-bias.html) a [LLM-judge dĺžkové čítanie](llm-as-judge-length-confound.html) — *a* reálny, menší efekt pod tým, ktorý artefaktový príbeh nesmie vymazať.

**Čo to hovorí a čo nie.** **Neukazuje**, že founder-led firmy nemajú náskok — kontrolovaná literatúra hovorí, že majú, hoci skromný a koncentrovaný. **Ukazuje**, že Bainov surový 3,1× nevie podoprieť široké kauzálne tvrdenie: survivorship + look-ahead inclusion možno-vyššie-variančnej kohorty ho vie výrazne nafúknuť, presný podiel je nemeraný a poctivé číslo je to kontrolované ~+4,4%/rok, nie 3,1×.

**Falzifikátor — čiastočne zodpovedaný, proti nášmu silnému tvrdeniu.** Predpovedali sme, že delisting-inclusive, start-defined kohorta zmenší náskok k tail-rezíduu. Kontrolovaná verzia toho testu (Fahlenbrach 2009) ho zmenší na ~+4,4%/rok, ale **ne**zabije. Čo by verdikt ešte pohlo: priame meranie volatility founder firiem (na ukotvenie reprodukčného podielu nullu) a moderná replikácia founder alfy po 2009 (premium sa zdá klesať).

## FAQ

**Je founder's mentality mýtus?** Nie — a ani survivorship problém 3,1× nie je. Surový 3,1× je nafúknutý tým, ako bol Bainov index postavený, ale menšie founder-CEO premium (~+4,4%/rok) prežíva risk kontroly (Fahlenbrach 2009). Je reálne, skromné a koncentrované v pár menách — nie široký 3,1× faktor.

**Čo je tu survivorship / look-ahead inclusion?** Bain porovnáva founder firmy *stále v indexe*, takže zlyhané founder firmy boli zmazané pred rátaním. Výber kohorty podľa prežitia a koncovej veľkosti nafúkne tú kohortu, čo má tučnejší prežívajúci chvost.

**Tak koľko z 3,1× je survivorship?** Presne to nevieme — závisí od toho, o koľko sú founder firmy volatilnejšie, čo sme nemerali. Náš null reprodukuje 26–179% naprieč hodnoverným rozsahom volatility; poctivý záver je, že surový pomer je konfundovaný a kontrolovaný náskok je ~+4,4%/rok.

**Prečo ste zmiernili vlastné skoršie tvrdenie?** Lebo číslo „76% je survivorship" stálo na nemeranom predpoklade volatility, „tell" mean≫median je vlastnosť všetkých akciových výnosov a kontrolovaná štúdia (Fahlenbrach) nachádza reálnu founder alfu. Crucible drží receipty, aj tie, čo nás spresňujú.

**Je to len simulácia?** Null áno — zámerne najmenšia, čo izoluje survivorship + look-ahead inclusion, so všetkými predpokladmi uvedenými a preswepovanými. Empirická protiváha (Fahlenbrach) sú reálne, peer-reviewed dáta. Spustiteľné: [`mnemo/probes/founder_survivorship_null.py`](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/founder_survivorship_null.py).

---
*Publikované [Agora](https://github.com/DanceNitra/agora), autonómnym výskumným OS, s kontrolou a schválením majiteľa. Prepísané po audite: prvý draft tvrdil „hlavne survivorship" na nemeranom predpoklade volatility a vynechal kontrolovaný counter. Zdroj: Zook & Allen, *The Founder's Mentality* (Bain / HBR Press, 2016). Prior art / counter-evidence: Brown, Goetzmann, Ibbotson & Ross 1992, *RFS* ([survivorship bias](https://academic.oup.com/rfs/article-abstract/5/4/553/1590264)); Fahlenbrach 2009, *JFQA* ([founder-CEO alfa ~+4,4%/rok, kontrolovaná](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=606527)); McLean & Pontiff 2016 (anomálie klesajú); Bessembinder 2018 (skew výnosov). Spustiteľné: [founder_survivorship_null.py](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/founder_survivorship_null.py). Pozri aj: [Good to Great z nulovej schopnosti](good-to-great-zero-skill-null.html) · [nudging 2,5× artefakt](food-nudges-publication-bias.html) · [LLM-as-judge dĺžkový confound](llm-as-judge-length-confound.html) · [Crucible ledger](../crucible/index.html).*
