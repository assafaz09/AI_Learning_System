import Link from "next/link";

export default function DashboardPage() {
  return (
    <main className="stack">
      <section className="glass hero">
        <h1 className="hero-title">מערכת הלמידה שלכם</h1>
        <p>סביבת למידה אישית עם סוכן מורה, מחולל שאלות וסוכן בודק.</p>
      </section>
      <section className="grid">
        <article className="glass stack">
          <h3>איך זה עובד?</h3>
          <ol className="stack" style={{ gap: 6 }}>
            <li>מעלים קבצי לימוד.</li>
            <li>שואלים את הסוכן המורה על מסמכים שנבחרו.</li>
            <li>יוצרים שאלון ומגישים תשובות.</li>
            <li>מקבלים ציון ופידבק יחד עם היסטוריה מלאה.</li>
          </ol>
        </article>
        <article className="glass stack">
          <h3>קיצורי דרך מהירים</h3>
          <div className="actions">
            <Link href="/teacher" className="action-link">פתיחת סוכן מורה</Link>
            <Link href="/quiz" className="action-link">יצירת שאלון חדש</Link>
            <Link href="/grader" className="action-link">בדיקת תשובות</Link>
          </div>
        </article>
      </section>
    </main>
  );
}
