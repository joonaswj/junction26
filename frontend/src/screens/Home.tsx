import { useEffect, useState } from "react";
import {
    getInsights,
    getOverview,
    getSpending,
    type Insights,
    type Overview,
    type Spending,
} from "../api";
import { describePeers, formatEur, formatEurCents } from "../format";

type Props = { customerId: string };

const formatDate = (iso: string) => new Date(iso).toLocaleDateString("fi-FI");

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
            .catch(() => setError("We couldn't load your information. Please try again later."));
    }, [customerId]);

    if (error) {
        return (
            <div className="screen">
                <p className="form-error">{error}</p>
            </div>
        );
    }
    if (!overview || !insights || !spending) {
        return (
            <div className="screen">
                <div className="spinner" aria-label="Loading" />
            </div>
        );
    }

    const categories = Object.entries(spending.by_category_eur);
    const maxCategory = Math.max(...categories.map(([, v]) => v), 1);

    return (
        <div className="screen">
            <section className="card account-card">
                <div className="account-row">
                    <span className="account-name">Current account</span>
                    <span className="muted small">{formatDate(overview.data_until)}</span>
                </div>
                <span className="balance">{formatEurCents(overview.current_balance_eur)}</span>
                <span className="muted small">Available balance</span>
            </section>

            <section className="card stats">
                <Stat label="Income / mo" value={formatEur(overview.avg_monthly_income_eur)} />
                <Stat label="Spending / mo" value={formatEur(overview.avg_monthly_spending_eur)} />
                <Stat
                    label="You save"
                    value={
                        overview.savings_rate_pct === null
                            ? "–"
                            : `${Math.round(overview.savings_rate_pct)} %`
                    }
                />
            </section>

            <section>
                <h2 className="section-title">You compared with others</h2>
                <p className="muted small section-subtitle">
                    Compared with {describePeers(insights.peer_group)}, last 12 months
                </p>
                {insights.insights.length === 0 && (
                    <div className="card">
                        <p>Your spending is close to people like you. Nice and steady!</p>
                    </div>
                )}
                <div className="insights">
                    {insights.insights.map((i) => (
                        <article key={i.category} className={`card insight insight-${i.direction}`}>
                            <div className="insight-head">
                                <span className="insight-category">{i.category}</span>
                                <span className="insight-amount">
                                    {i.direction === "more" ? "+" : "−"}
                                    {formatEur(Math.abs(i.diff_eur))}
                                    <span className="per-month"> /mo</span>
                                </span>
                            </div>
                            <p>{i.text}</p>
                        </article>
                    ))}
                </div>
            </section>

            <section>
                <h2 className="section-title">Spending by category</h2>
                <p className="muted small section-subtitle">
                    Last {spending.months} months, total {formatEur(spending.total_eur)}
                </p>
                <ul className="card bars">
                    {categories.map(([category, value]) => (
                        <li key={category}>
                            <div className="bar-label">
                                <span>{category}</span>
                                <span className="bar-value">{formatEur(value)}</span>
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
            <span className="muted small">{label}</span>
        </div>
    );
}
