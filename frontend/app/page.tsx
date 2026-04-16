import Link from "next/link";

export default function HomePage() {
  return (
    <main className="stack">
      <section className="glass hero">
        <h1 className="hero-title">פלטפורמת למידה מבוססת בינה מלאכותית</h1>
        <p className="hero-subtitle">
          למדו מהמסמכים האישיים שלכם עם סוכן מורה חכם, צרו מבחנים מותאמים וקבלו בדיקה אוטומטית
          עם פידבק פרקטי לשיפור.
        </p>
        <p>כל פעולה נשמרת בחשבון האישי שלכם, כולל היסטוריית שיחות, קבצים שהועלו, שאלונים וציונים.</p>
      </section>
      <section className="grid">
        <article className="glass stack">
          <h3>איך מתחילים?</h3>
          <div className="actions actions-two home-auth-actions">
          <Link href="/login" className="action-link">התחברות</Link>
          <Link href="/register" className="action-link">הרשמה</Link>
          </div>
        </article>
        <article className="glass stack">
          <h3>מה תקבלו במערכת</h3>
          <div className="item-list">
            <div className="surface">סוכן מורה שמבין מסמכים אישיים ומסביר לפי ההקשר שלכם.</div>
            <div className="surface">מחולל שאלות ברמות קושי שונות לאימון ממוקד.</div>
            <div className="surface">בודק תשובות עם ציון, פידבק והיסטוריה למדידה לאורך זמן.</div>
          </div>
        </article>
      </section>
    </main>
  );
}
