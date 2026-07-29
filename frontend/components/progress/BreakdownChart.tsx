import type { ActivityBreakdown } from "../../lib/api";

const ITEMS: { key: keyof ActivityBreakdown; label: string; color: string }[] = [
  { key: "teacher_messages", label: "הודעות למורה", color: "#2563eb" },
  { key: "quiz_submissions", label: "שאלונים שנבחנו", color: "#7c3aed" },
  { key: "group_messages", label: "הודעות בקבוצה", color: "#0891b2" },
  { key: "documents_uploaded", label: "מסמכים", color: "#15803d" },
  { key: "projects_updated", label: "פרויקטים", color: "#ea580c" },
  { key: "podcasts_created", label: "פודקאסטים", color: "#db2777" },
];

type BreakdownChartProps = {
  breakdown: ActivityBreakdown;
};

export default function BreakdownChart({ breakdown }: BreakdownChartProps) {
  const max = Math.max(1, ...ITEMS.map((item) => breakdown[item.key]));

  return (
    <div className="progress-breakdown">
      {ITEMS.map((item) => {
        const value = breakdown[item.key];
        const widthPct = Math.round((value / max) * 100);
        return (
          <div key={item.key} className="progress-breakdown-row">
            <div className="progress-breakdown-meta">
              <span>{item.label}</span>
              <strong>{value}</strong>
            </div>
            <div className="progress-breakdown-track">
              <div
                className="progress-breakdown-fill"
                style={{ width: `${widthPct}%`, background: item.color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
