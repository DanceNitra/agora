import { useState, useEffect, useRef, useCallback } from 'react';

interface SSEOptions {
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
}

interface SSEState<T> {
  connected: boolean;
  lastEvent: T | null;
  error: string | null;
}

/**
 * React hook for Server-Sent Events with auto-reconnect.
 *
 * @template T - The expected shape of parsed event data
 * @param url - SSE endpoint URL (relative or absolute)
 * @param options - Configuration options
 */
export function useSSE<T = unknown>(
  url: string,
  options: SSEOptions = {},
): SSEState<T> & { close: () => void } {
  const { autoReconnect = true, reconnectDelay = 3000 } = options;

  const [state, setState] = useState<SSEState<T>>({
    connected: false,
    lastEvent: null,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const urlRef = useRef(url);
  urlRef.current = url;

  // Cleanup helper
  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    // Don't connect if unmounted
    if (!mountedRef.current) return;

    // Clean any existing connection
    cleanup();

    try {
      const es = new EventSource(urlRef.current);
      eventSourceRef.current = es;

      es.onopen = () => {
        if (mountedRef.current) {
          setState((prev) => ({ ...prev, connected: true, error: null }));
        }
      };

      // Handle named events — if the server sends events with a specific `event:` field,
      // we'll handle all via onmessage as a fallback too.
      es.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data) as T;
          setState((prev) => ({
            ...prev,
            lastEvent: data,
            error: null,
          }));
        } catch {
          // If data isn't JSON, pass the raw string
          setState((prev) => ({
            ...prev,
            lastEvent: event.data as unknown as T,
            error: null,
          }));
        }
      };

      es.onerror = () => {
        if (!mountedRef.current) return;

        setState((prev) => ({
          ...prev,
          connected: false,
          error: 'SSE connection lost',
        }));

        es.close();
        eventSourceRef.current = null;

        if (autoReconnect && mountedRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
    } catch (err: any) {
      if (mountedRef.current) {
        setState((prev) => ({
          ...prev,
          connected: false,
          error: `Failed to create EventSource: ${err.message ?? String(err)}`,
        }));
      }
    }
  }, [autoReconnect, reconnectDelay, cleanup]);

  // Connect on mount, reconnect when url changes
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [connect, cleanup]);

  const close = useCallback(() => {
    mountedRef.current = false;
    cleanup();
    setState({ connected: false, lastEvent: null, error: null });
  }, [cleanup]);

  return { ...state, close };
}

export default useSSE;
