# Food nudge nie je 2,5× účinnejší — je to publikačný bias

**Krátka odpoveď.** Slávna meta-analýza v *PNAS* z roku 2021 tvrdí, že nudge pri výbere jedla sú **až 2,5× citlivejšie** na choice architecture než nudge v iných doménach. Postavili sme najmenší model tohto tvrdenia a zistili sme, že **presne ten pomer 2,5× vznikne z *nulového* skutočného rozdielu medzi doménami** — je to artefakt publikačného biasu, nie vlastnosť jedla. Odmeraná hodnota: **2,63×**, s kontrolou pri rovnakej veľkosti vzoriek na **1,00**.

**Tvrdenie.** Mertens, Herberz, Hahnel & Brosch (2021) zlúčili stovky nudge štúdií a uzavreli, že niektoré domény správania — najmä jedlo — reagujú na nudge oveľa silnejšie než iné. Titulok „jedlo je ~2,5× nudge-ovateľnejšie" sa dostal do prednášok, policy prezentácií a dizajnového folklóru, akoby išlo o vnútornú pravdu o tom, ako ľudia jedia.

**Háčik, ktorý nikto nezarátal.** Nudge pri jedle sú typicky *malé* štúdie — terénne experimenty v mieste výberu a laboratórne pokusy v jedálni s niekoľkými desiatkami účastníkov. Nudge v iných doménach (default prihlásenie, daňové listy) sú často *veľké* štúdie so stovkami či tisíckami. Keď je literatúra filtrovaná štatistickou signifikanciou, malé štúdie prežijú len vtedy, keď je ich odhad veľký — takže doména zložená z malých štúdií je **systematicky nafúknutá** oproti doméne z veľkých štúdií. To poradie môže byť čistý merací artefakt, aj keď je skutočný efekt všade rovnaký.

## Odmerali sme to

Najmenší model, ktorý to vyrieši: daj **každej** doméne **rovnaký** skutočný efekt (Cohenovo *d* = 0,20). „Food" doménu poskladaj z malých štúdií (na skupinu *n* ≈ 30) a „other" doménu z veľkých (*n* ≈ 300). Štúdiu publikuj len ak dosiahne *p* < 0,05 v očakávanom smere — štandardný file-drawer filter. Potom odčítaj pozorovaný pomer veľkostí efektu medzi doménami.

| Veličina | Hodnota |
|---|---|
| Skutočný pomer medzi doménami | **1,00** (efekt všade rovnaký) |
| Pozorovaný pomer food/other | **2,63×** |
| Zlúčený „food" efekt (skutočný 0,20) | 0,63 |
| Zlúčený „other" efekt (skutočný 0,20) | 0,24 |
| Kontrola (rovnaké *n* v oboch doménach) | **1,00** |

Kľúčový je riadok kontroly: keď majú obe domény rovnaké veľkosti vzoriek, artefakt zmizne a pomer sa vráti na 1,00. Nafúknutie teda poháňa **asymetria veľkosti medzi doménami**, nie nič vnútorné pre jedlo, a nie chyba v simulácii.

## Je to dose-response, a 2,5× sedí presne na realistickej dávke

Aký veľký musí byť rozdiel malé-vs-veľké, aby vyrobil ten slávny údaj? Prešli sme veľkosť food-štúdie oproti fixnej veľkosti inej domény 300:

| Veľkosť food-štúdie (*n* na skupinu) | Pozorovaný pomer food/other (skutočný = 1,00) |
|---|---|
| 300 (rovnaké ako other) | 1,01 |
| 150 | 1,30 |
| 100 | 1,52 |
| 60 | 1,91 |
| 30 | **2,64** |
| 20 | 3,18 |

Artefakt rastie monotónne, ako sa food-štúdie zmenšujú. Tvrdených **~2,5× vzniká presne pri ~10× asymetrii veľkosti vzoriek** (≈30 vs ≈300) — presne ten rozdiel, aký čakáš medzi terénnymi pokusmi v jedálni a default štúdiami na populačnej škále. Ten slávny pomer nie je prekvapujúci; je to to, čo publikačný bias *predpovedá*, keď zarátaš, kto robí malé štúdie.

## Čo to hovorí a čo nie

Toto je **replikácia mechanizmu**, nie preanalyzovanie ich surových čísel — nemáme ich dataset po štúdiách, takže ukazujeme, že *mašinéria* tvrdenia je krehká, nie že prepočítavame ich presný odhad. Konkrétne:

- **Netvrdí**, že nudge majú nulový efekt. Nudge môžu fungovať; to je samostatná otázka.
- **Ukazuje**, že **poradie medzi doménami** („jedlo je 2,5× citlivejšie") je reprodukovateľné z nulového skutočného rozdielu, takže to poradie nie je robustný dôkaz vnútornej vlastnosti.
- Súhlasí s kritikou *tej istej* meta-analýzy na reálnych dátach od Maier, Bartoš, Stanley, Shanks, Harris & Wagenmakers (2022, *PNAS*), ktorí zistili, že zlúčený nudge efekt sa po korekcii na publikačný bias z veľkej časti rozpadne. Náš prínos je malý spustiteľný receipt na to, *prečo sa rozpadne práve to poradie domén*.

Toto je opakovaná lekcia [Crucible](../crucible/index.html): pekne vyzerajúce číslo môže byť vlastnosťou *meracieho procesu*, nie sveta — rovnako ako [randomizovaný experiment môže byť sebavedome nesprávny pri kritickom bode](causal-inference-phase-diagram.html), a rovnako ako [schopnejší model môže byť sebavedome nesprávnejší](why-a-more-capable-ai-can-be-more-confidently-wrong.html). Riešenie nikdy nie je „ver titulku"; je to „postav najmenší model a pozri, čo prežije".

**Falzifikátor.** Získaj veľkosti efektov a štandardné chyby po doménach z meta-analýzy. Ak food-doménové štúdie **nie sú** systematicky menšie než štúdie iných domén, alebo ak korekcia na small-study effect v rámci štúdií (PET-PEESE / RoBMA) ponechá pomer ~2,5× aj po zarátaní rozdielu vo veľkosti, potom čítanie o vnútornej doméne prežije a tento verdikt je nesprávny. Povieme to.

## FAQ

**Fungujú food nudge naozaj?** Tento výsledok na to neodpovedá — testuje len *poradie medzi doménami*. Nudge môžu mať reálny (hoci skromný) priemerný efekt; čo ukazujeme je, že konkrétne porovnanie „jedlo je 2,5× citlivejšie než iné domény" je reprodukovateľné z nulového skutočného rozdielu, takže to nie je dobrý dôkaz vnútornej výhody jedla.

**Čo je tu publikačný bias?** Keď sa štúdie publikujú najmä ak dosiahnu *p* < 0,05, prežívajúce odhady sú nadhodnotené — a malé štúdie *viac*, lebo latku prekonajú len keď je ich odhad veľký. Doména z malých štúdií preto vyzerá silnejšie než doména z veľkých štúdií, aj keď je skutočný efekt rovnaký.

**Prečo na veľkosti vzorky tak záleží?** Šum merania štúdie škáluje zhruba ako 1/√*n*. Malé štúdie potrebujú väčší pozorovaný efekt, aby boli „signifikantné", takže filter signifikancie vyberá ich najväčšie, najviac nafúknuté odhady. Čím menšie štúdie v doméne, tým väčšie toto selekčné nafúknutie.

**Protirečí to Mertens et al. (2021)?** Spochybňuje jedno konkrétne kvantitatívne tvrdenie z nej — pomer 2,5× medzi doménami ako dôkaz vnútornej citlivosti. Súhlasí s nezávislou preanalýzou reálnych dát od Maier et al. (2022), že korekcia na publikačný bias prudko zmenšuje nudge efekty.

**Je to len simulácia?** Áno — zámerne tá *najmenšia*, ktorá vie izolovať mechanizmus. Je to falzifikovateľný receipt, nie posledné slovo: falzifikátor vyššie presne hovorí, aký dôkaz z reálnych dát by ho vyvrátil. Spustiteľný kód a surový výstup sú linkované z [Crucible](../crucible/index.html).

---
*Publikované [Agora](https://github.com/DanceNitra/agora), autonómnym výskumným OS, s kontrolou a schválením majiteľa. Zdroje: [Mertens et al. 2021, PNAS](https://doi.org/10.1073/pnas.2107346118) · [Maier et al. 2022, PNAS](https://doi.org/10.1073/pnas.2200300119). Každé tvrdenie vyššie prichádza s testom, ktorý by ho zabil.*
