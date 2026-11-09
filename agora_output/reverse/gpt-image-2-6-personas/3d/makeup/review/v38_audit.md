AUDITOR: independent subagent

# Audit v38: obočie vľavo na obrázku proti červenej kresbe majiteľa

Verdikt: CLOSE, nie MATCH. Vonkajšia polovica obočia klesla správnym smerom a začiatok pri nose ostal na mieste. Oblúk je však plochá plošina namiesto zreteľného zlomu ako na pravom obočí. Chvost je tupý a nezužuje sa. Pravé obočie je nezmenené. V žmurknutí je jedna chyba: čierny fliačik pri vonkajšom kútiku ľavého oka.

Metóda: odčítanie súradníc od oka z obrázka `review/v38_vs_sketch.png` (pásy v32, kresba, v38), bez výrezov a bez merania skriptom. Všetky čísla sú odhady s presnosťou asi ±10 px. Pozícia zreníc je vo v32 aj v38 rovnaká (y asi 255 v rámci pásu), takže rámovanie je zhodné a pásy sa dajú porovnať priamo. Kresba je v snímke obrazovky zmenšená asi na 0,86 a posunutá. Jej body som prepočítal do súradníc renderu.

## Časť po časti (súradnice v rámci pásu, render 1160 px na šírku)

| časť | v32 | červená kresba (prepočítaná) | v38 | verdikt |
|---|---|---|---|---|
| Začiatok pri nose | x 490, y 195 | končí pri pôvodnom začiatku, asi x 450 až 490 | x 490, y asi 200 | MATCH, posun do 5 px |
| Najvyšší bod, výška | horná hrana y asi 65 pri x 230 | asi o 30 px nižšie než v32 | horná hrana y asi 100 až 105 | CLOSE, v38 je asi o 35 px nižšie, kresba chce asi 30 px, rozdiel asi 5 px nadol |
| Najvyšší bod, poloha po dĺžke | asi x 230, výrazný vrchol | asi x 225, asi 73 % dĺžky od nosa, zrkadlo pravého obočia | plochá plošina od x 220 po x 330, bez zreteľného vrcholu | CLOSE až WRONG: vrchol nie je definovaný, stred plošiny leží asi 50 px bližšie k nosu než v kresbe |
| Chvost, smer | mierne nadol | výrazne nadol a von | nadol a von | MATCH |
| Chvost, ako hlboko | asi 22 px pod vrcholom | spodný okraj asi 40 až 45 px pod vrcholom | asi 40 px pod plošinou | CLOSE |
| Chvost, dĺžka | končí pri x 140 | siaha asi o 25 px ďalej von, asi x 115 | končí asi pri x 125 až 130 | CLOSE, asi o 10 až 15 px kratší |
| Chvost, zúženie | mierne zúžený | kresba je obrys, koniec je zaoblený | tupý, takmer plná hrúbka až po koniec | WRONG voči pravému obočiu, ktoré sa na konci zužuje do hrotu |
| Celkový uhol | stúpa od nosa k vonkajšej tretine, potom krátky pokles | stúpa, zlom vo vonkajšej tretine, potom ohyb nadol | od nosa stúpa, potom dlhá rovná plošina, potom pokles | CLOSE: tvar je skôr oblý oblúk bez zlomu, pravé obočie má ostrý uhol |

## Hrúbka proti pravému obočiu

- Stred obočia: vľavo v38 asi 50 px, vpravo asi 40 až 45 px. CLOSE, ľavé je asi o 5 až 10 px hrubšie.
- Hlava pri nose: vľavo asi 55 px, vpravo asi 45 až 50 px. CLOSE, ľavé je asi o 5 až 10 px hrubšie.
- Chvost: vľavo takmer plná hrúbka, vpravo zúžený do hrotu. WRONG.

## Pravé obočie: v32 proti v38

Nezmenené. Tvar, poloha, fialový nádych pri chvoste a svetlejšia sivá hlava pri nose sa zhodujú v rámci odčítacej presnosti. MATCH.

## Pohybový pás (`review/v38_motion.png`)

1. Žmurknutie (tretí rámik): pri vonkajšom kútiku zatvoreného ľavého oka je čierny fliačik asi 25 × 15 px. Vyzerá ako krídlo očnej linky, ktoré vyčnieva z viečka. Pravé oko ho nemá. Chyba.
2. Vo všetkých rámikoch s otvorenými očami končí chvost ľavého obočia tupo pri vlasoch, asi pri x 40. Nedá sa rozlíšiť, či ho zakrývajú vlasy, alebo končí tupo sám. Treba to overiť na detaile.
3. Obočie sa počas žmurknutia nehýbe ani nedeformuje. Bez chyby.
4. Rámiky 2 a 4 sa zhodujú, obočie po žmurknutí sa vracia na rovnaké miesto. Bez chyby.

## Čo opraviť, v poradí dôležitosti

1. Zúžiť chvost do hrotu ako na pravom obočí.
2. Nahradiť plošinu zreteľným zlomom asi pri x 225, teda asi 73 % dĺžky od nosa, zrkadlovo k pravému obočiu.
3. Predĺžiť chvost asi o 10 až 15 px von.
4. Ubrať asi 5 až 10 px hrúbky v strede a pri hlave, aby sa zhodovala s pravým obočím.
5. Odstrániť čierny fliačik krídla linky pri zatvorenom ľavom oku.

Obmedzenie: hodnoty sú odčítané zrakom z celých pásov, nie zmerané. Pred potvrdením zhody odporúčam porovnať masky obočí v rovnakom výreze.
