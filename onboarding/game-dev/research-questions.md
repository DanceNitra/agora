# 🧪 Agora Dungeon — Research Questions pre NotebookLM

## Cieľ
Získať **presné implementačné detaily** z kníh + paperov, aby som mohol kódovať herné AI systémy, ktoré ešte nepoznám — a upgradnúť skill `agora-dungeon-game-dev` na plne funkčného coding agenta.

---

## 1. 🧠 Memory Stream + Reflection (Generative Agents paper)

Toto je north star — agenti s pamäťou, ktorá sa vyvíja.

### Otázky:
```
1.1  Aký je presný algoritmus Memory Stream v Generative Agents?
     - Ako sa vypočíta importance (1-10) pre každú spomienku?
     - Ako funguje retrieval weighting: recency × importance × relevance?
     - Aké sú presné vzorce a parametre (α, decay rate 0.995)?

1.2  Ako presne funguje Reflection Tree?
     - Kedy sa spustí reflexia (sum(importance) > 150)?
     - Ako vyzerá JSON štruktúra reflections?
     - Ako sa vyššie úrovne abstrakcie odvodzujú z nižších?

1.3  Ako funguje plánovanie v Generative Agents?
     - Recurse plan: daily → hourly → actions — presný JSON formát?
     - Ako agenti menia plány na základe nových spomienok?
     - Ako funguje "react" keď agent zbadá niečo neočakávané?

1.4  Daj mi presný TypeScript/JavaScript kód pre implementáciu
     retrospektívneho vyhľadávania (retrieval) s vážením
     recency + importance + relevance. Potrebujem triedu MemoryStream.
```

---

## 2. 🌲 Behavior Trees (Behavior Trees paper + Game AI by Example)

Toto je NPC AI — nahrádza FSM pre komplexné správanie.

### Otázky:
```
2.1  Daj mi presný TypeScript kód implementácie Behavior Tree runtime:
     - Triedy: Selector, Sequence, Condition, Action, Decorator, Parallel
     - Ako funguje tick() — presný flow s NodeState (SUCCESS/FAILURE/RUNNING)?
     - Ako sa správajú Selector vs Sequence pri RUNNING deťoch?

2.2  Ako implementovať Behavior Tree editor v Phaser 3?
     - Ako serializovať BT do JSON a deserializovať späť?
     - Ako vizuálne debugovať ktorý node práve beží?

2.3  Daj mi príklad komplexného Behavior Tree pre NPC strážcu v 2D dungeon:
     - Patrol → Detect player → Combat → Flee when low health → Heal → Patrol
     - Ako kombinovať BT s A* pathfindingom?

2.4  Ako presne funguje "Parallel" node?
     - All-Parallel (čaká na všetky deti) vs Any-Parallel (prvý hotový)?
     - Ako riešiť RUNNING stav u Parallel nodov?
```

---

## 3. 🏃 Pathfinding + Steering (AI for Games kniha)

NPC pohyb — A*, steering behaviours.

### Otázky:
```
3.1  Daj mi presnú TypeScript implementáciu A* pre tile-based 2D mapu:
     - GridGraph + Node + Heuristic (manhattan/Euclidean)
     - Ako optimizovať A* pre veľké mapy (hierarchický A*, JPS)?

3.2  Ako implementovať tieto steering behaviours v Phaser 3?
     - Seek, Flee, Arrival, Pursuit, Evasion, Wander, Obstacle Avoidance
     - Ako kombinovať viac steeringov naraz (blended steering)?
     - Presný kód: velocity-based, s max_speed a max_force.

3.3  Ako implementovať navmesh (navigation mesh) namiesto tile grid?
     - Ako triangulovať mapu na navmesh?
     - Ako beží A* na navmeshi namiesto gridu?

3.4  Ako implementovať group movement?
     - Flocking (Separaton, Alignment, Cohesion) — presný kód
     - Crowd pathfinding — ako riešiť kolízie medzi NPC
```

---

## 4. 🎲 Decision Making — FSM, Fuzzy, Utility AI (Game AI by Example)

Ako NPC rozhodujú čo robiť.

### Otázky:
```
4.1  Daj mi presnú TypeScript implementáciu Hierarchical FSM:
     - State, StateMachine, Transition, Action
     - Ako debugovať ktorý state práve beží?

4.2  Ako implementovať Fuzzy Logic v Game AI?
     - Membership functions (triangular, trapezoidal)
     - Fuzzification → Inference → Defuzzification (COG metóda)
     - Konkrétny príklad: fuzzy health → enemy threat assessment

4.3  Ako implementovať Utility AI?
     - Utility curves (linear, exponential, logistic)
     - Ako agent vyhodnotí viac akcií a vyberie najvyššiu utility?
     - Ako kombinovať utility s Behavior Trees?

4.4  Daj mi kód pre Decision Tree runtime v TypeScript:
     - TreeNode, DecisionNode, ActionNode
     - Ako serializovať decision tree do JSON
```

---

## 5. 🤝 Multi-Agent Coordination (Shoham kniha)

Ako agenti medzi sebou komunikujú, súťažia, kooperujú.

### Otázky:
```
5.1  Ako implementovať Contract Net Protocol v TypeScript?
     - Task announcement → bids → award → execution → completion
     - Ako agenti hodnotia či sa im oplatí bidnúť na task?

5.2  Ako implementovať Aukcie pre rozdelenie úloh medzi agentov?
     - First-price sealed bid, Vickrey (second-price) auction
     - Ako agenti vypočítajú svoju valuation pre task?

5.3  Ako implementovať kooperatívne správanie?
     - Coalition formation — ktorí agenti spolupracujú na tasku?
     - Shapley value — ako rozdeliť odmenu medzi agentov v koalícii?

5.4  Ako implementovať trust a reputáciu medzi agentmi?
     - Presný algoritmus trust update z ESS protokolu
     - Ako trust ovplyvňuje výber partnera pre task

5.5  Ako implementovať argumentation / negotiation medzi agentmi?
     - Jednoduché vyjednávanie o cene tasku
     - Persuasion — agent presviedča iného agenta
```

---

## 6. 🎮 Game Programming Patterns — architektúra

Ako postaviť hru cleanly.

### Otázky:
```
6.1  Daj mi presný TypeScript kód pre Game Loop pattern v Phaser 3:
     - Fixed timestep vs variable timestep
     - Ako oddeliť update (logika) od render (grafika)?

6.2  Ako implementovať Component pattern pre herné entity?
     - Entity je ID + Component[]
     - Position, Render, Health, AI, Inventory komponenty
     - Ako systém iteruje entity so správnymi komponentami?

6.3  Ako implementovať Event Bus / Observer pattern pre herné eventy?
     - Event: enemy_killed, item_picked, quest_completed
     - Ako na eventy reagujú agenty, UI, quest systém?

6.4  Ako implementovať State pattern pre hru samotnú?
     - MenuState, PlayingState, PauseState, GameOverState
     - Ako prepínať medzi state-ami bez memory leakov?

6.5  Ako implementovať Object Pool pre projectily / častice?
     - Pre-allokovať 50 projectile objektov, reusable
     - TypeScript kód s generic <T>
```

---

## 7. 🔗 LLM + Traditional Game AI Hybrid

Ako spojiť Generative Agents LLM s tradičnými algoritmami.

### Otázky:
```
7.1  Kedy volať LLM a kedy použiť tradičný algoritmus?
     - LLM: dialógy, plány, reflexie, kreatívne rozhodnutia
     - Tradičné: pathfinding, combat, physics, movement
     - Daj mi decision flow: "ktorú cestou ísť?"

7.2  Ako implementovať "LLM-as-a-Service" v spine?
     - Fronta requestov, pooling, rate limiting, timeout
     - Ako agenti čakajú na LLM odpoveď bez zaseknutia tick loopu?

7.3  Ako dať LLM kontext z herného sveta?
     - Vektorová databáza pre retrospektívne vyhľadávanie (Qdrant/Chroma)
     - Aké informácie posielať do promptu: okolie, inventár, HP, spomienky
     - Maximálna dĺžka promptu — ako prioritizovať context?

7.4  Daj mi príklad promptu pre agenta v dungeon svete:
     - Je v miestnosti s dvoma NPC a jedným monštrom
     - Jeho inventory: meč, kľúč, 3 životy
     - Má spomienku: "včera ma zradil NPC Bob"
     - Ako by mal LLM rozhodnúť čo robiť?
```

---

## 8. 🎨 Phaser 3 + UI (praktické)

Konkrétne Phaser 3 implementácie pre Agora dungeon.

### Otázky:
```
8.1  Ako vytvoriť tile-based mapu v Phaser 3 z Tiled editoru?
     - Ako načítať .tmx/.json mapu
     - Ako nastaviť kolízie pre konkrétne tile-y
     - Ako implementovať kamery a parallax layers

8.2  Ako implementovať turn-based combat v Phaser 3?
     - Battle state: výber akcie → animácia → damage → check death
     - Ako UI zobrazuje HP bary, stavové efekty, log akcií?

8.3  Ako implementovať dialógový systém s NPC?
     - Dialógový strom s možnosťami odpovedí
     - Ako vetviť dialóg podľa stavu questu/inventára
     - Ako LLM generuje dynamické dialógy?

8.4  Ako implementovať inventory / quest log UI?
     - Drag & drop predmety
     - Quest tracker: aktívne questy, progress, completion

8.5  Ako spraviť mini-mapu v Phaser 3?
     - Render celú mapu do malej textúry
     - Zobraziť pozíciu hráča a objavené oblasti (fog of war)
```

---

## 🎯 Priority poradie do NotebookLM

1. **Memory Stream + Reflection** (Q1) — najdôležitejšie, north star
2. **Behavior Trees** (Q2) — NPC AI treba hneď
3. **Pathfinding + Steering** (Q3) — pohyb NPC
4. **Decision Making** (Q4) — FSM, fuzzy, utility
5. **Multi-Agent Coordination** (Q5) — až keď bežia agenti
6. **Game Architektúra** (Q6) — vždy dobré vedieť
7. **LLM Hybrid** (Q7) — keď zapneme LLM
8. **Phaser 3 UI** (Q8) — keď ideme na frontend

---

> **Ako používať:** Daj týchto 8 sekcií postupne do NotebookLM (jedna séria otázok = jedna NotebookLM relácia). Po každej relácii daj vedieť — ja spracujem odpovede a upgradnem skill `agora-dungeon-game-dev` s presným TypeScript kódom.
