AUDITOR: independent subagent, saw only the three-strip comparison and the motion strip

Zdroj: v35_vs_sketch.png (1160 px šírka, pásy: v32 y 0-360, náčrt y 360-700, v35 y 725-1085) a v35_motion.png. Súradnice sú v pixeloch každého pásu. Náčrt vlastníka je zmenšený asi na 0,85 voči pásom 1 a 3, preto ho porovnávam tvarom, nie pixelom. Odhady sú od oka, presnosť asi 5 px.

## 1. Ľavé obočie (na obrázku) proti červenej čiare: CLOSE, smerom k WRONG v tvare chvosta a hrúbke

Čo sedí:
- Vnútorný koniec (pri koreni nosa) ostal na mieste: v32 asi x 490, y 195; v35 asi x 490, y 180-190. Rozdiel do 10 px. Sedí so zadaním „musí začať presne tam, kde začínalo“.
- Stred je znížený: horný okraj na vrchole oblúka (x asi 230) klesol z y asi 68 (v32) na y asi 90 (v35), teda asi o 20 px nadol. Smer zodpovedá červenej čiare.
- Vonkajší koniec klesol: v32 asi x 140, y 85; v35 asi x 130, y 105. Asi 20 px nadol a 10 px doľava. Smer zodpovedá červenej čiare, ktorá začína nižšie a mierne vľavo od pôvodného chvosta.

Rozdiely proti červenej čiare:
- Tvar: červená čiara je stále jemný oblúk (plochý vrchol, potom klesá k vnútornému koncu). v35 pôsobí skôr ako rovný šikmý pás bez oblúka. Vrchol je takmer zrušený, nie len znížený.
- Hrúbka: vonkajšia polovica v35 je hrubšia ako v32, odhadom 35-40 px proti 25-30 px, teda asi +10 px. Červený obrys predpisuje podobnú alebo užšiu hrúbku, nie hrubšiu.
- Chvost: v32 sa vonkajší koniec zužoval do hrotu. v35 končí tupo, takmer v plnej hrúbke. Červený obrys sa na ľavom konci zužuje.
- Vnútorný koniec v náčrte: červená čiara sa pri vnútornom konci napája na spodný okraj obočia a mierne ho stláča nadol. V v35 sa vnútorný koniec viditeľne nezmenil (to je v poriadku), ale prechod zo stredu do vnútorného konca je rovný, nie ohnutý ako na náčrte.

Verdikt bodu 1: CLOSE pre polohu oboch koncov a zníženie stredu; WRONG pre hrúbku vonkajšej polovice a tupý chvost.

## 2. Pravé obočie (na obrázku): MATCH

Pás 1 a pás 3 sú na pravom obočí okom nerozlíšiteľné: poloha, oblúk, fialový nádych pri vonkajšom konci aj prechod do sivej pri vnútornom konci. Súhlasí s nameraným rozdielom 0,16 z 255.

## 3. Nové chyby: CLOSE

- Obe obočia teraz pôsobia ako iný druh: pravé je oblúk so zúženým chvostom, ľavé je hrubý rovný pás s tupým koncom. Pri pohľade na celú tvár je to najviditeľnejšia nesúmernosť.
- Horný okraj ľavého obočia v v35 pôsobí tvrdšie a rovnejšie ako v v32, menej jednotlivých chĺpkov vyčnieva nad líniu. Pri tomto rozlíšení to neviem potvrdiť ako chybu, odporúčam priblíženie.
- Diery ani chĺpky mimo obočia v pásoch nevidím.
- Žmurknutie (v35_motion.png): obočie sa počas žmurknutia nehýbe a nerozpadá sa, po žmurknutí je rovnaké ako pred ním. Pri zatvorenom ľavom oku je pri vonkajšom kútiku tmavá škvrna (krídlo linky na viečku). To sa týka linky, nie obočia, a zo zadaných obrázkov neviem povedať, či je nová vo v35.

## Súhrn

| bod | verdikt |
|---|---|
| 1. konce na mieste | MATCH |
| 1. stred znížený | CLOSE (znížený asi o 20 px, ale oblúk takmer zmizol) |
| 1. hrúbka a chvost | WRONG (vonkajšia polovica asi +10 px hrubšia, chvost tupý) |
| 2. pravé obočie | MATCH |
| 3. nové chyby | CLOSE (nesúmerný druh obočia, tvrdší horný okraj na overenie) |

Odporúčaná ďalšia zmena: zachovať konce a zníženie, vrátiť jemný oblúk podľa červenej čiary a zúžiť vonkajšiu tretinu do hrotu ako v v32.
