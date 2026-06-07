/**
 * pixiApp.ts — creates/destroys the PixiJS Application.
 * PixiJS v8 API: await app.init(), app.canvas (not app.view).
 */

import { Application } from 'pixi.js';

export async function createPixiApp(parent: HTMLDivElement): Promise<Application> {
  const app = new Application();

  await app.init({
    resizeTo: parent,
    antialias: false,
    roundPixels: true,
    backgroundAlpha: 0,
    preference: 'webgl',
  });

  parent.appendChild(app.canvas);
  return app;
}

export function destroyPixiApp(app: Application | null): void {
  if (!app) return;
  app.destroy(true, { children: true, texture: true });
}
