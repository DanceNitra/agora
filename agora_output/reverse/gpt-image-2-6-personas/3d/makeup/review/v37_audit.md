AUDITOR: independent subagent

# Audit v37: obočie vľavo na obrázku proti červenej kresbe majiteľa

Celkový verdikt: v37 NESPĹŇA kresbu. Začiatok pri nose sedí a chvost klesá o niečo viac ako vo v32. Obočie je však stále rovnako hrubé a vysoké ako vo v32. Chvost klesá asi o polovicu menej, ako je nakreslené. Zmena je malá, nie tvar z kresby.

Mierka: pixely sú v mierke pásu 1 a 3 (v32, v37). Pás 2 so screenshotom je zmenšený asi 0,84×, preto sú jeho rozmery prepočítané. Všetky hodnoty sú odhadnuté od oka z obrázka, nie zmerané skriptom.

## Porovnanie po častiach (obočie vľavo na obrázku)

| Časť | Kresba (červená) | v37 | Verdikt |
|---|---|---|---|
| Začiatok pri nose | Končí tesne pri pôvodnom vnútornom konci obočia vo v32 | Vnútorný koniec je na rovnakom mieste ako vo v32 (x asi 490, rovnaká výška ±5 px) | MATCH |
| Najvyšší bod: výška | Horná hrana kresby je asi 25 až 30 px POD hornou hranou v32 | Vrchol je v rovnakej výške ako vo v32 (±5 px), oblúk nie je znížený | WRONG: asi 25 px príliš vysoko |
| Najvyšší bod: poloha po dĺžke | Asi 65 % dĺžky od vnútorného konca | Asi 70 % od vnútorného konca | CLOSE: asi 10 až 15 px smerom k spánku |
| Chvost: smer | Za vrcholom výrazne ohnutý nadol, háčik k spánku | Klesá nadol, ale miernym sklonom, bez háčika | CLOSE až WRONG |
| Chvost: o koľko nadol | Od vrcholu klesá asi o 40 px (prepočítané) | Od vrcholu klesá asi o 30 až 35 px, vo v32 asi o 20 px | CLOSE: chýba asi 10 až 15 px poklesu. Koniec chvosta je navyše asi 15 až 20 px kratší smerom k spánku ako na kresbe |
| Chvost: zúženie | Zužuje sa do tenkého hrotu | Zužuje sa len mierne, koniec je široký a strapatý | WRONG |
| Hrúbka | Asi 15 až 20 px v celej dĺžke | Asi 35 až 45 px v tele obočia, rovnako ako vo v32 | WRONG: asi 2× hrubšie |
| Celkový uhol | Plochý oblúk s nízkym vrcholom a strmo klesajúcim chvostom | Vysoký oblúk ako vo v32 s mierne nižším chvostom | WRONG |

Poznámka k "ohyb je už zrkadlený": kresba je nakreslená priamo na obočí vľavo na obrázku a v37 upravuje to isté obočie. Smer ohybu je správny, nie je prevrátený. Chyba je vo veľkosti zmeny, nie v strane.

## Obočie vpravo na obrázku

Proti v32 nevidím zmenu. Vnútorný koniec, vrchol, chvost, hrúbka aj fialový nádych pri chvoste sú rovnaké v rámci ±5 px. Verdikt: NEZMENENÉ.

## Chyby v páse s pohybom (v37_motion.png)

1. Snímka 3 (zatvorené oči): v ľavom oku na obrázku je pri vonkajšom kútiku tmavá sivomodrá škvrna. Linka alebo krídlo sa pri žmurknutí mení na fľak. Pravé oko na obrázku túto chybu nemá.
2. Snímka 3: mihalnice zatvoreného ľavého oka na obrázku trčia neporiadne dole a do strán. Pravé oko na obrázku je čistejšie.
3. Obočie počas žmurknutia drží tvar a nikam neskáče. Jeho tvar má však tú istú chybu ako statický záber: je hrubé a vysoké.

## Referencia (depesa_p6.png)

Obočie na referencii je nízke, ploché, tesne nad okom, a chvost klesá k spánku. Kresba majiteľa smeruje k tomuto tvaru. v37 ostáva bližšie k vysokému hrubému oblúku z v32.

## Čo treba opraviť

1. Znížiť hornú hranu oblúka asi o 25 px.
2. Hrúbku stenčiť asi na polovicu.
3. Chvost ohnúť nadol o ďalších 10 až 15 px, predĺžiť ho k spánku o 15 až 20 px a zúžiť do hrotu.
4. Vnútorný začiatok nechať, kde je.
5. Opraviť škvrnu na viečku ľavého oka na obrázku pri žmurknutí.
