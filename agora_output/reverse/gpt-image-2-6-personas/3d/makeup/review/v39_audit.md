AUDITOR: independent subagent

# v39: audit obočia vľavo na obrázku proti červenej kresbe

Výsledok: v39 je od v32 len málo odlišná a kresbu nesplna. Výška oblúka sedí. Chvost klesá menej, ako ukazuje kresba. Vrchol leží bližšie k spánku. Obočie je hrubšie ako obočie vpravo na obrázku. Toto nie je MATCH.

Metóda: odčítané oko z dvoch obrázkov, bez skriptu. Pásik so skicou je menší, preto som ho prepočítal na mierku v32/v39 (faktor asi 1,21, podľa koncov obočia v32 na oboch pásikoch). Odchýlky v pixeloch majú presnosť asi ±10 px. Referenčný portrét depesa_p6.png som neotvoril, lebo rozpočet volaní na to nestačil.

## Časť po časti (súradnice v mierke pásika v32/v39, y relatívne k hornej hrane pásika)

| časť | kresba (prepočítané) | v39 | verdikt |
|---|---|---|---|
| Začiatok pri nose | kresba končí asi na x 441, ale vlastník chce začiatok tam, kde bol (v32: x asi 490, spodná hrana y asi 195-200) | x asi 490, spodná hrana y asi 175-183 | CLOSE: x sedí, vnútorný začiatok sa zdá vyšší o asi 10-15 px. Treba zmerať, môže ísť o chybu odčítania. |
| Vrchol, výška | horná hrana y asi 92 | horná hrana y asi 93-96 (v32 asi 65-70) | MATCH: v39 je pri vrchole nižšie ako v32 o asi 25 px, ako vlastník nakreslil. |
| Vrchol, poloha po dĺžke | x asi 250-300, teda asi 55-65 % od nosa | x asi 220-260, teda asi 65-75 % od nosa | CLOSE až WRONG: vrchol je posunutý k spánku o asi 30-40 px. |
| Vrchol, ostrosť | zaoblený, mierny | zaoblený | MATCH |
| Chvost, smer | za vrcholom klesá nadol k spánku | klesá nadol, ale mierne | CLOSE |
| Chvost, ako nízko | horná hrana konca y asi 106, spodná asi 142 | koniec asi y 112-130 | WRONG: koniec je vyššie o asi 10-15 px, ohyb nadol je slabší ako na kresbe. |
| Chvost, dĺžka | koniec x asi 127 | koniec x asi 130 (v32 asi 145) | MATCH: predĺžený o asi 15 px. |
| Chvost, zúženie | na kresbe je koniec tupý a pomerne široký (asi 30 px) | zužuje sa do užšieho konca | CLOSE: kresba je tu hrubá skica, vlastníkovo slovo o hrúbke (ako vpravo) má prednosť. |
| Celkový uhol | od nosa hore k vrcholu, potom zreteľne nadol | takmer rovné dlhé obočie s miernym oblúkom, podobné v32 | CLOSE: tvar sa od v32 zmenil len málo, okrem zníženia vrcholu. |

## Zrkadlenie ("ohyb je už zrkadlený")

Obočie vpravo na obrázku má vrchol asi na 80-85 % dĺžky od nosa. Má ostrejší zlom a krátky chvost dlhý asi 55-70 px, ktorý strmo klesá. Obočie vľavo vo v39 má vrchol asi na 65-75 %, mäkký oblúk a chvost dlhý asi 110-130 px s miernym sklonom. Ak má byť ohyb zrkadlový, ľavé obočie sa obrazu vpravo nepodobá: WRONG.

## Hrúbka proti obočiu vpravo na obrázku

- Vľavo vo v39: v strede asi 40-45 px, sýto čierne po celej dĺžke.
- Vpravo vo v39: v strede asi 30-35 px, pri nose redšie a svetlejšie.
- Verdikt: WRONG. Ľavé obočie je hrubšie o asi 8-12 px a tmavšie, hlavne v strednej a vnútornej tretine.

## Obočie vpravo na obrázku: v32 proti v39

Vyzerá nezmenené. Začiatok pri nose (x asi 690), vrchol (x asi 950, y asi 113-115), koniec chvosta (x asi 1020) aj fialový nádych pri vrchole sú rovnaké v rámci presnosti odčítania.

## Pásik s pohybom (v39_motion.png)

1. Snímka 3 (zatvorené oči), oko vľavo na obrázku: na vonkajšom kútiku viečka je čierna škvrna (krídlo linky alebo zhluk mihalníc) asi na x 50-75, y asi 510-520. Na zatvorenom viečku vyzerá ako odtrhnutý fľak. Oko vpravo na obrázku takú škvrnu nemá. Toto je chyba.
2. Snímka 3: linka a mihalnice na ľavom zatvorenom viečku sú výrazne hrubšie a tmavšie ako na pravom, takže viečka pôsobia nesymetricky.
3. Obočia sa pri žmurknutí mierne znížia a vrátia sa späť. Prenikanie ani skok tvaru obočia som nevidel.
4. Snímky 1 a 4 sa zhodujú, otvorené oko sa po žmurknutí vráti bez viditeľnej chyby.

## Čo treba zmeniť, aby obočie sedelo s kresbou

1. Spustiť chvost za vrcholom nižšie o asi 10-15 px, aby ohyb nadol bol zreteľný ako na obočí vpravo (zrkadlovo).
2. Posunúť vrchol k nosu o asi 30-40 px a urobiť zlom trochu ostrejší, podľa zrkadla obočia vpravo.
3. Stenčiť obočie o asi 8-12 px na hrúbku obočia vpravo, pri nose ho zriediť ako vpravo.
4. Overiť pixelovým meraním, či sa vnútorný začiatok neposunul nahor; vlastník chce začiatok presne tam, kde bol.
5. Opraviť čiernu škvrnu na vonkajšom kútiku ľavého zatvoreného viečka.
