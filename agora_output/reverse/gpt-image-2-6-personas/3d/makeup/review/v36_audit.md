AUDITOR: independent subagent

# v36: obočie vľavo na obraze, audit

## Verdikt

**Ohyb nadol, ktorý majiteľ nakreslil, vo v36 chýba.** Obočie vľavo na obraze vyzerá takmer rovnako ako vo v32. Je to rovná šikmá čiara, ktorá od nosa stúpa a koniec chvosta je jej najvyšší bod. Na červenej kresbe obočie vytvorí oblúk a chvost potom klesá. Vo v36 nie je viditeľný ani vrchol, ani pokles.

Pixely sú merané na obrázkoch tak, ako sa zobrazili (šírka približne 1160 px). Sú to odhady od oka s presnosťou približne ±5 px, nie meranie skriptom. Referenčný portrét depesa_p6.png som neotvoril, lebo rozpočet na volania nástrojov to nedovolil.

## Porovnanie po častiach

Porovnávam s červenou kresbou (pás 2 vo v36_vs_sketch.png) a so zrkadlovo otočeným obočím vpravo na obraze (červené vo v36_mirror_check.png).

| Časť | Verdikt | Rozdiel |
|---|---|---|
| Začiatok pri nose | MATCH | Oproti v32 je na rovnakom mieste, približne (490, 180) v páse. Majiteľova podmienka „začína presne tam, kde začínalo“ je splnená. Zrkadlo leží v tomto mieste o približne 10–15 px nižšie, ale to je asymetria tváre, nie chyba. |
| Začiatok chvosta (vrchol oblúka) | WRONG | Kresba má vrchol približne v 60 % dĺžky od nosa, za ním čiara klesá. Vo v36 obočie stúpa až po samý koniec a vrchol chýba. |
| Stred | WRONG | Stred leží približne 15–25 px vyššie ako zrkadlo. Vedie po priamke, ale mal by sa začať zaobľovať. |
| Hrúbka | CLOSE | Pri nose má približne 40 px, v strede 35 px a pri chvoste 25 px, rovnako ako vo v32. Zrkadlo je v tretine pri chvoste približne o 5–10 px hrubšie. |
| Zúženie chvosta | WRONG | Koniec je tupý a zaoblený. Kresba aj zrkadlo sa zužujú do hrotu, ktorý smeruje nadol. |
| Celkový uhol | WRONG | Koniec chvosta je približne 90–100 px nad začiatkom pri nose a smeruje nahor. Na kresbe chvost klesá zhruba na úroveň strednej výšky. Rozdiel na konci chvosta je približne 25–40 px. Chvost vo v36 je príliš vysoko a chýba mu pokles. |

## Obočie vpravo na obraze

Oproti v32 sa nezmenilo. Začiatok pri nose aj vrchol sú na rovnakom mieste a zostal aj fialový nádych na vrchole. Pri tejto veľkosti nevidím žiadny rozdiel.

## Chyby v pásoch s pohybom (v36_motion.png)

1. **Snímka so zatvoreným okom (3. pás):** Pri vonkajšom kútiku ľavého oka na obraze je čierny fľak, približne (60, 490). Vyzerá ako krídelko linky, ktoré sa pri zatvorenom viečku odlepilo nad riasy a pláva vo vzduchu. Je to najzreteľnejší defekt.
2. **Riasy pri žmurknutí:** Na ľavom oku na obraze sú riasy hustejšie a strapatejšie ako na pravom. Obe oči sú tak pri žmurknutí výrazne asymetrické.
3. **Obočie vľavo na obraze:** Vo všetkých štyroch snímkach zostáva rovné a stúpa nahor. Pohyb chybu potvrdzuje, nezakrýva ju.
4. **Spodné riasy vpravo na obraze:** Ružový nádych je viditeľný v snímkach 1, 2 a 4. Nie je to nová chyba, bol už vo v32.

## Čo treba opraviť

Pri nose obočie ponechaj na mieste. Vrchol oblúka umiestni približne do 55–60 % dĺžky od nosa a chvost od neho vedie nadol o približne 25–40 px (v mierke obrázka). Chvost zúž do hrotu. Tvar porovnaj so zrkadlom obočia vpravo na obraze.
