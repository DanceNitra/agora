/**
 * pixiApp.ts — creates/destroys the PixiJS Application.
 * PixiJS v8 API: await app.init(), app.canvas (not app.view).
 *
 * Handles initial sizing: uses ResizeObserver to ensure the canvas
 * gets proper dimensions even when the parent starts at zero size
 * (common with flex layouts during React hydration).
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

  // Ensure canvas fills parent even if parent was zero-sized at init
  // (common after React re-render / route transition)
  requestAnimationFrame(() => {
    if (parent.offsetWidth > 0 && parent.offsetHeight > 0) {
      app.renderer.resize(parent.offsetWidth, parent.offsetHeight);
    }
  });

  // Also watch for future resize
  const observer = new ResizeObserver(() => {
    if (parent.offsetWidth > 0 && parent.offsetHeight > 0) {
      app.renderer.resize(parent.offsetWidth, parent.offsetHeight);
    }
  });
  observer.observe(parent);
  (parent as any).__pixiObserver = observer;

  return app;
}

export function destroyPixiApp(app: Application | null, parentDiv?: HTMLDivElement): void {
  if (!app) return;
  if (parentDiv?.__pixiObserver) {
    (parentDiv as any).__pixiObserver.disconnect();
  }
  app.destroy(true, { children: true, texture: true });
}
