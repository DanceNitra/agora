import { useEffect, useRef, useCallback } from 'react';

// ═══════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════

export interface WSEvent {
  type: string;
  topic?: string;
  payload: Record<string, any>;
  timestamp?: string;
}

export interface WSTickUpdate {
  tick: number;
  agents: number;
  total_energy?: number;
  thinking_agents?: number;
}

export interface WSThoughtUpdate {
  agent_id: string;
  role: string;
  tier?: string;
  action: string;
  insight?: string;
  trust?: number;
  trust_raw?: number;
  energy_cost?: number;
}

export interface WSCSDAlert {
  metric: string;
  severity: string;
  current: number;
  baseline_mean: number;
  z_score: number;
  message: string;
}

export interface WSEpochUpdate {
  epoch: number;
  metrics?: Record<string, any>;
  timestamp?: string;
}

export interface WSHelpRequest {
  requester: string;
  helper: string;
  problem: string;
  description?: string;
}

// ═══════════════════════════════════════════
// HOOK
// ═══════════════════════════════════════════

interface UseWebSocketOptions {
  onEvent?: (event: WSEvent) => void;
  onThought?: (thought: WSThoughtUpdate) => void;
  onHeartbeat?: (hb: WSTickUpdate) => void;
  onCSDAlert?: (alert: WSCSDAlert) => void;
  onEpochUpdate?: (epoch: WSEpochUpdate) => void;
  onHelpRequest?: (req: WSHelpRequest) => void;
  onHelpAccepted?: (req: WSHelpRequest) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  connected: boolean;
  lastEvent: WSEvent | null;
  subscribe: (topics: string[]) => void;
  unsubscribe: (topics: string[]) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    onEvent,
    onThought,
    onHeartbeat,
    onCSDAlert,
    onEpochUpdate,
    onHelpRequest,
    onHelpAccepted,
    onError,
    enabled = true,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectedRef = useRef<boolean>(false);
  const lastEventRef = useRef<WSEvent | null>(null);

  const getWsUrl = useCallback(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}/ws`;
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(getWsUrl());

      ws.onopen = () => {
        connectedRef.current = true;
        // Subscribe to all events on connect
        ws.send(JSON.stringify({ type: 'subscribe', topics: ['all'] }));
      };

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          const eventType = data.type || '';
          const eventTopic = data.topic || '';
          const payload = data.payload || {};

          const event: WSEvent = {
            type: eventType,
            topic: eventTopic,
            payload,
            timestamp: data.timestamp || new Date().toISOString(),
          };
          lastEventRef.current = event;

          // Generic callback
          onEvent?.(event);

          // Typed callbacks
          if (eventType === 'agent_thought' && onThought) {
            onThought(payload as WSThoughtUpdate);
          } else if (eventType === 'heartbeat' && onHeartbeat) {
            onHeartbeat(payload as WSTickUpdate);
          } else if (eventType === 'csd_alert' && onCSDAlert) {
            onCSDAlert(payload as WSCSDAlert);
          } else if (eventType === 'epoch_update' && onEpochUpdate) {
            onEpochUpdate(payload as WSEpochUpdate);
          } else if (eventType === 'agent_help_request' && onHelpRequest) {
            onHelpRequest(payload as WSHelpRequest);
          } else if (eventType === 'agent_help_accepted' && onHelpAccepted) {
            onHelpAccepted(payload as WSHelpRequest);
          }
        } catch (e) {
          // Non-JSON messages are ignored
        }
      };

      ws.onclose = () => {
        connectedRef.current = false;
        wsRef.current = null;
        // Auto-reconnect after 3 seconds
        reconnectRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        const errMsg = 'WebSocket connection error';
        onError?.(errMsg);
        ws.close();
      };

      wsRef.current = ws;
    } catch (e: any) {
      onError?.(`WebSocket init error: ${e.message}`);
      // Retry
      reconnectRef.current = setTimeout(connect, 5000);
    }
  }, [getWsUrl, enabled, onEvent, onThought, onHeartbeat, onCSDAlert, onEpochUpdate, onHelpRequest, onHelpAccepted, onError]);

  const disconnect = useCallback(() => {
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null; // Prevent reconnect
      wsRef.current.close();
      wsRef.current = null;
    }
    connectedRef.current = false;
  }, []);

  const subscribe = useCallback((topics: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', topics }));
    }
  }, []);

  const unsubscribe = useCallback((topics: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', topics }));
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }
    return disconnect;
  }, [enabled, connect, disconnect]);

  return {
    connected: connectedRef.current,
    lastEvent: lastEventRef.current,
    subscribe,
    unsubscribe,
  };
}

export default useWebSocket;
