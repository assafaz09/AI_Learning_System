import type { ProjectStatusSlice } from "../../lib/api";

const COLORS = ["#22c55e", "#f59e0b", "#94a3b8"];

type ProjectDonutProps = {
  slices: ProjectStatusSlice[];
  total: number;
};

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export default function ProjectDonut({ slices, total }: ProjectDonutProps) {
  const size = 160;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 54;
  const stroke = 18;

  if (total === 0) {
    return (
      <div className="progress-donut-empty">
        <p>אין פרויקטים שמורים</p>
        <span className="muted">צרו פרויקט למידה בדף המורה</span>
      </div>
    );
  }

  let cursor = 0;
  const arcs = slices
    .filter((slice) => slice.value > 0)
    .map((slice, index) => {
      const sweep = (slice.value / total) * 360;
      const start = cursor;
      const end = cursor + sweep;
      cursor = end;
      const path = describeArc(cx, cy, radius, start, end - 0.5);
      return (
        <path
          key={slice.label}
          d={path}
          fill="none"
          stroke={COLORS[index % COLORS.length]}
          strokeWidth={stroke}
          strokeLinecap="butt"
        />
      );
    });

  return (
    <div className="progress-donut-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="סטטוס פרויקטים">
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        {arcs}
        <text x={cx} y={cy - 4} textAnchor="middle" className="progress-donut-total">
          {total}
        </text>
        <text x={cx} y={cy + 16} textAnchor="middle" className="progress-donut-sub">
          פרויקטים
        </text>
      </svg>
      <ul className="progress-donut-legend">
        {slices.map((slice, index) => (
          <li key={slice.label}>
            <span className="progress-donut-swatch" style={{ background: COLORS[index % COLORS.length] }} />
            {slice.label} ({slice.value})
          </li>
        ))}
      </ul>
    </div>
  );
}
