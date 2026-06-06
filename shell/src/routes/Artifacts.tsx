import React, { useState, useEffect, useCallback } from 'react';

interface ArtifactSummary {
  total_artifacts: number;
  total_bytes: number;
  by_type: { type: string; count: number }[];
  by_role: { role: string; count: number }[];
}

interface Artifact {
  id: number;
  agent_id: string;
  role: string;
  title: string;
  artifact_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  is_published: boolean;
  difficulty?: number;
  task_id?: number;
  summary?: string;
}

const TYPE_COLORS: Record<string, string> = {
  analysis: '#88ccff',
  writing: '#44ff88',
  review: '#ffcc44',
  research: '#cc88ff',
  exploration: '#ff8844',
  general: '#aaaaaa',
};

const TYPE_ICONS: Record<string, string> = {
  analysis: '📊',
  writing: '📝',
  review: '🔍',
  research: '🧬',
  exploration: '🧭',
  general: '📄',
};

const Artifacts: React.FC = () => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [summary, setSummary] = useState<ArtifactSummary | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const url = typeFilter
        ? `/api/v1/artifacts/?artifact_type=${typeFilter}&limit=50`
        : '/api/v1/artifacts/?limit=50';
      const [artRes, sumRes] = await Promise.all([
        fetch(url),
        fetch('/api/v1/artifacts/stats/summary'),
      ]);
      if (artRes.ok) {
        const json = await artRes.json();
        setArtifacts(json.artifacts);
        setTotal(json.total);
      }
      if (sumRes.ok) {
        setSummary(await sumRes.json());
      }
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const typeCounts = summary?.by_type.reduce<Record<string, number>>((acc, t) => {
    acc[t.type] = t.count;
    return acc;
  }, {}) ?? {};

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={{ textAlign: 'center', color: '#525252', marginTop: 60 }}>Loading artifacts…</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>📦 Artifacts</h2>
      <p style={styles.subtitle}>Agent-produced documents, reports, and audit trails</p>

      {/* Summary cards */}
      {summary && (
        <div style={styles.cardRow}>
          <div style={styles.card}>
            <div style={{ ...styles.cardValue, color: '#fbbf24' }}>{summary.total_artifacts}</div>
            <div style={styles.cardLabel}>Total Artifacts</div>
          </div>
          <div style={styles.card}>
            <div style={{ ...styles.cardValue, color: '#44ff88' }}>
              {summary.total_bytes > 1024
                ? `${(summary.total_bytes / 1024).toFixed(1)}KB`
                : `${summary.total_bytes}B`}
            </div>
            <div style={styles.cardLabel}>Total Size</div>
          </div>
          <div style={styles.card}>
            <div style={{ ...styles.cardValue, color: '#88ccff' }}>
              {Object.keys(typeCounts).length}
            </div>
            <div style={styles.cardLabel}>Types</div>
          </div>
        </div>
      )}

      {/* Type breakdown */}
      {summary && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>📊 By Type</h3>
          <div style={styles.typeGrid}>
            {summary.by_type.map((t) => (
              <button
                key={t.type}
                onClick={() => setTypeFilter(typeFilter === t.type ? '' : t.type)}
                style={{
                  ...styles.typeBtn,
                  borderColor: typeFilter === t.type ? TYPE_COLORS[t.type] || '#fbbf24' : '#3a3a3a',
                  background: typeFilter === t.type
                    ? `${TYPE_COLORS[t.type] || '#fbbf24'}22`
                    : '#2a2a2a',
                }}
              >
                <span style={{ fontSize: 16 }}>{TYPE_ICONS[t.type] || '📄'}</span>
                <span style={{ fontWeight: 600 }}>{t.type}</span>
                <span style={{ color: '#6b7280', fontSize: 11 }}>{t.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Artifact list */}
      <div style={styles.listSection}>
        <h3 style={styles.listTitle}>
          Recent Artifacts ({total})
          {typeFilter && (
            <span style={{ marginLeft: 8, color: '#6b7280', fontWeight: 400 }}>
              — filtered: {typeFilter}
              <button onClick={() => setTypeFilter('')} style={styles.clearBtn}>✕</button>
            </span>
          )}
        </h3>

        {artifacts.length === 0 && (
          <div style={styles.emptyText}>No artifacts yet. Task pipeline generates them on completion.</div>
        )}

        <div style={styles.artifactList}>
          {artifacts.map((art) => (
            <ArtifactCard key={art.id} artifact={art} />
          ))}
        </div>
      </div>
    </div>
  );
};

const ArtifactCard: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  const [expanded, setExpanded] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const toggleExpand = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (content === null) {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/artifacts/${artifact.id}`);
        if (res.ok) {
          const json = await res.json();
          setContent(json.content || '(empty)');
        } else {
          setContent('(failed to load)');
        }
      } catch {
        setContent('(error loading)');
      } finally {
        setLoading(false);
      }
    }
  };

  const typeColor = TYPE_COLORS[artifact.artifact_type] || '#aaaaaa';
  const typeIcon = TYPE_ICONS[artifact.artifact_type] || '📄';

  return (
    <div style={styles.artifactCard}>
      <div style={styles.artifactHeader} onClick={toggleExpand} className="artifact-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
          <span style={{ fontSize: 16 }}>{typeIcon}</span>
          <div style={{ flex: 1 }}>
            <div style={styles.artifactTitle}>{artifact.title}</div>
            <div style={styles.artifactMeta}>
              <span style={{ color: typeColor }}>{artifact.artifact_type}</span>
              {' · '}
              <span>{artifact.role || 'agent'}</span>
              {' · '}
              <span style={{ color: '#6b7280' }}>{new Date(artifact.created_at).toLocaleString()}</span>
              {' · '}
              <span style={{ color: '#6b7280' }}>
                {artifact.size_bytes > 1024
                  ? `${(artifact.size_bytes / 1024).toFixed(1)}KB`
                  : `${artifact.size_bytes}B`}
              </span>
            </div>
          </div>
        </div>
        <span style={{ color: '#6b7280', fontSize: 11 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div style={styles.artifactContent}>
          {loading ? (
            <div style={{ color: '#6b7280', fontStyle: 'italic' }}>Loading content…</div>
          ) : (
            <pre style={styles.contentPre}>{content}</pre>
          )}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  title: { fontSize: '18px', fontWeight: 700, color: '#fbbf24', margin: '12px 0 0' },
  subtitle: { fontSize: '13px', color: '#6b7280', margin: '4px 0 16px' },
  cardRow: { display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' },
  card: { flex: '1 1 100px', background: '#2a2a2a', borderRadius: '8px', padding: '14px', textAlign: 'center', border: '1px solid #3a3a3a' },
  cardValue: { fontSize: '24px', fontWeight: 700 },
  cardLabel: { fontSize: '12px', color: '#6b7280', marginTop: '4px' },
  section: { background: '#2a2a2a', borderRadius: '8px', padding: '12px', marginBottom: '12px', border: '1px solid #3a3a3a' },
  sectionTitle: { fontSize: '14px', fontWeight: 600, margin: '0 0 10px', color: '#d4d4d4' },
  typeGrid: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  typeBtn: { display: 'flex', alignItems: 'center', gap: '6px', border: '1px solid', borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontSize: '12px', color: '#d4d4d4', transition: 'all 0.15s' },
  listSection: { flex: 1 },
  listTitle: { fontSize: '14px', fontWeight: 600, margin: '0 0 10px', color: '#d4d4d4' },
  clearBtn: { background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', marginLeft: 6, fontSize: 13 },
  emptyText: { color: '#525252', fontSize: '13px', fontStyle: 'italic', padding: '20px 0', textAlign: 'center' },
  artifactList: { display: 'flex', flexDirection: 'column', gap: '6px' },
  artifactCard: { background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px', overflow: 'hidden' },
  artifactHeader: { display: 'flex', alignItems: 'center', padding: '10px 12px', cursor: 'pointer', transition: 'background 0.1s' },
  artifactTitle: { fontWeight: 600, fontSize: '13px', color: '#d4d4d4' },
  artifactMeta: { fontSize: '11px', color: '#a3a3a3', marginTop: '2px' },
  artifactContent: { borderTop: '1px solid #3a3a3a', padding: '10px 12px', maxHeight: 400, overflowY: 'auto', background: '#1a1a1a' },
  contentPre: { fontSize: '12px', lineHeight: 1.5, color: '#d4d4d4', whiteSpace: 'pre-wrap', fontFamily: "'Fira Code', 'JetBrains Mono', monospace", margin: 0 },
};

export default Artifacts;
