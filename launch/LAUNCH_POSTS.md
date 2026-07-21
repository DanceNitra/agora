# Launch posts — second_brain_mcp + inspeximus (DRAFT, gated — nothing posted until owner ships)

> Corrected after an adversarial honesty review (run wf_ec21e760). Every number below is verified
> against the real lab ledger; the run command is tested working after a flat download.
> **Verified facts used:**
> - Run command: `python second_brain_mcp.py` (script form, works after a flat download; the `-m`
>   package form does NOT — keep it script-form everywhere).
> - Recall (run `b4c260`, "embedder-crossover-by-store-size"): lexical recall@5 decays from **0.94**
>   at a small store to **0.25** at ~6k notes, while semantic **holds ~0.65** → ≈**2.6×** at full scale.
> - Recall (run `3501f1`, paraphrase queries): semantic recall@5 **0.86** vs lexical **0.20**.
> - Vault size: **~6,000 notes** (the corpus the recall numbers were measured on).
> - The severe-tested ideas (cue-validity crossover ~0.45; independence is the load-bearing
>   wise-crowd condition) were tested in the **separate Agora research lab**, NOT inside the MCP server.

---

## EN — Show HN

**Title:** `Show HN: MCP server that turns a Markdown vault into a thinking partner`

I run an autonomous research system whose memory layer (inspeximus) is a single zero-dependency Python
file. I pulled the "think over my notes" part out into an MCP server and want to show it honestly —
because the design choice is the whole point.

**The distinction I care about:** the server does NOT think. It gives an agent (Claude Desktop,
Cursor, Claude Code) retrieval + structure over a folder of notes; the LLM does the reasoning. The
tool is the memory and the map; the model is the mind. There is no LLM call inside the server, so it
runs anywhere. I'm not claiming an autonomous oracle — I'm claiming a substrate that makes an agent's
reasoning over *your own* notes possible.

**What it exposes (MCP tools):**
- `relevant_notes` — pull substrate, ranked by relevance × accrued value (value accrues as you use a
  note; a cold index is effectively relevance-ranked on the first run)
- `find_gaps` — isolated/under-linked notes + thin folders (trivially noisy on a tiny vault; earns
  its keep at scale)
- `bridge_candidates` — distant notes (different folder, no link) that are semantically close =
  candidate connections
- `extract_claims` — claim-like sentences from a note so the agent can ground or challenge them
- `idea_methods` — a toolkit of named idea-generation recipes, so generation is principled, not a vibe

**Zero config, true:** with no embedder it uses a lexical-overlap fallback and runs today. An
embedder is optional (`INSPEXIMUS_EMBED_URL/MODEL/KEY`, any OpenAI-compatible endpoint). It matters most
**at scale**: on my vault, lexical recall@5 decayed from 0.94 on a small store to **0.25 at ~6k
notes**, while semantic recall held at **~0.65** (≈2.6× at full corpus). Lexical is a real floor for
a small vault, not a stub; semantic is what stops the floor from falling out as you grow.

**The true story (why I think it's worth your time):** I dogfooded it on my own ~6,000-note Obsidian
vault. In one run, Claude using these tools:
1. Read my decision-science notes and caught a number in my *own* forecasting note inflated ~7× — I'd
   written that training beat controls "by 60-78%"; the actual Good Judgment Project figure is ~6-11%.
2. Found two of my beliefs silently contradicting (crowd-averaging vs lone-expert "recognition-primed"
   judgment) and turned the clash into one experiment.
3. Generated ideas via my own documented methods (`idea_methods`). I then severe-tested two of them in
   my separate research lab (not inside this MCP server); both held — a cue-validity crossover near
   signal-quality ~0.45 that flips crowd-vs-expert, and that independence is the load-bearing "wise
   crowd" condition.

**Honest caveats:** the LLM did the reasoning, not the tool. The ~7× catch still needs source-checking
before I'd cite it publicly — I'm reporting it as "the agent flagged this and it held up on my check,"
not as verified fact. No invented benchmarks, no "10×", no testimonials.

**Try it (works after a flat download):**
```
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/second_brain_mcp.py
pip install "mcp[cli]"
NOTES_DIR=/path/to/your/vault python second_brain_mcp.py
```
Then register it with your MCP client and call `index_status`, then `relevant_notes`. The underlying
store is append-only and contradictions are flagged, never auto-resolved — I didn't want a tool that
silently rewrites my notes.

**License / model:** MIT, open core, free. A hosted/pro tier is a maybe later, not a promise — nothing
here is paywalled. Repo: https://github.com/DanceNitra/agora (`inspeximus/`). Track record + methods:
https://dancenitra.github.io/agora/

The part I'm least sure of is the gap/bridge heuristic — happy to be told where it's too crude on a
vault that isn't mine.

---

## EN — Reddit (r/ObsidianMD)

**Title:** `Made an MCP server that lets Claude/Cursor think over my vault — it caught a number in my own note that was off by ~7x`

I've been dogfooding a small tool on my own ~6,000-note vault and figured this sub would either find
it useful or tell me exactly where it's dumb.

It's an MCP server you point at your notes folder. It does **not** think for you — it gives your agent
(Claude Desktop, Cursor, etc.) structured access to your vault, and the agent does the reasoning. I'm
not selling a magic "AI second brain that thinks." The tool is the memory and the map; the model is
the mind.

What it actually surfaces:
- the notes most relevant to a topic (ranked by relevance × how much value a note has accrued as you
  use it — a fresh index is basically relevance-ranked)
- **gaps**: isolated notes with no `[[links]]` and folders that are thin vs the rest (on a small vault
  this is noisy; it gets useful as the vault grows)
- **bridge candidates**: notes in different folders, no link between them, that are semantically close
  — connections you probably should have made
- **claim-like sentences** from a note, so the agent can go ground or challenge them
- a toolkit of named idea-generation methods (inversion, abstraction-ladder, missing-reciprocity, …)
  so it generates ideas by a recipe instead of vibes

Why I'm posting: in one run, Claude using these tools read my decision-science notes and caught a stat
in my *own* forecasting note inflated by ~7× — I'd written training beat controls "by 60-78%"; the
real Good Judgment Project number is ~6-11%. It also caught two of my notes quietly contradicting each
other and proposed one experiment to settle it.

Honesty, because this sub (rightly) hates hype: the LLM did the catching, not the tool — the tool just
handed it the right notes and the claims. And I still need to re-check that ~7× correction against the
source before I'd trust it. The underlying store is append-only and contradictions get **flagged**,
never auto-edited — I didn't want anything silently rewriting my notes.

Runs with zero config (lexical fallback). Optional embedder for semantic bridges — it matters at scale
(on my vault lexical recall@5 fell to ~0.25 at ~6k notes while semantic held ~0.65). Single file, no
required deps, MIT.

```
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/second_brain_mcp.py
pip install "mcp[cli]"
NOTES_DIR=/path/to/your/vault python second_brain_mcp.py
```

Repo: https://github.com/DanceNitra/agora (look in `inspeximus/`). Genuinely interested whether the
gap/bridge heuristics surface anything useful on a vault that isn't mine — it's read-only, local, no
telemetry.

---

## SK — Show HN / všeobecná verzia

**Titulok:** `Show HN: MCP server, ktorý zmení Markdown vault na partnera na premýšľanie`

Prevádzkujem autonómny výskumný systém, ktorého pamäťová vrstva (inspeximus) je jeden Python súbor bez
závislostí. Časť „premýšľaj nad mojimi poznámkami" som vytiahol do MCP servera a chcem to ukázať
úprimne — lebo práve to dizajnové rozhodnutie je celá pointa.

**Rozdiel, na ktorom mi záleží:** server **nepremýšľa**. Dáva agentovi (Claude Desktop, Cursor, Claude
Code) vyhľadávanie + štruktúru nad priečinkom poznámok; uvažuje LLM. Nástroj je pamäť a mapa; model je
myseľ. Vnútri servera nie je žiadne volanie LLM, takže beží kdekoľvek. Netvrdím, že je to autonómna
veštba — tvrdím, že je to substrát, ktorý umožní agentovi uvažovať nad **tvojimi vlastnými** poznámkami.

**Čo ponúka (MCP nástroje):**
- `relevant_notes` — substrát zoradený podľa relevancie × nazbieranej hodnoty (hodnota rastie tým, ako
  poznámku používaš; čerstvý index je v podstate len podľa relevancie)
- `find_gaps` — izolované/málo prepojené poznámky + tenké priečinky (na malom vaulte je to šum; zmysel
  dáva pri škále)
- `bridge_candidates` — vzdialené poznámky (iný priečinok, žiadny link), čo sú sémanticky blízke =
  kandidáti na spojenie
- `extract_claims` — vetné tvrdenia z poznámky, ktoré vie agent overiť alebo spochybniť
- `idea_methods` — sada pomenovaných receptov na tvorbu ideí, aby generovanie bolo princípom, nie vibe-om

**Zero config, naozaj:** bez embeddera používa lexikálny fallback a beží dnes. Embedder je voliteľný
(`INSPEXIMUS_EMBED_URL/MODEL/KEY`, akýkoľvek OpenAI-kompatibilný endpoint). Najviac sa oplatí **pri škále**:
na mojom vaulte lexikálny recall@5 klesol z 0,94 na malom úložisku na **0,25 pri ~6 000 poznámkach**,
kým sémantický držal **~0,65** (≈2,6× pri plnom korpuse).

**Pravdivý príbeh (prečo to stojí za pozornosť):** otestoval som to na vlastnom ~6 000-poznámkovom
Obsidian vaulte. V jednom behu Claude pomocou týchto nástrojov:
1. Prečítal moje poznámky o rozhodovaní a chytil v mojej *vlastnej* poznámke o prognózovaní číslo
   nafúknuté ~7× — napísal som „tréning prekonal kontrolnú skupinu o 60-78 %"; reálne číslo z Good
   Judgment Project je ~6-11 %.
2. Našiel dve moje presvedčenia, čo si ticho protirečia (priemerovanie davu vs jeden expert), a urobil
   z toho jeden experiment.
3. Vygeneroval idey cez moje vlastné zdokumentované metódy (`idea_methods`). Dve som potom severe-testol
   v samostatnom výskumnom labe (nie vnútri tohto MCP servera) — obe obstáli.

**Úprimné výhrady:** uvažoval LLM, nie nástroj. Tú ~7× opravu treba ešte overiť oproti zdroju, kým by
som ju citoval verejne — uvádzam to ako „agent to označil a u mňa to obstálo", nie ako overený fakt.
Žiadne vymyslené benchmarky, žiadne „10×", žiadne testimoniály.

**Vyskúšaj (funguje po obyčajnom stiahnutí):**
```
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/second_brain_mcp.py
pip install "mcp[cli]"
NOTES_DIR=/cesta/k/tvojmu/vaultu python second_brain_mcp.py
```

**Licencia / model:** MIT, open core, zadarmo. Hostovaný/pro tier je možno neskôr, nie sľub — nič tu nie
je za paywallom. Repo: https://github.com/DanceNitra/agora (`inspeximus/`).

---

## SK — Reddit / komunitná verzia

**Titulok:** `Spravil som MCP server, vďaka ktorému Claude/Cursor premýšľa nad mojím vaultom — chytil v mojej vlastnej poznámke číslo nafúknuté ~7×`

Testujem malý nástroj na vlastnom ~6 000-poznámkovom vaulte. Nástroj **nepremýšľa za teba** — dáva
tvojmu agentovi štruktúrovaný prístup k vaultu a uvažuje agent. Nepredávam zázračný „AI druhý mozog, čo
myslí". Nástroj je pamäť a mapa; model je myseľ.

Čo reálne vynáša: najrelevantnejšie poznámky (relevancia × nazbieraná hodnota), **diery** (izolované
poznámky bez `[[linkov]]` a tenké priečinky), **kandidátov na spojenie** (vzdialené poznámky, čo sú si
sémanticky blízke), **vetné tvrdenia** na overenie/spochybnenie, a sadu **metód na tvorbu ideí**.

Prečo to píšem: v jednom behu Claude cez tieto nástroje chytil v mojej *vlastnej* poznámke o
prognózovaní štatistiku nafúknutú ~7× (napísal som „60-78 %", reálne ~6-11 %), a našiel dve moje
poznámky, čo si protirečia. Úprimne: chytil to LLM, nie nástroj — nástroj mu len podal správne poznámky.
A tú opravu si ešte musím overiť oproti zdroju. Úložisko je append-only, protirečenia sa **označia**,
nikdy automaticky neprepíšu — nechcel som nič, čo by mi ticho prepisovalo poznámky.

Beží bez konfigurácie (lexikálny fallback). Voliteľný embedder pre sémantické mosty — oplatí sa pri
škále. Jeden súbor, bez nutných závislostí, MIT.

```
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/second_brain_mcp.py
pip install "mcp[cli]"
NOTES_DIR=/cesta/k/vaultu python second_brain_mcp.py
```

Repo: https://github.com/DanceNitra/agora (`inspeximus/`). Je to read-only, lokálne, bez telemetrie.
