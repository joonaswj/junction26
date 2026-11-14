import { useEffect, useState } from "react";
import {
    getDashboardVisuals,
    getInsights,
    getOverview,
    type DashboardVisuals,
    type Insight,
    type Insights,
    type Overview,
} from "../api";
import Visual from "../charts/Visual";
import { describePeers, formatEur, formatEurCents } from "../format";

type Props = {
    customerId: string;
    /** Open the assistant with this question. */
    onAsk: (question: string) => void;
};

type Data = { overview: Overview; insights: Insights; visuals: DashboardVisuals };

const formatDate = (iso: string) => new Date(iso).toLocaleDateString("fi-FI");

export default function Home({ customerId, onAsk }: Props) {
    const [data, setData] = useState<Data | null>(null);
    const [error, setError] = useState(false);
    const [attempt, setAttempt] = useState(0);

    useEffect(() => {
        let cancelled = false;
        Promise.all([
            getOverview(customerId),
            getInsights(customerId),
            getDashboardVisuals(customerId),
        ])
            .then(([overview, insights, visuals]) => {
                if (!cancelled) setData({ overview, insights, visuals });
            })
            .catch(() => {
                if (!cancelled) setError(true);
            });
        return () => {
            cancelled = true;
        };
    }, [customerId, attempt]);

    if (error) {
        return (
            <div className="screen">
                <div className="chat-error" role="alert">
                    <p>We couldn't load your information.</p>
                    <button
                        className="link-button"
                        onClick={() => {
                            setError(false);
                            setAttempt((a) => a + 1);
                        }}
                    >
                        Try again
                    </button>
                </div>
            </div>
        );
    }
    if (!data) {
        return (
            <div className="screen" aria-busy="true">
                <div className="skeleton skeleton-card" />
                <div className="skeleton skeleton-row" />
                <div className="skeleton skeleton-card" />
                <p className="muted small center">Loading your finances…</p>
            </div>
        );
    }

    const { overview, insights, visuals } = data;
    const saved = overview.avg_monthly_income_eur - overview.avg_monthly_spending_eur;

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

            <section>
                <div className="card stats">
                    <Stat label="Income / mo" value={formatEur(overview.avg_monthly_income_eur)} />
                    <Stat label="Spending / mo" value={formatEur(overview.avg_monthly_spending_eur)} />
                    <Stat
                        label="You keep"
                        value={
                            overview.savings_rate_pct === null
                                ? "–"
                                : `${Math.round(overview.savings_rate_pct)}\u00a0%`
                        }
                    />
                </div>
                {overview.savings_rate_pct !== null && (
                    <p className="explain">
                        On average you keep <strong>{formatEur(saved)}</strong> a month: that's{" "}
                        {Math.round(overview.savings_rate_pct)}&nbsp;% of your income, your{" "}
                        <em>savings rate</em>. Averages are for the last 12 months.
                    </p>
                )}
            </section>

            <section>
                <SectionHead
                    title="You and similar customers"
                    subtitle={`Monthly averages, compared with ${insights.peer_count} ${describePeers(insights.peer_group)}.`}
                />
                {insights.insights.length === 0 ? (
                    <div className="card">
                        <p>Your spending is close to similar customers. Nice and steady!</p>
                    </div>
                ) : (
                    <div className="insights">
                        {insights.insights.map((i) => (
                            <InsightCard key={i.category} insight={i} onAsk={onAsk} />
                        ))}
                    </div>
                )}
                <button
                    className="btn-secondary"
                    onClick={() => onAsk("How do I compare with similar customers?")}
                >
                    See the full comparison
                </button>
            </section>

            <section>
                <div className="card">
                    <Visual spec={visuals.income_vs_spending} />
                </div>
                <p className="explain">
                    When the green column is taller than the blue one, you earned more than you
                    spent that month.
                </p>
            </section>

            <section>
                <div className="card">
                    <Visual spec={visuals.spending} />
                </div>
                <button className="btn-secondary" onClick={() => onAsk("Where could I save the most?")}>
                    Ask where you could save
                </button>
            </section>

            <section>
                {visuals.mortgage ? (
                    <>
                        <div className="card">
                            <Visual spec={visuals.mortgage} />
                        </div>
                        <button
                            className="btn-secondary"
                            onClick={() =>
                                onAsk(
                                    visuals.mortgage?.decision === "rejected"
                                        ? "What could improve my chances next time?"
                                        : "What would my monthly loan payment be?",
                                )
                            }
                        >
                            Ask about your application
                        </button>
                    </>
                ) : (
                    <div className="card teaser">
                        <strong>Thinking about a home of your own?</strong>
                        <p className="muted">
                            See what price range could fit your income and savings, and what a loan
                            would cost each month.
                        </p>
                        <button
                            className="btn-primary"
                            onClick={() => onAsk("Could I afford a 250 000 € home?")}
                        >
                            Try a home loan estimate
                        </button>
                    </div>
                )}
            </section>
        </div>
    );
}

function SectionHead({ title, subtitle }: { title: string; subtitle: string }) {
    return (
        <>
            <h2 className="section-title">{title}</h2>
            <p className="muted small section-subtitle">{subtitle}</p>
        </>
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

function InsightCard({ insight, onAsk }: { insight: Insight; onAsk: (q: string) => void }) {
    const more = insight.direction === "more";
    const max = Math.max(insight.you_eur, insight.peer_median_eur, 1);
    return (
        <article className="card insight">
            <div className="insight-head">
                <span className="insight-category">{insight.category}</span>
                <span className={`delta ${more ? "delta-more" : "delta-less"}`}>
                    <span aria-hidden="true">{more ? "▲" : "▼"}</span>
                    {formatEur(Math.abs(insight.diff_eur))} {more ? "more" : "less"} / mo
                </span>
            </div>
            <div className="mini-compare">
                <MiniBar label="You" value={insight.you_eur} max={max} className="you" />
                <MiniBar
                    label="Others"
                    value={insight.peer_median_eur}
                    max={max}
                    className="peer"
                />
            </div>
            <div className="insight-foot">
                <span className="muted small">
                    You spend {more ? "more" : "less"} than{" "}
                    {Math.min(Math.round(more ? insight.percentile : 100 - insight.percentile), 99)}
                    &nbsp;% of similar customers.
                </span>
                <button
                    className="link-button"
                    onClick={() =>
                        onAsk(
                            `Why do I spend ${insight.direction} on ${insight.category.toLowerCase()} than others?`,
                        )
                    }
                >
                    Ask why
                </button>
            </div>
        </article>
    );
}

function MiniBar(props: { label: string; value: number; max: number; className: string }) {
    return (
        <div className="mini-row">
            <span className="mini-label">{props.label}</span>
            <div className="mini-track">
                <div
                    className={`mini-fill ${props.className}`}
                    style={{ width: `${Math.max((props.value / props.max) * 100, 1)}%` }}
                />
            </div>
            <span className="mini-value">{formatEur(props.value)}</span>
        </div>
    );
}
