import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';

interface AgentNode {
  id: string;
  name: string;
  role: string;
  trustScore: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface RelationshipLink {
  source: string;
  target: string;
  type: string;
  weight: number;
}

interface GraphData {
  nodes: AgentNode[];
  links: RelationshipLink[];
}

const trustColor = (score: number): string => {
  if (score >= 0.7) return '#22c55e';   // green — high
  if (score >= 0.4) return '#eab308';   // yellow — medium
  return '#ef4444';                      // red — low
};

const Graph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [data, setData] = useState<GraphData | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentNode | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch graph data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/v1/graph');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: GraphData = await res.json();
        setData(json);
      } catch (err) {
        console.error('Graph fetch failed:', err);
        // Fallback mock data for development
        setData({
          nodes: [
            { id: 'agent-1', name: 'Alpha', role: 'researcher', trustScore: 0.85 },
            { id: 'agent-2', name: 'Beta', role: 'writer', trustScore: 0.92 },
            { id: 'agent-3', name: 'Gamma', role: 'critic', trustScore: 0.45 },
            { id: 'agent-4', name: 'Delta', role: 'analyst', trustScore: 0.3 },
            { id: 'agent-5', name: 'Epsilon', role: 'explorer', trustScore: 0.72 },
          ],
          links: [
            { source: 'agent-1', target: 'agent-2', type: 'collaboration', weight: 1 },
            { source: 'agent-1', target: 'agent-3', type: 'critique', weight: 0.5 },
            { source: 'agent-2', target: 'agent-4', type: 'report', weight: 0.8 },
            { source: 'agent-3', target: 'agent-5', type: 'review', weight: 0.6 },
            { source: 'agent-4', target: 'agent-5', type: 'knowledge', weight: 0.4 },
          ],
        });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // D3 force simulation
  useEffect(() => {
    if (!svgRef.current || !data) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Clear previous
    svg.selectAll('*').remove();

    // Zoom / pan
    const g = svg.append('g');
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Tooltip
    const tooltip = d3.select(svgRef.current.parentElement!)
      .append('div')
      .attr('class', 'graph-tooltip')
      .style('position', 'absolute')
      .style('background', '#2a2a2a')
      .style('color', '#d4d4d4')
      .style('border', '1px solid #3a3a3a')
      .style('border-radius', '6px')
      .style('padding', '8px 12px')
      .style('font-size', '13px')
      .style('pointer-events', 'none')
      .style('opacity', 0);

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#3a3a3a')
      .attr('stroke-width', (d) => Math.max(1, d.weight * 2))
      .attr('stroke-opacity', 0.6);

    // Nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .join('circle')
      .attr('r', 12)
      .attr('fill', (d) => trustColor(d.trustScore))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('mouseenter', function (event, d) {
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${d.name}</strong><br/>Role: ${d.role}<br/>Trust: ${(d.trustScore * 100).toFixed(0)}%`,
          )
          .style('left', `${event.pageX + 12}px`)
          .style('top', `${event.pageY - 28}px`);
        d3.select(this).attr('stroke', '#fbbf24').attr('stroke-width', 2.5);
      })
      .on('mousemove', function (event) {
        tooltip
          .style('left', `${event.pageX + 12}px`)
          .style('top', `${event.pageY - 28}px`);
      })
      .on('mouseleave', function () {
        tooltip.style('opacity', 0);
        d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
      })
      .on('click', function (event, d) {
        setSelectedAgent(d);
      });

    // Labels
    const label = g.append('g')
      .selectAll('text')
      .data(data.nodes)
      .join('text')
      .text((d) => d.name)
      .attr('font-size', 11)
      .attr('fill', '#a3a3a3')
      .attr('dx', 16)
      .attr('dy', 4);

    // Force simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id((d: any) => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .on('tick', () => {
        link
          .attr('x1', (d: any) => d.source.x)
          .attr('y1', (d: any) => d.source.y)
          .attr('x2', (d: any) => d.target.x)
          .attr('y2', (d: any) => d.target.y);
        node
          .attr('cx', (d: any) => d.x)
          .attr('cy', (d: any) => d.y);
        label
          .attr('x', (d: any) => d.x)
          .attr('y', (d: any) => d.y);
      });

    // Drag
    const drag = d3.drag<SVGCircleElement, AgentNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
    node.call(drag as any);

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [data]);

  const handleCloseDetail = useCallback(() => setSelectedAgent(null), []);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading graph data…</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🌐 Agent Graph</h2>
      <div style={styles.legend}>
        <span style={{ color: '#22c55e' }}>● High trust (≥70%)</span>
        <span style={{ color: '#eab308' }}>● Medium (40–69%)</span>
        <span style={{ color: '#ef4444' }}>● Low (&lt;40%)</span>
      </div>
      <div style={styles.svgWrapper}>
        <svg ref={svgRef} style={styles.svg} />

        {/* Agent detail panel */}
        {selectedAgent && (
          <div style={styles.detailPanel}>
            <div style={styles.detailHeader}>
              <strong>{selectedAgent.name}</strong>
              <button onClick={handleCloseDetail} style={styles.closeBtn}>✕</button>
            </div>
            <div style={styles.detailRow}><span>ID:</span> {selectedAgent.id}</div>
            <div style={styles.detailRow}><span>Role:</span> {selectedAgent.role}</div>
            <div style={styles.detailRow}>
              <span>Trust:</span>
              <span style={{ color: trustColor(selectedAgent.trustScore) }}>
                {(selectedAgent.trustScore * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#1a1a1a',
    color: '#d4d4d4',
    fontFamily: "'Inter', system-ui, sans-serif",
    overflow: 'hidden',
  },
  loading: {
    textAlign: 'center',
    marginTop: '80px',
    color: '#6b7280',
    fontSize: '16px',
  },
  title: {
    margin: '12px 16px 8px',
    fontSize: '18px',
    fontWeight: 700,
    color: '#fbbf24',
  },
  legend: {
    display: 'flex',
    gap: '16px',
    padding: '0 16px 8px',
    fontSize: '12px',
  },
  svgWrapper: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
  },
  svg: {
    width: '100%',
    height: '100%',
    display: 'block',
  },
  detailPanel: {
    position: 'absolute',
    top: 12,
    right: 12,
    background: '#2a2a2a',
    border: '1px solid #3a3a3a',
    borderRadius: '8px',
    padding: '14px',
    minWidth: '180px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
    fontSize: '15px',
    color: '#fbbf24',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#a3a3a3',
    cursor: 'pointer',
    fontSize: '16px',
  },
  detailRow: {
    fontSize: '13px',
    marginBottom: '6px',
  },
};

export default Graph;
