import { useState } from 'react';

/**
 * SvgTimelineChart — Custom SVG Chart to display ELO history over time.
 * Accepts `history` array of objects: { case_query, reputation_before, reputation_after, change_amount }
 */
export default function SvgTimelineChart({ history }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  if (!history || history.length === 0) {
    return (
      <div style={{
        height: '220px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--color-text-muted)',
        fontStyle: 'italic',
        fontSize: '0.875rem'
      }}>
        No reputation history records found to plot.
      </div>
    );
  }

  // Build sequential data points (starting ELO, then each post-case ELO)
  const dataPoints = [];
  
  // Point 0: Starting value
  dataPoints.push({
    elo: history[0].reputation_before,
    query: 'Initial Rating',
    delta: 0,
    index: 0
  });

  // Points 1..N: Ratings after each case
  history.forEach((h, idx) => {
    dataPoints.push({
      elo: h.reputation_after,
      query: h.case_query,
      delta: h.change_amount,
      index: idx + 1
    });
  });

  // Chart layout dimensions
  const width = 600;
  const height = 240;
  const paddingLeft = 55;
  const paddingRight = 20;
  const paddingTop = 30;
  const paddingBottom = 40;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  // Find boundaries
  const eloValues = dataPoints.map(d => d.elo);
  let maxElo = Math.max(...eloValues);
  let minElo = Math.min(...eloValues);

  // Maintain a minimum spread of at least 50 ELO points
  const spread = maxElo - minElo;
  if (spread < 50) {
    const pad = (50 - spread) / 2;
    maxElo += pad;
    minElo -= pad;
  } else {
    // Add 10% padding top/bottom
    maxElo += spread * 0.1;
    minElo -= spread * 0.1;
  }

  // Ensure ELO is rounded to clean numbers for grid lines
  maxElo = Math.ceil(maxElo);
  minElo = Math.floor(minElo);

  // Mapping functions
  const getX = (index) => {
    if (dataPoints.length <= 1) return paddingLeft + chartWidth / 2;
    return paddingLeft + (index / (dataPoints.length - 1)) * chartWidth;
  };

  const getY = (elo) => {
    const scale = (elo - minElo) / (maxElo - minElo);
    return paddingTop + chartHeight - scale * chartHeight;
  };

  // Generate SVG path for the line
  let pathD = '';
  dataPoints.forEach((p, i) => {
    const x = getX(i);
    const y = getY(p.elo);
    if (i === 0) {
      pathD = `M ${x} ${y}`;
    } else {
      pathD += ` L ${x} ${y}`;
    }
  });

  // Generate vertical grid lines (steps)
  const verticalGrid = dataPoints.map((p, i) => {
    const x = getX(i);
    return (
      <line
        key={`v-${i}`}
        x1={x}
        y1={paddingTop}
        x2={x}
        y2={paddingTop + chartHeight}
        stroke="rgba(255, 255, 255, 0.05)"
        strokeWidth="1"
      />
    );
  });

  // Generate horizontal grid lines (reputation values)
  const numHorizontalLines = 4;
  const horizontalGrid = [];
  const yLabels = [];
  for (let i = 0; i <= numHorizontalLines; i++) {
    const scale = i / numHorizontalLines;
    const eloVal = minElo + scale * (maxElo - minElo);
    const y = getY(eloVal);
    
    horizontalGrid.push(
      <line
        key={`h-${i}`}
        x1={paddingLeft}
        y1={y}
        x2={width - paddingRight}
        y2={y}
        stroke="rgba(255, 255, 255, 0.06)"
        strokeWidth="1"
        strokeDasharray={i === 0 || i === numHorizontalLines ? "0" : "4 4"}
      />
    );

    yLabels.push(
      <text
        key={`lbl-${i}`}
        x={paddingLeft - 8}
        y={y + 4}
        fill="var(--color-text-muted)"
        fontSize="10px"
        fontFamily="var(--font-mono)"
        textAnchor="end"
      >
        {Math.round(eloVal)}
      </text>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height="100%"
        style={{ overflow: 'visible' }}
      >
        {/* Definition for neon glow effect */}
        <defs>
          <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-indigo)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="var(--color-indigo)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        <g>{verticalGrid}</g>
        <g>{horizontalGrid}</g>
        <g>{yLabels}</g>

        {/* Area fill under the line */}
        {dataPoints.length > 1 && (
          <path
            d={`${pathD} L ${getX(dataPoints.length - 1)} ${paddingTop + chartHeight} L ${getX(0)} ${paddingTop + chartHeight} Z`}
            fill="url(#chart-gradient)"
          />
        )}

        {/* Glow Line */}
        <path
          d={pathD}
          fill="none"
          stroke="var(--color-indigo)"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#neon-glow)"
          style={{ dropShadow: '0 0 10px rgba(108,99,255,0.5)' }}
        />

        {/* Standard Overlay Line */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(255, 255, 255, 0.4)"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points (circles) */}
        {dataPoints.map((p, i) => {
          const x = getX(i);
          const y = getY(p.elo);
          const isHovered = hoveredPoint && hoveredPoint.index === i;
          return (
            <g key={`pt-${i}`}>
              {/* Larger hover target area */}
              <circle
                cx={x}
                cy={y}
                r="12"
                fill="transparent"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
              {/* Visible circle */}
              <circle
                cx={x}
                cy={y}
                r={isHovered ? "6" : "4.5"}
                fill={isHovered ? "#fff" : "var(--color-indigo)"}
                stroke={isHovered ? "var(--color-indigo)" : "#fff"}
                strokeWidth={isHovered ? "3" : "1.5"}
                style={{ pointerEvents: 'none', transition: 'all 0.15s ease' }}
              />
            </g>
          );
        })}

        {/* Axis Titles */}
        <text
          x={paddingLeft + chartWidth / 2}
          y={height - 8}
          fill="var(--color-text-muted)"
          fontSize="10px"
          fontWeight="bold"
          textAnchor="middle"
          letterSpacing="0.05em"
        >
          CASES (CHRONOLOGICAL SEQUENCE)
        </text>
      </svg>

      {/* Hover Tooltip Overlay */}
      {hoveredPoint && (
        <div style={{
          position: 'absolute',
          left: `${(getX(hoveredPoint.index) / width) * 100}%`,
          top: `${(getY(hoveredPoint.elo) / height) * 100 - 15}%`,
          transform: 'translate(-50%, -100%)',
          background: 'rgba(15, 12, 35, 0.92)',
          border: '1px solid var(--color-indigo)',
          borderRadius: '6px',
          padding: '8px 12px',
          color: '#fff',
          fontSize: '0.75rem',
          pointerEvents: 'none',
          zIndex: 10,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5), 0 0 10px rgba(108, 99, 255, 0.25)',
          backdropFilter: 'blur(8px)',
          minWidth: '160px',
          maxWidth: '240px',
          transition: 'all 0.1s ease'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontWeight: 'bold' }}>
            <span>Case #{hoveredPoint.index}</span>
            <span style={{
              color: hoveredPoint.delta > 0 ? 'var(--color-green)' : hoveredPoint.delta < 0 ? 'var(--color-red)' : '#aaa',
              fontFamily: 'var(--font-mono)'
            }}>
              {hoveredPoint.delta > 0 ? `+${hoveredPoint.delta.toFixed(2)}` : hoveredPoint.delta < 0 ? hoveredPoint.delta.toFixed(2) : '0.00'}
            </span>
          </div>
          <div style={{ color: 'var(--color-text-dim)', marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {hoveredPoint.query}
          </div>
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '4px', fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: 'var(--color-indigo)' }}>
            {hoveredPoint.elo.toFixed(2)} ELO
          </div>
        </div>
      )}
    </div>
  );
}
