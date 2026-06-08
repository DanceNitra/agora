---
type: handoff
agent: "tg-hermes"
target: "agora-builder"
status: ready-for-implementation
task: "Phase 2 — Connect ESS API to existing Shell UI"
commit: "dc4b175 (current, Phase 1 planning complete)"
created: 2026-06-08
---

## HANDOFF — 2026-06-08 | Phase 2: Connect ESS to Shell

**From:** tg-hermes (planner)
**To:** agora-builder (executor)
**Status:** 🟢 PLANNING → 🟡 READY FOR IMPLEMENTATION
**Depends on:** 1.6 REST API (must exist first — provides `/api/ess/*` endpoints)

---

### Context

The Shell UI already has ALL the components:

| Component | Lines | Status | Need to change? |
|-----------|-------|--------|:----:|
| `Dashboard.tsx` | 465 | ✅ Full agent table, trust bars, energy, economy, health | Add ESS API calls |
| `Timeline.tsx` | 287 | ✅ WebSocket event parser, filters, auto-scroll | Subscribe to `ess:*` topics |
| `Graph.tsx` | 216 | ✅ D3 force simulation, zoom/drag, tooltips | Load trust data from ESS API |
| `GodConsole.tsx` | 1172 | ✅ 7 tabs (agents, violations, OS, controller, health, trust, quests) | Already uses `/api/v1/eval/trust/matrix` — add ESS tab |
| `AgentDetailPanel.tsx` | 240 | ✅ Floating detail panel | Add ESS trust score |
| `AgentContext.tsx` | 224 | ✅ Zustand state with liveAgents, WebSocket | Add ESS fields |
| `useWebSocket.ts` | 178 | ✅ Reconnect, heartbeat, event bus | Already solid |

**Goal:** Don't rewrite the shell. Add a thin ESS integration layer.

---

### Step 1: Add ESS fields to AgentContext — `shell/src/context/AgentContext.tsx`

Find the `AgentDetail` interface and add:

```typescript
export interface AgentDetail {
  id: string;
  name: string;
  role: string;
  trustScore: number;
  energyBalance: number;
  status: string;
  // NEW ESS fields
  tftScore?: number;
  provokabilityScore?: number;
  isStable?: boolean;
}
```

In the `useAgent` hook, add a method to fetch ESS data:

```typescript
const fetchESSTrust = useCallback(async () => {
  const res = await fetch('/api/ess/aggregates');
  if (!res.ok) return;
  const data = await res.json();
  // Just ping the API to confirm it's alive
  setLastEvent('ess-ready');
}, []);
```

Call it in the mount effect alongside the existing data fetches.

---

### Step 2: Connect Timeline to ESS topics — `shell/src/routes/Timeline.tsx`

Change the WebSocket URL from `/ws` to `/ws/ess` (line 163):

```typescript
// OLD:
const wsUrl = `${protocol}//${window.location.host}/ws`;
// NEW:
const wsUrl = `${protocol}//${window.location.host}/ws/ess`;
```

The existing `parseWsMessage()` function (lines 16-148) already handles:
- `trust_<outcome>` events (lines 19-30) — ESS trust interactions
- `tft_evaluation` events — need to add parser for these

After line 60 (stigmergy_insight handler), add:

```typescript
// ESS TFT evaluation events
if (parsed.type === 'tft_evaluation' && parsed.payload) {
  const p = parsed.payload;
  return {
    id: `tft-${p.agent_id}-${parsed.timestamp}`,
    type: 'trust',
    agentName: p.agent_id || 'unknown',
    message: `🧪 TFT eval: ${p.agent_id || '?'} score=${p.tft_score} (nice=${p.components?.nice}, retaliatory=${p.components?.retaliatory}, forgiving=${p.components?.forgiving}, clear=${p.components?.clear})`,
    timestamp: parsed.timestamp || new Date().toISOString(),
    details: p,
  };
}

// ESS stability events
if (parsed.type === 'provokability_result' && parsed.payload) {
  const p = parsed.payload;
  return {
    id: `prov-${p.agent_id}-${parsed.timestamp}`,
    type: 'alert',
    agentName: p.agent_id || 'unknown',
    message: `${p.is_stable ? '🟢' : '🔴'} Provokability: ${p.agent_id || '?'} → ${(p.provokability_score * 100).toFixed(0)}% ${p.is_stable ? 'ESS-stable' : 'fragile'}`,
    timestamp: parsed.timestamp || new Date().toISOString(),
    details: p,
  };
}
```

---

### Step 3: Wire Graph to ESS trust data — `shell/src/routes/Graph.tsx`

Replace the hardcoded trust scoring (line 43) with a fetch from the ESS API:

```typescript
useEffect(() => {
  const fetchTrust = async () => {
    try {
      const promises = liveAgents.map(async (a) => {
        const res = await fetch(`/api/ess/evaluate/${a.id}`);
        if (!res.ok) return null;
        return res.json();
      });
      const results = (await Promise.all(promises)).filter(Boolean);
      // Merge TFT scores into nodes
      setTftScores(
        results.reduce((acc, r) => {
          acc[r.agent_id] = r;
          return acc;
        }, {} as Record<string, any>)
      );
    } catch { /* ignore */ }
  };
  if (liveAgents.length > 0) fetchTrust();
}, [liveAgents]);
```

Add state at top of component:

```typescript
const [tftScores, setTftScores] = useState<Record<string, any>>({});
```

In the link weight calculation (around line 44), replace the random-ish trust average with real data:

```typescript
// OLD:
const weight = (nodes[i].trustScore + nodes[j].trustScore) / 2;
// NEW:
const tftI = tftScores[nodes[i].id];
const tftJ = tftScores[nodes[j].id];
const weight = tftI && tftJ
  ? (tftI.tft_score + tftJ.tft_score) / 2
  : (nodes[i].trustScore + nodes[j].trustScore) / 2;
```

---

### Step 4: Add ESS tab to GodConsole — `shell/src/routes/GodConsole.tsx`

Add a new tab after line 79:

```typescript
{ id: 'ess', label: 'ESS Protocol', icon: '🔗' },
```

Add a new ESS tab component. Add this after the QuestsTab (near the end of the file, around line 1150):

```typescript
// ═══════════════════════════════════════════
// TAB 8: ESS PROTOCOL
// ═══════════════════════════════════════════

const ESSTab: React.FC<{ npcs: NPC[] }> = ({ npcs }) => {
  const [essData, setEssData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchESS = async () => {
      setLoading(true);
      try {
        const [aggRes, evalRes] = await Promise.all([
          fetch('/api/ess/aggregates'),
          ...npcs.slice(0, 5).map(n => fetch(`/api/ess/evaluate/${n.npc_id}`)),
        ]);
        const agg = aggRes.ok ? await aggRes.json() : null;

        const evals = (await Promise.all(
          npcs.slice(0, 10).map(async (n) => {
            const res = await fetch(`/api/ess/evaluate/${n.npc_id}`);
            if (!res.ok) return null;
            return res.json();
          })
        )).filter(Boolean);

        setEssData({ aggregates: agg, evaluations: evals });
      } catch { /* ignore */ }
      setLoading(false);
    };
    fetchESS();
    const interval = setInterval(fetchESS, 10000);
    return () => clearInterval(interval);
  }, [npcs]);

  if (loading && !essData) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>Loading ESS data…</div>;
  }

  return (
    <div style={styles.tabContent}>
      {/* Aggregate summary */}
      <div style={{ background: '#1f2937', borderRadius: 8, padding: 12, border: '1px solid #374151', marginBottom: 12 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#fbbf24', margin: '0 0 8px' }}>
          📊 ESS Event Store
        </h3>
        {essData?.aggregates?.aggregates?.map((a: any) => (
          <div key={a.type} style={styles.statRow}>
            <span style={{ color: '#d4d4d4', textTransform: 'capitalize' }}>{a.type}</span>
            <span style={{ color: '#22c55e', fontWeight: 600 }}>{a.event_count} events</span>
            <span style={{ color: '#6b7280', fontSize: 11 }}>{a.stream_count} streams</span>
          </div>
        )) || (
          <div style={{ color: '#6b7280', fontSize: 13, fontStyle: 'italic' }}>No ESS data yet</div>
        )}
      </div>

      {/* Agent TFT scores */}
      <div style={{ background: '#1f2937', borderRadius: 8, padding: 12, border: '1px solid #374151' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#fbbf24', margin: '0 0 8px' }}>
          🧪 TFT Compliance & Provokability
        </h3>
        <div style={styles.table}>
          <div style={styles.tableHeader}>
            <span style={{ flex: 1 }}>Agent</span>
            <span style={{ flex: 1, textAlign: 'center' }}>TFT</span>
            <span style={{ flex: 1, textAlign: 'center' }}>Provokability</span>
            <span style={{ flex: 1, textAlign: 'center' }}>Stable</span>
            <span style={{ flex: 1, textAlign: 'center' }}>Interactions</span>
          </div>
          {essData?.evaluations?.map((e: any) => (
            <div key={e.agent_id} style={styles.tableRow}>
              <span style={{ flex: 1, fontWeight: 600, fontSize: 12 }}>{e.agent_id}</span>
              <span style={{ flex: 1, textAlign: 'center', color: e.tft_score >= 0.7 ? '#22c55e' : e.tft_score >= 0.4 ? '#eab308' : '#ef4444' }}>
                {(e.tft_score * 100).toFixed(0)}%
              </span>
              <span style={{ flex: 1, textAlign: 'center', color: e.provokability?.average >= 0.7 ? '#22c55e' : '#eab308' }}>
                {e.provokability ? `${(e.provokability.average * 100).toFixed(0)}%` : '—'}
              </span>
              <span style={{ flex: 1, textAlign: 'center' }}>
                {e.provokability?.is_stable ? '🟢' : '🔴'}
              </span>
              <span style={{ flex: 1, textAlign: 'center', color: '#6b7280' }}>
                {e.interaction_count || 0}
              </span>
            </div>
          ))}
          {(!essData?.evaluations || essData.evaluations.length === 0) && (
            <div style={{ color: '#6b7280', fontSize: 13, fontStyle: 'italic', textAlign: 'center', padding: 16 }}>
              No TFT evaluations yet. Run some agent interactions first.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

Wire into the tab switcher (in `GodConsoleV2` component, at the `activeTab` switch):

```typescript
{activeTab === 'ess' && <ESSTab npcs={npcs} />}
```

---

### Step 5: Update Queue Status

| # | Task | Status | Note |
|---|------|--------|------|
| 2.1 | Trust graph visualization | 🔴 | ✅ UI exists — just connect ESS API |
| 2.2 | Timeline ESS events | 🔴 | ✅ UI exists — change WS URL + add 2 parsers |
| 2.3 | Arena | 🔴 | ✅ UI exists — no ESS changes needed |
| 2.4 | God Console | 🔴 | ✅ UI exists — add `ess` tab |
| 2.5 | Agent detail panel | 🔴 | ✅ UI exists — add TFT/provokability fields |

---

### What NOT to do

- ❌ Don't rewrite any of the existing components — they work
- ❌ Don't add React Router routes — everything connects via existing routes
- ❌ Don't add authentication — internal shell API

---

### Files to Change

| File | Action |
|------|--------|
| `shell/src/context/AgentContext.tsx` | Add ESS fields to AgentDetail, add `fetchESSTrust` method |
| `shell/src/routes/Timeline.tsx` | Change WS to `/ws/ess`, add 2 ESS event parsers |
| `shell/src/routes/Graph.tsx` | Fetch TFT scores, use in link weight calculation |
| `shell/src/routes/GodConsole.tsx` | Add `ess` tab + ESSTab component |
| `planning/ESS-Queue.md` | Mark Phase 2 tasks to indicate UI exists |

---

### What's Next

After implementation:
1. `git add -A && git commit -m "ess: phase-2 — connect ESS API to existing Shell UI"`
2. `git push`
3. Start server + shell, verify ESS tab shows data
4. Move to Phase 2b (framework plugins) or Phase 3 (launch)