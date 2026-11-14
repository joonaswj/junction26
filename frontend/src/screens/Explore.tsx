import { useEffect, useState, type ReactNode } from "react";
import {
    exportUrl,
    getExplore,
    getExploreTransactions,
    getMyData,
    type CompareWith,
    type ExploreQuery,
    type ExploreResult,
    type GroupBy,
    type Measure,
    type MyData,
    type Transaction,
} from "../api";
import Visual from "../charts/Visual";
import HouseholdCard from "../components/HouseholdCard";
import { formatEurCents, formatMonthYear } from "../format";

type Props = {
    customerId: string;
    /** The view to show. Lives in App so other screens can open a view here. */
    query: ExploreQuery;
    onQuery: (query: ExploreQuery) => void;
    onAsk: (question: string) => void;
    /** Changes when the customer edits their household details. */
    contextVersion: number;
    onContextChange: () => void;
};

const GROUP_LABELS: Record<GroupBy, string> = {
    category: "Category",
    month: "Month",
    merchant: "Merchant",
    weekday: "Weekday",
};
const COMPARE_LABELS: Record<CompareWith, string> = {
    none: "Nobody",
    peers: "Similar customers",
    finland: "Finnish average",
};
const PAGE = 15;
const formatDate = (iso: string) => new Date(iso).toLocaleDateString("fi-FI");

/**
 * Explore your own data freely: choose what to look at, how to slice it and
 * who to compare with. Nothing here is a chart the bank picked for you.
 */
export default function Explore(props: Props) {
    const { customerId, query, onQuery, onAsk, contextVersion, onContextChange } = props;
    const [result, setResult] = useState<ExploreResult | null>(null);
    const [loadedKey, setLoadedKey] = useState("");
    const [failed, setFailed] = useState(false);
    const [view, setView] = useState<"chart" | "table">("chart");
    const key = JSON.stringify(query);
    const loadKey = `${key}#${contextVersion}`;
    const loading = loadedKey !== loadKey; // the chart on screen is for an older view

    useEffect(() => {
        let cancelled = false;
        getExplore(customerId, JSON.parse(key) as ExploreQuery)
            .then((r) => {
                if (cancelled) return;
                setResult(r);
                setFailed(false);
                setLoadedKey(loadKey);
            })
            .catch(() => {
                if (!cancelled) setFailed(true);
            });
        return () => {
            cancelled = true;
        };
    }, [customerId, key, loadKey]);

    if (failed && !result) {
        return (
            <div className="screen">
                <div className="chat-error" role="alert">
                    <p>We couldn't load your data.</p>
                    <button className="link-button" onClick={() => onQuery({ ...query })}>
                        Try again
                    </button>
                </div>
            </div>
        );
    }
    if (!result) {
        return (
            <div className="screen" aria-busy="true">
                <div className="skeleton skeleton-row" />
                <div className="skeleton skeleton-card" />
                <p className="muted small center">Loading your data…</p>
            </div>
        );
    }

    const q = result.query;
    const opts = result.options;
    const spending = q.measure === "spending";
    const allCats = q.categories.length === opts.categories.length;
    const canCompare = spending && (q.group_by === "category" || q.group_by === "month");
    // Change part of the view, keeping the rest.
    const set = (patch: ExploreQuery) => onQuery({ ...q, ...patch });

    function toggleCategory(cat: string) {
        if (allCats) return set({ categories: [cat] });
        const next = q.categories.includes(cat)
            ? q.categories.filter((c) => c !== cat)
            : [...q.categories, cat];
        set({ categories: next.length ? next : opts.categories });
    }

    return (
        <div className="screen explore">
            <header>
                <h2 className="section-title">Explore your data</h2>
                <p className="muted small">
                    Your data, your questions. Choose what to look at and tap anything in the chart.
                </p>
            </header>

            <section className="card controls" aria-label="What to look at">
                <Control label="Show">
                    {opts.measures.map((m) => (
                        <Chip
                            key={m.id}
                            active={q.measure === m.id}
                            onClick={() => set({ measure: m.id as Measure, month: null })}
                        >
                            {m.label}
                        </Chip>
                    ))}
                </Control>

                {spending && (
                    <Control label="Categories">
                        <Chip active={allCats} onClick={() => set({ categories: opts.categories })}>
                            All
                        </Chip>
                        {opts.categories.map((c) => (
                            <Chip
                                key={c}
                                active={!allCats && q.categories.includes(c)}
                                onClick={() => toggleCategory(c)}
                            >
                                {c}
                            </Chip>
                        ))}
                    </Control>
                )}

                {spending && (
                    <Control label="Slice by">
                        {opts.group_by
                            .filter((g) => !(q.month && g === "month"))
                            .map((g) => (
                                <Chip key={g} active={q.group_by === g} onClick={() => set({ group_by: g })}>
                                    {GROUP_LABELS[g]}
                                </Chip>
                            ))}
                    </Control>
                )}

                <Control label="Period">
                    {q.month && (
                        <Chip active onClick={() => set({ month: null, months: 12, group_by: "month" })}>
                            {formatMonthYear(q.month)} ×
                        </Chip>
                    )}
                    {opts.periods.map((p) => (
                        <Chip
                            key={p}
                            active={!q.month && q.months === p}
                            onClick={() => set({ months: p, month: null })}
                        >
                            {p} mo
                        </Chip>
                    ))}
                </Control>

                {canCompare && (
                    <Control label="Compare with">
                        {opts.compare.map((c) => (
                            <Chip key={c} active={q.compare === c} onClick={() => set({ compare: c })}>
                                {COMPARE_LABELS[c]}
                            </Chip>
                        ))}
                    </Control>
                )}
            </section>

            <section className={`card result${loading ? " loading" : ""}`} aria-busy={loading}>
                <p className="takeaway">{result.summary}</p>
                <div className="view-toggle" role="tablist" aria-label="View">
                    <button role="tab" aria-selected={view === "chart"} onClick={() => setView("chart")}>
                        Chart
                    </button>
                    <button role="tab" aria-selected={view === "table"} onClick={() => setView("table")}>
                        Table
                    </button>
                </div>
                {view === "chart" ? (
                    // Remount per view so a selection from the last chart doesn't carry over.
                    <Visual
                        key={key}
                        // The chart knows which view it shows, so a tap can drill
                        // down from exactly here (same categories, same month).
                        spec={{
                            ...result.visual,
                            notes: result.notes,
                            source: result.source,
                            explore: { ...q, categories: allCats ? undefined : q.categories },
                        }}
                        onAsk={onAsk}
                        onExplore={(next) => onQuery({ measure: "spending", compare: "none", ...next })}
                        question={result.questions[0]}
                        hideExploreButton
                    />
                ) : (
                    <DataTable table={result.table} />
                )}
                {result.questions.length > 1 && (
                    <div className="more-questions">
                        <p className="chips-label">Or ask</p>
                        <div className="suggestions">
                            {result.questions.slice(1).map((text) => (
                                <button key={text} className="suggestion" onClick={() => onAsk(text)}>
                                    {text}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </section>

            <HouseholdCard
                customerId={customerId}
                onChange={onContextChange}
                highlight={result.household_hint}
            />

            {spending && <Transactions customerId={customerId} query={q} queryKey={key} />}

            <YourData customerId={customerId} />
        </div>
    );
}

function Control({ label, children }: { label: string; children: ReactNode }) {
    return (
        <div className="control">
            <span className="control-label">{label}</span>
            <div className="chips">{children}</div>
        </div>
    );
}

function Chip(props: { active: boolean; onClick: () => void; children: ReactNode }) {
    return (
        <button
            type="button"
            className={`chip${props.active ? " active" : ""}`}
            aria-pressed={props.active}
            onClick={props.onClick}
        >
            {props.children}
        </button>
    );
}

function DataTable({ table }: { table: ExploreResult["table"] }) {
    const cell = (v: string | number) =>
        typeof v === "number" ? formatEurCents(v) : /^\d{4}-\d{2}$/.test(v) ? formatMonthYear(v) : v;
    return (
        <div className="table-wrap">
            <table className="data-table">
                <thead>
                    <tr>
                        {table.columns.map((c) => (
                            <th key={c}>{c}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {table.rows.map((row, i) => (
                        <tr key={i}>
                            {row.map((v, j) => (
                                <td key={j} className={typeof v === "number" ? "num" : ""}>
                                    {/* "Purchases" is a count, not euros */}
                                    {table.columns[j] === "Purchases" ? v : cell(v)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

/** The raw transactions behind the current view. */
function Transactions(props: { customerId: string; query: ExploreQuery; queryKey: string }) {
    const [limit, setLimit] = useState(PAGE);
    const [data, setData] = useState<{ total: number; items: Transaction[] } | null>(null);
    const [shownFor, setShownFor] = useState(props.queryKey);
    if (shownFor !== props.queryKey) {
        // A new view starts from the first page again.
        setShownFor(props.queryKey);
        setLimit(PAGE);
    }

    useEffect(() => {
        let cancelled = false;
        getExploreTransactions(props.customerId, JSON.parse(props.queryKey) as ExploreQuery, limit)
            .then((d) => {
                if (!cancelled) setData(d);
            })
            .catch(() => {
                if (!cancelled) setData(null);
            });
        return () => {
            cancelled = true;
        };
    }, [props.customerId, props.queryKey, limit]);

    if (!data) return null;
    return (
        <section>
            <h2 className="section-title">Transactions behind this view</h2>
            <p className="muted small section-subtitle">
                {data.total} transactions, newest first
            </p>
            <ul className="card tx-list">
                {data.items.map((t, i) => (
                    <li key={i}>
                        <div>
                            <span className="tx-category">{t.category}</span>
                            <span className="muted small">
                                {formatDate(t.tx_date)}
                                {t.merchant_id && ` · ${t.merchant_id}`}
                            </span>
                        </div>
                        <span className="tx-amount">{formatEurCents(t.tx_amount_eur)}</span>
                    </li>
                ))}
                {data.items.length === 0 && <li className="muted">No transactions in this view.</li>}
            </ul>
            {data.items.length < data.total && (
                <button className="btn-secondary" onClick={() => setLimit(limit + PAGE * 2)}>
                    Show more
                </button>
            )}
        </section>
    );
}

/** Transparency and portability: what we hold, how it's used, take it with you. */
function YourData({ customerId }: { customerId: string }) {
    const [info, setInfo] = useState<MyData | null>(null);
    const [open, setOpen] = useState(false);

    useEffect(() => {
        getMyData(customerId)
            .then(setInfo)
            .catch(() => setInfo(null));
    }, [customerId]);

    if (!info) return null;
    return (
        <section className="card your-data">
            <strong>Your data is yours</strong>
            <p className="muted small">
                This view uses your {info.transactions} transactions from {formatDate(info.first_date)} to{" "}
                {formatDate(info.last_date)}. You can take a copy with you.
            </p>
            <div className="download-row">
                <a className="btn-secondary" href={exportUrl(customerId, "csv")} download>
                    Download CSV
                </a>
                <a className="btn-secondary" href={exportUrl(customerId, "json")} download>
                    Download JSON
                </a>
            </div>
            <button className="viz-notes-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
                <span aria-hidden="true">{open ? "−" : "+"}</span>
                How is my data used here?
            </button>
            {open && (
                <ul className="data-notes">
                    <li>
                        <strong>Only you see your transactions.</strong> The assistant can look up your data
                        and nobody else's.
                    </li>
                    <li>
                        <strong>Similar customers</strong> are {info.peer_count} customers in your group (
                        {info.peer_group}). You only ever see the group's typical figure, never another
                        person's data, and others only see you as part of such a figure.
                    </li>
                    <li>
                        <strong>Finnish averages</strong> are open data:{" "}
                        <a href={info.open_data.url} target="_blank" rel="noreferrer">
                            {info.open_data.source} {info.open_data.year}
                        </a>{" "}
                        ({info.open_data.license}). They describe spending per person by age group, and the
                        categories match the bank's only roughly.
                    </li>
                    <li>
                        <strong>Suggested questions</strong> are chosen from your own figures, and each one
                        says why it was suggested.
                    </li>
                </ul>
            )}
        </section>
    );
}
