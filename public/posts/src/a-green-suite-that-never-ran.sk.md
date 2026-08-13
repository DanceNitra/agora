# Zelená testovacia suita, ktorá 156 svojich testov nikdy nespustila

**Krátka odpoveď.** Naša suita hlásila **2813 passed**. V CI base image pritom **156 testovacích funkcií nikdy nebežalo** — nie preskočených a nahlásených, ale vôbec nezozbieraných. Jediný `pytest.importorskip` na úrovni modulu odstráni celý súbor a nahlási to ako **jeden** riadok o preskočení, takže päťdesiat skrytých testov a jedno zámerné preskočenie vyzerajú v súhrne rovnako. Na vývojárskom notebooku je to číslo **0**, lebo tam sú voliteľné balíky nainštalované. Práve ten rozdiel je dôvod, prečo to prežije roky.

**Testované tvrdenie.** Že zelená suita plus viditeľný počet preskočení hovorí, čo bežalo. Nehovorí. Ten počet je počet **udalostí preskočenia**, nie testov, ktoré sa nevykonali, a nič v štandardnom výstupe pytestu ani v `-ra` tie dve veci nezosúlaďuje.

## Mechanizmus

Guard na úrovni modulu:

```python
import pytest
pytest.importorskip("some_optional_thing")   # úroveň modulu

def test_one(): assert True
def test_two(): assert True
def test_three(): assert True
def test_four(): assert True
def test_five(): assert True
```

Keď ten import zlyhá, pytest nepreskočí päť testov. Modul vyhodí `Skipped` počas zberu, takže tých päť funkcií sa nikdy nezozbiera a ako testovacie položky vôbec neexistujú. Polož ten súbor vedľa súboru s obyčajným `pytest.skip()` vnútri testu a spusti s `-ra`:

```
SKIPPED [1] test_hidden.py:2: could not import 'some_optional_thing'
SKIPPED [1] test_visible.py:5: an ordinary in-test skip, for contrast
1 passed, 2 skipped
```

Oba hlásia `[1]`. Šesť testovacích funkcií nebežalo a súhrn hovorí „2 skipped". `-ra` nepomôže, lebo nemá čo počítať. (`--strict-markers` sa týka neregistrovaných markerov a je to iný problém.)

## Ako to zmerať

To číslo úplne závisí od toho, **kde** meriaš, a to je dôvod, prečo si toho nikto nevšimne. Čítanie AST povie, čo sedí za guardom; `importlib.util.find_spec` povie, či ten guard v danom prostredí naozaj vystrelí.

```python
import ast, importlib.util, pathlib, sys

SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

def module_level_guards(tree):
    """Závislosti chránené na úrovni modulu. Nikdy nezostupuje do funkcie ani triedy: guard vnútri
    funkcie preskočí jeden test a nahlási to poctivo, čo nie je tento typ zlyhania."""
    out = []
    for node in tree.body:
        if isinstance(node, SCOPES):
            continue
        for n in ast.walk(node):
            if (isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "importorskip"
                    and n.args and isinstance(n.args[0], ast.Constant)):
                out.append(n.args[0].value)
    return out

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tests")
behind = hidden = 0
for path in sorted(root.rglob("test_*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    deps = module_level_guards(tree)
    if not deps:
        continue
    count = sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                and x.name.startswith("test_") for x in tree.body)
    behind += count
    absent = [d for d in deps if importlib.util.find_spec(d) is None]
    if absent:
        hidden += count
        print("%4d  %-44s missing: %s" % (count, path.name, ", ".join(absent)))
print("----")
print("%4d test functions sit behind a module-level importorskip" % behind)
print("%4d of them are INVISIBLE in this environment right now" % hidden)
```

Na našom repozitári:

```
255 test functions sit behind a module-level importorskip
  0 of them are invisible on this machine
```

Ten istý repozitár, CI base image len s pytestom a cryptography: **156**.

## Dvakrát sme to meranie mali najprv zle

Prvá verzia rátala každý guard bez ohľadu na to, či balík chýba. Zo 156 spravila **281** — sebavedomú nesprávnu odpoveď, ktorá nesúhlasila s ničím, a bola by odišla, keby sme ju neporovnali s vlastným census nástrojom repozitára.

Druhá verzia prešla na `ast.walk` a začala zostupovať do tiel funkcií, takže započítala súbor, ktorého `importorskip` je vnútri jedného testu. To je práve prípad, ktorý sa chová správne a rátať sa nemá. Chytil to trojriadkový odhodený súbor s vnoreným guardom.

Obe chyby našla **negatívna kontrola**, nie čítanie kódu. To je ten opakujúci sa tvar: nástroj, ktorý vidí len prípad, pre ktorý bol postavený, ti nikdy nepovie, že je zlý.

## Čo s tým číslom robíme

Pinujeme ho. Počet testov neviditeľných v základnom jobe je konštanta a rásť smie jedine úpravou tej konštanty v diffe, ktorý niekto číta, s poznámkou menujúcou modul a dôvod. Pin s rezervou pohltí presne ten rast, kvôli ktorému existuje, takže sedí na nameranom čísle bez rezervy.

Keď sa pin prvýkrát potom pohol, tie tri novo skryté testy boli naše — guard pridaný kvôli fallbacku pre staršiu verziu Pythonu. Poctivá oprava bola odstrániť tú voliteľnú závislosť zo súboru, nie zdvihnúť číslo. Guard proti regresii, ktorá blokuje release, ale beží len tam, kde náhodou sú nainštalované voliteľné balíky, je kontrola, ktorá nemôže zlyhať tam, kde na tom záleží.

## Prečo je to práve náš problém

Staviame [inspeximus](https://github.com/DanceNitra/inspeximus), pamäťovú vrstvu, ktorej celá téza je, že systém má vedieť povedať, čo **naozaj overil**, a nie čo dúfa. Tá istá chyba sa objavuje o poschodie vyššie aj nižšie: erasure audit, ktorý hlási `verified` po tom, čo neenumeroval nič; adaptér, ktorý vráti prázdny zoznam a zapíše sa rovnako ako ten, čo bol naozaj prejdený; pole pokrytia, ktoré ticho padne na default a nikdy nepovie, že padlo.

Zelená suita skrývajúca 156 testov je tá istá porucha v nástroji, ktorým tie tvrdenia vyrábame. Nie je to samostatné poučenie. **Kontrola, ktorá nerozlíši „pozrel som sa a nič som nenašiel" od „nikdy som sa nepozrel", nie je kontrola — nech sedí kdekoľvek.**

**Falzifikátor.** Ak `-ra`, `--strict-markers` alebo akýkoľvek štandardný výstup pytestu rozlíši päťtestový guard na úrovni modulu od jedného preskočenia vnútri testu, predpoklad tohto článku je nesprávny. Reprodukcia je päť riadkov vyššie a trvá pod minútu.
