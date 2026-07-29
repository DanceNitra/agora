# Vydanie 1.87.0 — overené zvonku, nie z workflowu

**2026-07-29.** Workflow hlásil úspech. To je tvrdenie workflowu, nie stav sveta, takže:

| kde | stav |
|---|---|
| PyPI `inspeximus` | **1.87.0**, 2 súbory, `requires_python >=3.8` |
| MCP registry | **1.87.0**, `isLatest: True`, publikované 2026-07-28T21:33:43 |
| tag `v1.87.0` | ukazuje na `7dcbe2a` |
| wheel stiahnutý z PyPI | prešiel všetkých 8 kontrol brány, ktorá na 1.86.0 padla na 6 z 8 |

## Skoro som ohlásil zastaraný registry

Prvé čítanie vrátilo `version: 1.28.1` a všetko `isLatest: False`. Vyzeralo to ako zlyhaný zápis.

Bola to **chyba mojej čítačky**: API vracia 30 položiek na stránku od najstaršej a ja som neprestránkoval.
`RELEASING.md` presne toto zaznamenáva — *„44 publikovaných verzií je aj to, čo rozbilo kontrolu MCP
registry: čítala prvú stránku 30-položkového API a už nevidela verziu, ktorú práve vydala"* — a v pamäti
mám na to vlastnú poznámku. Zreprodukoval som známy defekt čítania a takmer ho vydal za nález.

Po prestránkovaní (3 strany, 61 položiek) je odpoveď jednoznačná a opačná.

**Poučenie, ktoré platí aj mimo tohto:** keď kontrola hlási, že niečo vonku chýba, over najprv **čítačku**.
Dnes v noci to bolo trikrát — panel skeptikov meral starú kópiu, môj CLI sken pretiekol do vedľajšej
vetvy, a teraz toto.
