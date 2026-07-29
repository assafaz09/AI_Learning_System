import type { QuizScorePoint } from "../../lib/api";

type ScoreAreaChartProps = {
  points: QuizScorePoint[];
};

function buildPath(points: QuizScorePoint[], width: number, height: number, padding: number): string {
  if (points.length === 0) {
    return "";
  }
  const innerW = width - padding * 2;
  const innerH = height - padding * 2;
  const coords = points.map((point, index) => {
    const x = padding + (points.length === 1 ? innerW / 2 : (index / (points.length - 1)) * innerW);
    const y = padding + innerH - (point.score / 100) * innerH;
    return { x, y };
  });
  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`).join(" ");
  const areaClose = ` L ${coords[coords.length - 1].x.toFixed(2)} ${(height - padding).toFixed(2)} L ${coords[0].x.toFixed(2)} ${(height - padding).toFixed(2)} Z`;
  return line + areaClose;
}

export default function ScoreAreaChart({ points }: ScoreAreaChartProps) {
  const width = 420;
  const height = 180;
  const padding = 16;

  if (points.length === 0) {
    return (
      <div className="progress-chart-empty">
        <p>עדיין אין ציוני שאלונים</p>
        <span className="muted">צרו שאלון ומלאו אותו כדי לראות גרף התקדמות</span>
      </div>
    );
  }

  const areaPath = buildPath(points, width, height, padding);
  const lineOnly = areaPath.replace(/ L [\d.]+ [\d.]+ L [\d.]+ [\d.]+ Z$/, "");

  return (
    <div className="progress-score-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="progress-score-svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id="score-area-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(37, 99, 235, 0.35)" />
            <stop offset="100%" stopColor="rgba(37, 99, 235, 0.02)" />
          </linearGradient>
        </defs>
        {[0, 25, 50, 75, 100].map((tick) => {
          const y = padding + (height - padding * 2) * (1 - tick / 100);
          return (
            <g key={tick}>
              <line x1={padding} x2={width - padding} y1={y} y2={y} className="progress-grid-line" />
              <text x={4} y={y + 4} className="progress-axis-label">
                {tick}
              </text>
            </g>
          );
        })}
        <path d={areaPath} fill="url(#score-area-fill)" />
        <path d={lineOnly} className="progress-score-line" fill="none" />
        {points.map((point, index) => {
          const x =
            padding + (points.length === 1 ? (width - padding * 2) / 2 : (index / (points.length - 1)) * (width - padding * 2));
          const y = padding + (height - padding * 2) * (1 - point.score / 100);
          return <circle key={`${point.quiz_id}-${index}`} cx={x} cy={y} r={5} className="progress-score-dot" />;
        })}
      </svg>
      <div className="progress-score-legend">
        {points.slice(-3).map((point) => (
          <span key={`${point.quiz_id}-${point.date}`} className="progress-score-chip">
            {point.quiz_title}: <strong>{Math.round(point.score)}%</strong>
          </span>
        ))}
      </div>
    </div>
  );
}
