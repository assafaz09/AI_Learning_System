"use client";

import type { CSSProperties } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import ActivityBarChart from "../../components/progress/ActivityBarChart";
import BreakdownChart from "../../components/progress/BreakdownChart";
import ProgressRing from "../../components/progress/ProgressRing";
import ProjectDonut from "../../components/progress/ProjectDonut";
import ScoreAreaChart from "../../components/progress/ScoreAreaChart";
import { errorMessage, fetchProgressDashboard, ProgressDashboard } from "../../lib/api";

type StatCardProps = {
  title: string;
  value: string;
  hint: string;
  accent: string;
};

function StatCard({ title, value, hint, accent }: StatCardProps) {
  return (
    <article className="progress-stat-card" style={{ "--stat-accent": accent } as CSSProperties}>
      <span className="progress-stat-title">{title}</span>
      <strong className="progress-stat-value">{value}</strong>
      <span className="progress-stat-hint">{hint}</span>
    </article>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<ProgressDashboard | null>(null);
  const [status, setStatus] = useState("טוען נתוני התקדמות…");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const dashboard = await fetchProgressDashboard();
        if (active) {
          setData(dashboard);
          setStatus("");
        }
      } catch (error) {
        if (active) {
          setStatus(errorMessage(error, "טעינת הדשבורד נכשלה"));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const summary = data?.summary;

  return (
    <main className="progress-dashboard">
      <section className="progress-hero glass">
        <div className="progress-hero-copy">
          <p className="progress-hero-kicker">דשבורד התקדמות</p>
          <h1 className="hero-title">המסע הלימודי שלכם במבט אחד</h1>
          <p className="hero-subtitle">
            מעקב אחר שיחות עם המורה, ציוני שאלונים, למידה בקבוצה ופרויקטים — עם תובנות מותאמות אישית.
          </p>
        </div>
        {summary ? (
          <div className="progress-hero-ring">
            <ProgressRing percent={summary.overall_progress_percent} />
          </div>
        ) : null}
      </section>

      {loading ? <p className="status">{status}</p> : null}
      {!loading && status ? <p className="status">{status}</p> : null}

      {summary ? (
        <>
          <section className="progress-stats-grid">
            <StatCard
              title="ממוצע ציונים"
              value={summary.average_quiz_score !== null ? `${Math.round(summary.average_quiz_score)}%` : "—"}
              hint={
                summary.best_quiz_score !== null
                  ? `שיא אישי: ${Math.round(summary.best_quiz_score)}%`
                  : "עדיין לא מילאתם שאלון"
              }
              accent="#7c3aed"
            />
            <StatCard
              title="שיחות עם המורה"
              value={String(summary.conversations_count)}
              hint={`${summary.teacher_messages_count} הודעות שנשלחו`}
              accent="#2563eb"
            />
            <StatCard
              title="למידה בקבוצה"
              value={String(summary.group_sessions_count)}
              hint={`${summary.group_messages_count} הודעות בסשנים`}
              accent="#0891b2"
            />
            <StatCard
              title="השלמת פרויקטים"
              value={`${Math.round(summary.projects_completion_percent)}%`}
              hint={`${summary.projects_done} מתוך ${summary.projects_total} הושלמו`}
              accent="#15803d"
            />
          </section>

          <section className="progress-charts-grid">
            <article className="glass progress-panel progress-panel--wide">
              <header className="progress-panel-header">
                <h3>מגמת ציונים</h3>
                <span className="muted">לאורך זמן</span>
              </header>
              <ScoreAreaChart points={data.quiz_scores_timeline} />
            </article>

            <article className="glass progress-panel">
              <header className="progress-panel-header">
                <h3>פעילות שבועית</h3>
                <span className="muted">14 ימים אחרונים</span>
              </header>
              <ActivityBarChart days={data.activity_last_14_days} />
            </article>

            <article className="glass progress-panel">
              <header className="progress-panel-header">
                <h3>פילוח פעילות</h3>
                <span className="muted">לפי סוג</span>
              </header>
              <BreakdownChart breakdown={data.activity_breakdown} />
            </article>

            <article className="glass progress-panel">
              <header className="progress-panel-header">
                <h3>סטטוס פרויקטים</h3>
                <span className="muted">{summary.projects_total} סה״כ</span>
              </header>
              <ProjectDonut slices={data.project_status_slices} total={summary.projects_total} />
            </article>
          </section>

          <section className="progress-bottom-grid">
            <article className="glass progress-panel">
              <header className="progress-panel-header">
                <h3>תובנות והמלצות</h3>
              </header>
              <ul className="progress-insights">
                {data.insights.map((insight) => (
                  <li key={insight}>{insight}</li>
                ))}
              </ul>
            </article>

            <article className="glass progress-panel">
              <header className="progress-panel-header">
                <h3>קיצורי דרך</h3>
              </header>
              <div className="actions dashboard-actions progress-shortcuts">
                <Link href="/teacher" className="action-link">
                  פתיחת סוכן מורה
                </Link>
                <Link href={"/group-learning" as Route} className="action-link">
                  למידה בקבוצה
                </Link>
                <Link href="/quiz" className="action-link">
                  יצירת שאלון
                </Link>
                <Link href="/teacher/my-projects" className="action-link">
                  הפרויקטים שלי
                </Link>
              </div>
              <div className="progress-mini-stats">
                <span>מסמכים: {summary.documents_count}</span>
                <span>שאלונים: {summary.quizzes_graded}</span>
                <span>פודקאסטים: {summary.podcasts_count}</span>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </main>
  );
}
