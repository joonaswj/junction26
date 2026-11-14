import { useEffect, useState } from "react";
import {
    getInsights,
    getOverview,
    getSpending,
    type Insights,
    type Overview,
    type Spending,
} from "../api";
import { formatEur } from "../format";

type Props = { customerId: string };

export default function Home({ customerId }: Props) {
    const [overview, setOverview] = useState<Overview | null>(null);
    const [insights, setInsights] = useState<Insights | null>(null);
    const [spending, setSpending] = useState<Spending | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([getOverview(customerId), getInsights(customerId), getSpending(customerId)])
            .then(([o, i, s]) => {
                setOverview(o);
                setInsights(i);
                setSpending(s);
            })
            .catch(() => setError("Could not load your data."));
    }, [customerId]);

    if (error) return <div className="screen"><p className="error">{error}</p></div>;
    if (!overview || !insights || !spending) {
        // The first request after the backend starts takes a few seconds.
        return <div className="screen"><p className="muted">Loading your data…</p></div>;
    }

    const categories = Object.entries(spending.by_category_eur);
    const maxCategory = Math.max(...categories.map(([, v]) => v), 1);

    return (
        <div className="screen">
            <section className="balance-card">
                <span className="label">Balance</span>
                <span className="balance">{formatEur(overview.current_balance_eur)}</span>
                <span className="small">Data until {overview.data_until}</span>
            </section>

            <section className="stats">
                <Stat label="Income / month" value={formatEur(overview.avg_monthly_income_eur)} />
                <Stat label="Spending / month" value={formatEur(overview.avg_monthly_spending_eur)} />
                <Stat
                    label="Savings rate"
                    value={overview.savings_rate_pct === null ? "–" : `${overview.savings_rate_pct}%`}
                />
            </section>

            <section>
                <h2>Compared to similar users</h2>
                <p className="muted small">
                    {insights.peer_count} customers: {insights.peer_group}
                </p>
                {insights.insights.length === 0 && (
                    <p className="muted">Your spending is close to similar users.</p>
                )}
                {insights.insights.map((i) => (
                    <article key={i.category} className={`insight insight-${i.direction}`}>
                        <span className="insight-amount">
                            {i.direction === "more" ? "+" : "−"}
                            {formatEur(Math.abs(i.diff_eur))}
                            <span className="small"> / month</span>
                        </span>
                        <span className="insight-category">{i.category}</span>
                        <p>{i.text}</p>
                    </article>
                ))}
                {insights.low_activity && (
                    <p className="muted small">
                        You make few card purchases from this account, so we only show where you
                        spend more.
                    </p>
                )}
            </section>

            <section>
                <h2>Spending, last {spending.months} months</h2>
                <p className="muted small">Total {formatEur(spending.total_eur)}</p>
                <ul className="bars">
                    {categories.map(([category, value]) => (
                        <li key={category}>
                            <div className="bar-label">
                                <span>{category}</span>
                                <span>{formatEur(value)}</span>
                            </div>
                            <div className="bar-track">
                                <div
                                    className="bar-fill"
                                    style={{ width: `${(value / maxCategory) * 100}%` }}
                                />
                            </div>
                        </li>
                    ))}
                </ul>
            </section>
        </div>
    );
}

function Stat({ label, value }: { label: string; value: string }) {
    return (
        <div className="stat">
            <span className="stat-value">{value}</span>
            <span className="label">{label}</span>
        </div>
    );
}
