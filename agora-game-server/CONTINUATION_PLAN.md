# Dungeon OS — Continuation Plan (v2)

## ✅ Completed
- [x] Three.js engine setup (isometric, orthographic, OrbitControls)
- [x] 50×50 open floor plan (miestnosti po obvode, basilika stĺpy)
- [x] 6 agentov (King, Voss, Elara, Orin, Kael, Mira)
- [x] ~~Cylinder+sphere placeholder~~ → **GLTF modely** (King, Adventurer, Worker)
- [x] Skeletal idle animácia z GLTF modelov (AnimationMixer)
- [x] Menovky + health bary (canvas sprite nad modelom)
- [x] MCP tooly (spawn, move, state, thought, health, light, ticks)
- [x] WebSocket real-time sync (HTTP :5174, WS :5175)
- [x] Pochodne na vonkajších stenách

## 📦 Assets Ready
- `static/models/King.gltf` (3.7MB) — 👑 Kráľ
- `static/models/Adventurer.gltf` (3.6MB) — 🗡️ Stráž/bojovník
- `static/models/Worker.gltf` (2.9MB) — 🔧 Robotník/zlodej
- `static/models/Farmer.gltf` (2.9MB) — 🌾 Farmár
- **`static/models/ruins/`** (8.2MB, 184 OBJ files) — **Ultimate Modular Ruins Pack!**

## 🏗️ Next Phase: Ruins Pack Integration

### Architektonické assety (OBJ/MTL):

**Steny:** `Wall`, `Wall_Broken`, `Wall_Half`, `Wall_Hole`, `Wall_Overgrown`, `Wall_Double_Hole`, `Wall_Double_Broken`, `Wall_ArchGothic`, `Wall_ArchRound`, `Wall_ArchRound_Broken`, `Wall_ArchRound_Overgrown`, `Wall_ArchRound_Overgrown_Broken`

**Oblúky & Dvere:** `Arch_Gothic`, `Arch_Round`, `Doors_GothicArch`, `Doors_GothicArch_Covered`, `Doors_RoundArch`, `Doors_RoundArch_Covered`

**Stĺpy:** `Column_Round`, `Column_Round_Short`, `Column_Square`, `Arch_Gothic_RoundColumn`, `Arch_Round_RoundColumn`

**Podlahy:** `Floor_Standard`, `Floor_Standard_Half`, `Floor_Squares`, `Floor_Diamond`, `Floor_SquareLarge`, `Floor_Hole_Straight`, `Floor_Hole_Corner`, `Floor_Tree`

**Dekorácie:** `Torch`, `Chest`, `Chest_Gold`, `Candles_1`, `Candles_2`, `Barrel`, `Crate`, `Cart`, `Bookcase_Full`, `Bookcase_Empty`, `Pot1-3`, `Skull`, `Flag_Wall`, `Flag_Wall2`, `Flag_GothicArch`, `Flag_RoundArch`

**Príroda:** `Bush_1x1`, `Bush_2x1`, `Bush_2x2`, `Bush_Large`, `Bush_Round`, `Tree_1-3`, `DeadTree_1-3`, `Grass`

**Ostatné:** `Stairs`, `Stairs_2`, `BridgeSection`, `Trapdoor`, `Rail_Corner`, `Rail_Divider`, `Rail_Straight`, `Support_Center/Left/Right/Tall`, `BearTrap`, `Statue_Fox`, `Statue_Stag`

⚠️ Textúry: `Bark_Texture.jpg`, `Leaf_Texture.png` (referencované z MTL súborov)

### Implementácia:

```js
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';
```

1. **Batch konverzia OBJ → GLB** (najjednoduchšie):
   - `npx obj2gltf -i Wall.obj -o Wall.glb` (alebo Blender script)
   - Potom loadovať cez GLTFLoader (už máme)

2. **Alebo priamy OBJLoader:**
   ```js
   const mtlLoader = new MTLLoader();
   mtlLoader.setPath('/models/ruins/OBJ/');
   mtlLoader.load('Wall.mtl', (materials) => {
     materials.preload();
     const objLoader = new OBJLoader();
     objLoader.setMaterials(materials);
     objLoader.setPath('/models/ruins/OBJ/');
     objLoader.load('Wall.obj', (obj) => scene.add(obj));
   });
   ```

3. **Vytvoriť dungeon layout pomocou modulárnych dielov:**
   - Nahradiť code-generated wall/pillar/floor boxy za OBJ/GLTF assety
   - Miestnosti: `Wall` + `Wall_ArchGothic` pre vchody
   - Stĺpy: `Column_Round` namiesto CylinderGeometry
   - Sály: `Floor_Diamond` alebo `Floor_Squares` namiesto farebných boxov
   - Dekorácie: `Torch`, `Candles`, `Chest`, `Crate` rozmiestniť
   - Kráľovská sieň: `Flag_GothicArch` + `Statue_Fox/Stag`

## 🚀 Server
```
cd ~/agora/agora-game-server
python3 mcp_server.py
# HTTP: http://localhost:5174
# WS: ws://localhost:5175
```
