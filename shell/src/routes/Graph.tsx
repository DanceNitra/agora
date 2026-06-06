import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { useAgent, AgentDetail } from '../context/AgentContext';

const trustColor = (score: number): string => {
  if (score >= 0.7) return '#22c55e';
  if (score >= 0.4) return '#eab308';
  return '#ef4444';
};

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  role: string;
  trustScore: number;
  energyBalance: number;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  type: string;
  weight: number;
}

const Graph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { liveAgents, setSelectedAgent, openAgentByName } = useAgent();
  const [loading, setLoading] = useState(true);

  const nodes: GraphNode[] = liveAgents.map((a) => ({
    id: a.id,
    name: a.name,
    role: a.role,
    trustScore: a.trustScore,
    energyBalance: a.energyBalance,
  }));

  // Build trust edges based on agent relationships
  const links: GraphLink[] = [];
  if (nodes.length >= 2) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        // Random-ish weight based on trust scores
        const weight = (nodes[i].trustScore + nodes[j].trustScore) / 2;
        if (weight > 0.1) {
          links.push({
            source: nodes[i].id,
            target: nodes[j].id,
            type: 'trust',
            weight: Math.max(0.2, weight),
          });
        }
      }
    }
  }

  useEffect(() => {
    setLoading(liveAgents.length === 0);
  }, [liveAgents]);

  // D3 force simulation
  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    svg.selectAll('*').remove();

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
      .data(links)
      .join('line')
      .attr('stroke', '#3a3a3a')
      .attr('stroke-width', (d) => Math.max(1, d.weight * 3))
      .attr('stroke-opacity', 0.6);

    // Nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => 8 + d.trustScore * 8)
      .attr('fill', (d) => trustColor(d.trustScore))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('mouseenter', function (event, d) {
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${d.name}</strong><br/>Role: ${d.role}<br/>Trust: ${(d.trustScore * 100).toFixed(0)}%<br/>Energy: ${Math.round(d.energyBalance)}`,
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
        openAgentByName(d.name);
      });

    // Labels
    const label = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text((d) => d.name)
      .attr('font-size', 11)
      .attr('fill', '#a3a3a3')
      .attr('dx', 16)
      .attr('dy', 4);

    // Force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .on('tick', () => {
        link
          .attr('x1', (d) => (d.source as GraphNode).x!)
          .attr('y1', (d) => (d.source as GraphNode).y!)
          .attr('x2', (d) => (d.target as GraphNode).x!)
          .attr('y2', (d) => (d.target as GraphNode).y!);
        node
          .attr('cx', (d) => d.x!)
          .attr('cy', (d) => d.y!);
        label
          .attr('x', (d) => d.x!)
          .attr('y', (d) => d.y!);
      });

    // Drag
    const drag = d3.drag<SVGCircleElement, GraphNode>()
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
  }, [liveAgents]);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🕸️ Agent Graph</h2>
      <div style={styles.legend}>
        <span style={{ color: '#22c55e' }}>● High trust (≥70%)</span>
        <span style={{ color: '#eab308' }}>● Medium (40–69%)</span>
        <span style={{ color: '#ef4444' }}>● Low (&lt;40%)</span>
        <span style={{ color: '#6b7280' }}>Size = trust score</span>
        <span style={{ color: '#6b7280' }}>Click = detail panel</span>
      </div>
      <div style={styles.svgWrapper}>
        {loading ? (
          <div style={styles.loading}>Waiting for agents…</div>
        ) : (
          <svg ref={svgRef} style={styles.svg} />
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflow: 'hidden' },
  loading: { textAlign: 'center', marginTop: '80px', color: '#6b7280', fontSize: '16px' },
  title: { margin: '12px 16px 8px', fontSize: '18px', fontWeight: 700, color: '#fbbf24' },
  legend: { display: 'flex', gap: '16px', padding: '0 16px 8px', fontSize: '12px', flexWrap: 'wrap' },
  svgWrapper: { flex: 1, position: 'relative', overflow: 'hidden' },
  svg: { width: '100%', height: '100%', display: 'block' },
};

export default Graph;
