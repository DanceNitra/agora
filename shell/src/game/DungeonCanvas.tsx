/**
 * DungeonCanvas.tsx — React component mounting the PixiJS dungeon canvas.
 *
 * Lifecycle:
 *   1. useEffect → createPixiApp(containerDiv)
 *   2. Generate textures (PixiJS Graphics API) → build tilemap
 *   3. Start ticker that reads world.ts state and updates sprites
 *   4. On unmount → cleanup
 */

import React, { useRef, useEffect, useState } from 'react';
import { Container } from 'pixi.js';
import { createPixiApp, destroyPixiApp } from './pixiApp';
import { buildTilemap } from './tilemap';
import { generatePixiTextures } from './graphicsTiles';
import { buildAgents, tickAgents } from './agents';
import { buildLighting, tickLighting, applyTorchGlow, applyStageBloom } from './lighting';
import { ParticleSystem } from './particles';
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

      // Generate textures using PixiJS Graphics API (vector, clean)
      const tex = generatePixiTextures(app);

      // Root dungeon container (everything inside gets bloom)
      const dungeonContainer = new Container();

      // Build tilemap container with PixiJS textures
      const worldContainer = new Container();
      buildTilemap(worldContainer, tex as any);
      dungeonContainer.addChild(worldContainer);

      // Build agent sprites (PixiJS vector agents)
      const agentLayer = new Container();
      buildAgents(agentLayer);
      dungeonContainer.addChild(agentLayer);

      // Particles (sparks + dust)
      const particleSystem = new ParticleSystem(dungeonContainer, 40, 19);

      // Lighting layer (darkness overlay + glow sprites)
      const lightLayer = new Container();
      buildLighting(lightLayer, app);
      dungeonContainer.addChild(lightLayer);

      // Add dungeon to stage and apply bloom
      app.stage.addChild(dungeonContainer);
      applyStageBloom(dungeonContainer);

      setReady(true);

      // Ticker
      app.ticker.add(() => {
        tickAgents();
        tickLighting(lightLayer);
        particleSystem.tick();
      });

      // Store for cleanup
      (div as any).__pixiApp = app;
      (div as any).__particleSystem = particleSystem;
    })();

    return () => {
      destroyed = true;
      stopDungeonSocket();
      stopSimulation();
      (div as any).__particleSystem?.destroy();
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
