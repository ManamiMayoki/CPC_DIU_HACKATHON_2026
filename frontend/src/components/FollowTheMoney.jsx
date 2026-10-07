import { useState, useEffect, useRef, useMemo } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ArrowRight,
  ArrowUpRight,
  ArrowDownLeft,
  X,
  Sparkles,
  Info
} from 'lucide-react';

export default function FollowTheMoney({
  initialNodes = [],
  initialEdges = [],
  selectedAccountId,
  onSelectAccount,
}) {
  const containerRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const [activeAccountInput, setActiveAccountInput] = useState(selectedAccountId || 'ACC_MULE_HUB');
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [hopsFilter, setHopsFilter] = useState(1); // 1-hop or 2-hop
  const [riskFilter] = useState('ALL'); // ALL, ELEVATED, PATTERNS_ONLY

  // Sync selectedAccountId from prop
  useEffect(() => {
    if (selectedAccountId) {
      // Keep the local search box in sync when another view selects an account.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveAccountInput(selectedAccountId);
      const found = initialNodes.find(n => n.id === selectedAccountId);
      if (found) setSelectedNode(found);
    }
  }, [selectedAccountId, initialNodes]);

  // Determine current center/target account
  const targetId = activeAccountInput || 'ACC_MULE_HUB';
  const targetNode = useMemo(() => {
    return initialNodes.find(n => n.id.toLowerCase() === targetId.toLowerCase()) || initialNodes[0];
  }, [initialNodes, targetId]);

  // Compute neighborhood subgraph (1-hop or 2-hop)
  const { filteredNodes, filteredEdges } = useMemo(() => {
    if (!targetNode) return { filteredNodes: initialNodes.slice(0, 15), filteredEdges: [] };

    const visited = new Set([targetNode.id]);
    let frontier = new Set([targetNode.id]);

    for (let h = 0; h < hopsFilter; h++) {
      const nextFrontier = new Set();
      for (const e of initialEdges) {
        if (frontier.has(e.source)) nextFrontier.add(e.target);
        if (frontier.has(e.target)) nextFrontier.add(e.source);
      }
      for (const id of nextFrontier) visited.add(id);
      frontier = nextFrontier;
    }

    let subNodes = initialNodes.filter(n => visited.has(n.id));

    if (riskFilter === 'ELEVATED') {
      subNodes = subNodes.filter(n => n.id === targetNode.id || n.risk_level !== 'LOW');
    } else if (riskFilter === 'PATTERNS_ONLY') {
      subNodes = subNodes.filter(n => n.id === targetNode.id || (n.patterns && n.patterns.length > 0));
    }

    const visibleNodeIds = new Set(subNodes.map(n => n.id));
    const subEdges = initialEdges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));

    return { filteredNodes: subNodes, filteredEdges: subEdges };
  }, [initialNodes, initialEdges, targetNode, hopsFilter, riskFilter]);

  // Set selected node to target node if none is selected
  useEffect(() => {
    if (targetNode && (!selectedNode || !filteredNodes.find(n => n.id === selectedNode.id))) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedNode(targetNode);
    }
  }, [targetNode, filteredNodes, selectedNode]);

  // Calculate layout coordinates for nodes (Radial / Force-inspired centered on target)
  const nodePositions = useMemo(() => {
    const positions = new Map();
    const width = 850;
    const height = 580;
    const centerX = width / 2;
    const centerY = height / 2;

    if (!targetNode) return positions;

    // Target node at center
    positions.set(targetNode.id, { x: centerX, y: centerY });

    // Other nodes in concentric orbits
    const otherNodes = filteredNodes.filter(n => n.id !== targetNode.id);

    // Classify incoming senders vs outgoing receivers
    const senders = [];
    const receivers = [];
    const others = [];

    otherNodes.forEach(node => {
      const isSender = filteredEdges.some(e => e.source === node.id && e.target === targetNode.id);
      const isReceiver = filteredEdges.some(e => e.target === node.id && e.source === targetNode.id);
      if (isSender && !isReceiver) senders.push(node);
      else if (isReceiver && !isSender) receivers.push(node);
      else others.push(node);
    });

    // Layout senders on the left arc
    senders.forEach((node, i) => {
      const angle = Math.PI - 0.7 + (1.4 * (i + 0.5)) / Math.max(1, senders.length);
      const r = 210 + (i % 2) * 45;
      positions.set(node.id, {
        x: centerX + Math.cos(angle) * r,
        y: centerY + Math.sin(angle) * r,
      });
    });

    // Layout receivers on the right arc
    receivers.forEach((node, i) => {
      const angle = -0.7 + (1.4 * (i + 0.5)) / Math.max(1, receivers.length);
      const r = 210 + (i % 2) * 45;
      positions.set(node.id, {
        x: centerX + Math.cos(angle) * r,
        y: centerY + Math.sin(angle) * r,
      });
    });

    // Layout cyclic/interconnected nodes on top/bottom
    others.forEach((node, i) => {
      const angle = (i % 2 === 0 ? -1.57 : 1.57) + (i * 0.4);
      const r = 190 + (i % 3) * 40;
      positions.set(node.id, {
        x: centerX + Math.cos(angle) * r,
        y: centerY + Math.sin(angle) * r,
      });
    });

    return positions;
  }, [filteredNodes, filteredEdges, targetNode]);

  // Handle Search Submission
  const handleAccountSubmit = (e) => {
    e.preventDefault();
    const clean = activeAccountInput.trim();
    if (!clean) return;

    const matched = initialNodes.find(n => n.id.toLowerCase() === clean.toLowerCase());
    if (matched) {
      setSelectedNode(matched);
      if (onSelectAccount) onSelectAccount(matched.id);
    } else {
      alert(`Account '${clean}' not found in the transaction universe. Try one of the demo accounts!`);
    }
  };

  // Node Color Helper based on visual states:
  // NORMAL: slate, MEDIUM: amber, HIGH: red, CRITICAL: bright red glow, SELECTED: neon green outline
  const getNodeFill = (node) => {
    if (node.risk_level === 'CRITICAL') return '#DC2626';
    if (node.risk_level === 'HIGH') return '#EF4444';
    if (node.risk_level === 'MEDIUM') return '#F59E0B';
    return '#475569';
  };

  // Pan and drag handlers
  const handleMouseDown = (e) => {
    if (e.target.tagName === 'circle' || e.target.tagName === 'text' || e.target.tagName === 'path') {
      return; // let click events work on nodes
    }
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 390px',
      gap: '24px',
      maxWidth: '1480px',
      margin: '0 auto',
      padding: '24px'
    }}>
      {/* Left: Main Network Visualization Canvas */}
      <div className="glass-panel" style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '20px',
        overflow: 'hidden',
        minHeight: '660px',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        {/* Canvas Top Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          background: 'rgba(5, 7, 11, 0.7)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          zIndex: 10,
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          {/* Target Account Search Bar */}
          <form onSubmit={handleAccountSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                value={activeAccountInput}
                onChange={(e) => setActiveAccountInput(e.target.value)}
                placeholder="Enter Account ID..."
                className="input-fintech"
                style={{ width: '220px', padding: '8px 16px', fontSize: '0.86rem', fontFamily: 'var(--font-mono)' }}
              />
            </div>
            <button type="submit" className="btn-primary" style={{ padding: '8px 18px', fontSize: '0.84rem' }}>
              <span>Follow the Money</span>
              <ArrowRight size={15} />
            </button>
          </form>

          {/* Subgraph Controls (Hops & Risk Filters) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '9999px',
              padding: '3px',
              border: '1px solid rgba(255, 255, 255, 0.08)'
            }}>
              <button
                onClick={() => setHopsFilter(1)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  border: 'none',
                  fontSize: '0.74rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  background: hopsFilter === 1 ? 'var(--primary-neon)' : 'transparent',
                  color: hopsFilter === 1 ? '#05070B' : 'var(--text-secondary)',
                  fontWeight: hopsFilter === 1 ? 700 : 500
                }}
              >
                1-Hop
              </button>
              <button
                onClick={() => setHopsFilter(2)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  border: 'none',
                  fontSize: '0.74rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  background: hopsFilter === 2 ? 'var(--primary-neon)' : 'transparent',
                  color: hopsFilter === 2 ? '#05070B' : 'var(--text-secondary)',
                  fontWeight: hopsFilter === 2 ? 700 : 500
                }}
              >
                2-Hops
              </button>
            </div>

            {/* Zoom / Pan Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <button onClick={() => setZoom(z => Math.min(z + 0.15, 2.5))} className="btn-icon" title="Zoom In">
                <ZoomIn size={16} />
              </button>
              <button onClick={() => setZoom(z => Math.max(z - 0.15, 0.5))} className="btn-icon" title="Zoom Out">
                <ZoomOut size={16} />
              </button>
              <button onClick={resetView} className="btn-icon" title="Reset View">
                <RotateCcw size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Legend Ribbon */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '8px 20px',
          background: 'rgba(13, 17, 26, 0.5)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: '0.74rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)'
        }}>
          <span>VISUAL STATES:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#475569' }} />
            <span>Normal</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#F59E0B' }} />
            <span>Medium Risk</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#EF4444' }} />
            <span>High Risk</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#DC2626', boxShadow: '0 0 8px #DC2626' }} />
            <span>Critical Hub</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '11px', height: '11px', borderRadius: '50%', border: '2px solid #B8FF3D' }} />
            <span style={{ color: '#B8FF3D' }}>Selected Target</span>
          </div>
        </div>

        {/* SVG Network Graph Canvas */}
        <div 
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            flex: 1,
            position: 'relative',
            cursor: isDragging ? 'grabbing' : 'grab',
            overflow: 'hidden',
            userSelect: 'none',
            background: 'radial-gradient(circle at 50% 50%, rgba(13, 21, 38, 0.8) 0%, rgba(5, 7, 11, 0.95) 100%)'
          }}
        >
          <svg 
            width="100%" 
            height="100%" 
            viewBox="0 0 850 580"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '50% 50%',
              transition: isDragging ? 'none' : 'transform 0.1s ease-out'
            }}
          >
            <defs>
              {/* Arrow Marker for Directed Edges */}
              <marker id="arrow" viewBox="0 -5 10 10" refX="24" refY="0" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,-5L10,0L0,5" fill="rgba(184, 255, 61, 0.6)" />
              </marker>
              <marker id="arrow-suspicious" viewBox="0 -5 10 10" refX="24" refY="0" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M0,-5L10,0L0,5" fill="#EF4444" />
              </marker>
              <marker id="arrow-normal" viewBox="0 -5 10 10" refX="22" refY="0" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,-5L10,0L0,5" fill="rgba(255, 255, 255, 0.3)" />
              </marker>

              {/* Glowing Filters */}
              <filter id="glow-target" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              <filter id="glow-critical" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background Grid Pattern */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
            </pattern>
            <rect width="850" height="580" fill="url(#grid)" />

            {/* Draw Directed Edges */}
            {filteredEdges.map((edge) => {
              const src = nodePositions.get(edge.source);
              const dst = nodePositions.get(edge.target);
              if (!src || !dst) return null;

              const isSuspicious = edge.is_suspicious || (edge.shared_patterns && edge.shared_patterns.length > 0);
              const isSelected = selectedEdge && selectedEdge.id === edge.id;
              const isHovered = hoveredEdge && hoveredEdge.id === edge.id;

              // Arc curve calculation for bi-directional or clean routing
              const dx = dst.x - src.x;
              const dy = dst.y - src.y;
              const dr = Math.sqrt(dx * dx + dy * dy);

              return (
                <g key={edge.id} onClick={() => setSelectedEdge(edge)} style={{ cursor: 'pointer' }}>
                  <path
                    d={`M ${src.x} ${src.y} A ${dr * 1.2} ${dr * 1.2} 0 0 1 ${dst.x} ${dst.y}`}
                    fill="none"
                    stroke={
                      isSelected ? '#B8FF3D' :
                      isHovered ? '#FFFFFF' :
                      isSuspicious ? 'rgba(239, 68, 68, 0.8)' :
                      'rgba(255, 255, 255, 0.22)'
                    }
                    strokeWidth={isSelected ? 3.5 : isSuspicious ? 2.4 : 1.4}
                    strokeDasharray={isSuspicious ? '5 3' : 'none'}
                    markerEnd={isSuspicious ? 'url(#arrow-suspicious)' : 'url(#arrow-normal)'}
                    onMouseEnter={() => setHoveredEdge(edge)}
                    onMouseLeave={() => setHoveredEdge(null)}
                  />

                  {/* Flowing animated dot along edge */}
                  {isSuspicious && (
                    <circle r="3.5" fill="#EF4444">
                      <animateMotion
                        path={`M ${src.x} ${src.y} A ${dr * 1.2} ${dr * 1.2} 0 0 1 ${dst.x} ${dst.y}`}
                        dur="1.8s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}
                </g>
              );
            })}

            {/* Draw Nodes */}
            {filteredNodes.map((node) => {
              const pos = nodePositions.get(node.id);
              if (!pos) return null;

              const isTarget = targetNode && node.id === targetNode.id;
              const isSelected = selectedNode && selectedNode.id === node.id;
              const nodeFill = getNodeFill(node);
              const radius = isTarget ? 20 : node.patterns?.length > 0 ? 15 : 12;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => {
                    setSelectedNode(node);
                    if (onSelectAccount) onSelectAccount(node.id);
                  }}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer pulse for Target or Critical */}
                  {(isTarget || node.risk_level === 'CRITICAL') && (
                    <circle
                      r={radius + 8}
                      fill="none"
                      stroke={isTarget ? '#B8FF3D' : '#EF4444'}
                      strokeWidth="2"
                      opacity="0.4"
                    >
                      <animate attributeName="r" values={`${radius + 5};${radius + 15};${radius + 5}`} dur="2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.7;0.1;0.7" dur="2s" repeatCount="indefinite" />
                    </circle>
                  )}

                  {/* Selection Ring */}
                  {isSelected && (
                    <circle
                      r={radius + 5}
                      fill="none"
                      stroke="#B8FF3D"
                      strokeWidth="2.5"
                      filter="url(#glow-target)"
                    />
                  )}

                  {/* Main Node Circle */}
                  <circle
                    r={radius}
                    fill={nodeFill}
                    stroke={isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.3)'}
                    strokeWidth={isSelected ? 2.5 : 1.2}
                    filter={node.risk_level === 'CRITICAL' ? 'url(#glow-critical)' : 'none'}
                  />

                  {/* Inner Node Pip */}
                  <circle r={radius * 0.35} fill="#FFFFFF" opacity="0.9" />

                  {/* Node Label Below */}
                  <text
                    y={radius + 14}
                    textAnchor="middle"
                    fill={isSelected ? '#B8FF3D' : '#FFFFFF'}
                    fontSize="11"
                    fontFamily="var(--font-mono)"
                    fontWeight={isSelected || isTarget ? '700' : '500'}
                    style={{ textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}
                  >
                    {node.id}
                  </text>

                  {/* Risk Badge Mini Indicator */}
                  <text
                    y={-radius - 5}
                    textAnchor="middle"
                    fill={nodeFill}
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    fontWeight="700"
                  >
                    {node.risk_score}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Hover Tooltip Overlay */}
          {hoveredNode && (
            <div style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              background: 'rgba(13, 17, 26, 0.95)',
              border: '1px solid rgba(184, 255, 61, 0.4)',
              borderRadius: '12px',
              padding: '12px 16px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.8)',
              zIndex: 30,
              minWidth: '220px',
              pointerEvents: 'none'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#FFFFFF', fontSize: '0.88rem' }}>
                  {hoveredNode.id}
                </span>
                <span className={`badge-risk badge-risk-${hoveredNode.risk_level.toLowerCase()}`}>
                  {hoveredNode.risk_level}
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'grid', gap: '3px' }}>
                <div>Risk Score: <strong style={{ color: '#FFFFFF' }}>{hoveredNode.risk_score}</strong> / 100</div>
                <div>Degree: In {hoveredNode.in_degree} • Out {hoveredNode.out_degree}</div>
                <div>Inflow: <strong style={{ color: '#22C55E' }}>৳{hoveredNode.incoming_amount?.toLocaleString()}</strong></div>
                <div>Outflow: <strong style={{ color: '#EF4444' }}>৳{hoveredNode.outgoing_amount?.toLocaleString()}</strong></div>
                {hoveredNode.patterns?.length > 0 && (
                  <div style={{ color: '#F59E0B', marginTop: '4px' }}>
                    Patterns: {hoveredNode.patterns.join(', ')}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Edge Tooltip Overlay */}
          {hoveredEdge && (
            <div style={{
              position: 'absolute',
              bottom: '20px',
              right: '20px',
              background: 'rgba(13, 17, 26, 0.95)',
              border: '1px solid rgba(139, 92, 246, 0.5)',
              borderRadius: '12px',
              padding: '12px 16px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.8)',
              zIndex: 30,
              minWidth: '220px',
              pointerEvents: 'none'
            }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                TRANSACTION TRANSFER
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#B8FF3D', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                ৳{hoveredEdge.amount?.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {hoveredEdge.source} → {hoveredEdge.target}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Tx: {hoveredEdge.transaction_id || 'Aggregated'} • {hoveredEdge.timestamp}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Node/Edge Detail Inspector & AI Summary */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Account Inspector Card */}
        {selectedNode ? (
          <div className="glass-panel" style={{ padding: '22px', border: '1px solid rgba(184, 255, 61, 0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  INSPECTING ENTITY
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                  {selectedNode.id}
                </div>
              </div>
              <span className={`badge-risk badge-risk-${selectedNode.risk_level.toLowerCase()}`}>
                {selectedNode.risk_level} RISK
              </span>
            </div>

            {/* Score & Anomaly Banner */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '12px',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
              border: '1px solid rgba(255, 255, 255, 0.06)'
            }}>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Composite Risk</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: getNodeFill(selectedNode) }}>
                  {selectedNode.risk_score}
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>/100</span>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Isolation Forest</div>
                <div style={{
                  fontSize: '0.86rem',
                  fontWeight: 700,
                  color: selectedNode.is_anomaly ? '#EF4444' : '#22C55E'
                }}>
                  {selectedNode.is_anomaly ? 'Outlier Flagged' : 'Normal Inlier'}
                </div>
              </div>
            </div>

            {/* Financial Flow Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '10px 12px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#22C55E', fontSize: '0.72rem' }}>
                  <ArrowDownLeft size={13} />
                  <span>Total Inflow</span>
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                  ৳{(selectedNode.incoming_amount || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {selectedNode.in_degree || 0} distinct senders
                </div>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '10px 12px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#EF4444', fontSize: '0.72rem' }}>
                  <ArrowUpRight size={13} />
                  <span>Total Outflow</span>
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                  ৳{(selectedNode.outgoing_amount || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {selectedNode.out_degree || 0} distinct receivers
                </div>
              </div>
            </div>

            {/* Detected Patterns */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '8px' }}>
                FLAGGED BEHAVIORAL PATTERNS
              </div>
              {selectedNode.patterns && selectedNode.patterns.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {selectedNode.patterns.map((p) => (
                    <span
                      key={p}
                      style={{
                        background: 'rgba(245, 158, 11, 0.15)',
                        border: '1px solid rgba(245, 158, 11, 0.4)',
                        color: '#F59E0B',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600
                      }}
                    >
                      {p.replace('_', ' ').toUpperCase()}
                    </span>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  No structural topology violations detected.
                </div>
              )}
            </div>

            {/* AI Evidence List from Member 3 */}
            <div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.74rem',
                color: 'var(--primary-neon)',
                fontFamily: 'var(--font-mono)',
                marginBottom: '8px'
              }}>
                <Sparkles size={13} color="#B8FF3D" />
                <span>GROUNDED AUDIT EVIDENCE</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedNode.evidence && selectedNode.evidence.length > 0 ? (
                  selectedNode.evidence.map((ev, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.4,
                        padding: '8px 10px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        borderRadius: '6px',
                        borderLeft: '2px solid var(--primary-neon)'
                      }}
                    >
                      {ev}
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Standard transactional profile verified.
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-panel" style={{ padding: '24px', textAlign: 'center' }}>
            <Info size={28} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
            <div style={{ fontSize: '0.92rem', color: 'var(--text-secondary)' }}>No account selected</div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Click any node on the graph canvas or select from demo scenarios.
            </div>
          </div>
        )}

        {/* Selected Edge Inspector Card */}
        {selectedEdge && (
          <div className="glass-panel" style={{ padding: '18px', border: '1px solid rgba(139, 92, 246, 0.4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: '#8B5CF6' }}>
                SELECTED TRANSFER EDGE
              </span>
              <button onClick={() => setSelectedEdge(null)} className="btn-icon" style={{ padding: '4px' }}>
                <X size={14} />
              </button>
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#B8FF3D', fontFamily: 'var(--font-mono)' }}>
              ৳{selectedEdge.amount?.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#FFFFFF', margin: '4px 0' }}>
              <strong>{selectedEdge.source}</strong> → <strong>{selectedEdge.target}</strong>
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Latest: {selectedEdge.timestamp || '2026-03-01'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
