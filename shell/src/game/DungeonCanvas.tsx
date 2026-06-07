/**
 * DungeonCanvas.tsx — React component mounting the PixiJS dungeon canvas.
 *
 * Lifecycle:
 *   1. useEffect → createPixiApp(containerDiv)
 *   2. Generate textures → build tilemap container
 *   3. Start ticker that reads world.ts state and updates sprites
 *   4. On unmount → app.destroy() (cleanup, no WebGL leaks)
 */

import React, { useRef, useEffect, useState } from 'react';
import { Container } from 'pixi.js';
import { createPixiApp, destroyPixiApp } from './pixiApp';
import { buildTilemap } from './tilemap';
import { generateAllTextures } from './textures';
import { buildAgents, tickAgents } from './agents';
import { buildLighting, tickLighting, applyTorchGlow, applyStageBloom } from './lighting';
import { startDungeonSocket, stopDungeonSocket } from '../net/dungeonSocket';
import { startSimulation, stopSimulation } from './agentSimulation';

const DungeonCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const div = containerRef.current;
    if (!div) return;

    let destroyed = false;

    // Start WebSocket bridge + local simulation
    startDungeonSocket();
    startSimulation();

    (async () => {
      const app = await createPixiApp(div);

      if (destroyed) {
        app.destroy(true);
        return;
      }

      // Generate textures
      const tex = generateAllTextures();

      // Root dungeon container (everything inside gets bloom)
      const dungeonContainer = new Container();

      // Build tilemap container
      const worldContainer = new Container();
      buildTilemap(worldContainer, {
        floor: tex.floor,
        wall: tex.wall,
        door: tex.door,
      });
      dungeonContainer.addChild(worldContainer);

      // Build agent sprites
      const agentLayer = new Container();
      buildAgents(agentLayer);
      dungeonContainer.addChild(agentLayer);

      // Lighting layer (darkness overlay + glow sprites)
      const lightLayer = new Container();
      buildLighting(lightLayer, app);
      dungeonContainer.addChild(lightLayer);

      // Add dungeon to stage and apply bloom
      app.stage.addChild(dungeonContainer);
      applyStageBloom(dungeonContainer);

      setReady(true);

      // Ticker: read world state and animate agents
      app.ticker.add(() => {
        tickAgents();
        tickLighting(lightLayer);
      });
      // Store for cleanup
      (div as any).__pixiApp = app;
    })();

    return () => {
      destroyed = true;
      stopDungeonSocket();
      stopSimulation();
      const app = (div as any).__pixiApp;
      if (app) {
        app.destroy(true, { children: true, texture: true });
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {!ready && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
          fontFamily: 'monospace',
          fontSize: '14px',
        }}>
          ✦ Initializing Dungeon...
        </div>
      )}
    </div>
  );
};

export default DungeonCanvas;
