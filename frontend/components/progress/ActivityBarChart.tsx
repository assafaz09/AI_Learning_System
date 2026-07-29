import type { ActivityDay } from "../../lib/api";

type ActivityBarChartProps = {
  days: ActivityDay[];
};

function formatDayLabel(iso: string): string {
  const date = new Date(`${iso}T12:00:00`);
  return date.toLocaleDateString("he-IL", { weekday: "short", day: "numeric" });
}

export default function ActivityBarChart({ days }: ActivityBarChartProps) {
  const max = Math.max(1, ...days.map((d) => d.count));

  return (
    <div className="progress-activity-chart">
      <div className="progress-activity-bars" role="img" aria-label="פעילות ב-14 הימים האחרונים">
        {days.map((day) => {
          const heightPct = Math.round((day.count / max) * 100);
          return (
            <div key={day.date} className="progress-activity-col" title={`${day.date}: ${day.count} פעולות`}>
              <div className="progress-activity-bar-wrap">
                <div
                  className={`progress-activity-bar${day.count > 0 ? " has-value" : ""}`}
                  style={{ height: `${Math.max(day.count > 0 ? 12 : 4, heightPct)}%` }}
                />
              </div>
              <span className="progress-activity-label">{formatDayLabel(day.date)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
