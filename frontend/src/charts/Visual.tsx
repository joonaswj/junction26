import { useState, type ReactNode } from "react";
import type {
    BarsVisual,
    BudgetVisual,
    CalcVisual,
    ColumnsVisual,
    CompareVisual,
    ExploreQuery,
    LineVisual,
    MortgageVisual,
    Visual as VisualSpec,
} from "../api";
import { formatEur, formatMonth, formatMonthYear, formatPct } from "../format";
import "./charts.css";

type Actions = {
    /** Send this question to the assistant. */
    onAsk?: (question: string) => void;
    /** Open this view in Explore. */
    onExplore?: (query: ExploreQuery) => void;
    /** The question for the whole chart. Defaults to one that fits the chart. */
    question?: string;
    /** Inside Explore the chart is already the explore view. */
    hideExploreButton?: boolean;
    /** In a chat answer the chart's own question was just asked. */
    hideAskButton?: boolean;
};

type Props = Actions & { spec: VisualSpec };

/**
 * Draws one chart spec from the backend. Used on the overview, in Explore
 * and in chat. Every chart is a starting point: tap a bar or a month to ask
 * the assistant about it or to look closer in Explore.
 */
export default function Visual({ spec, ...actions }: Props) {
    switch (spec.type) {
        case "budget":
            return <Budget spec={spec} {...actions} />;
        case "bars":
            return <Bars spec={spec} {...actions} />;
        case "columns":
            return <Columns spec={spec} {...actions} />;
        case "line":
            return <Line spec={spec} {...actions} />;
        case "compare":
            return <Compare spec={spec} {...actions} />;
        case "mortgage":
            return <Mortgage spec={spec} {...actions} />;
        case "calc":
            return <Calc spec={spec} />;
        default:
            return null;
    }
}

function Figure(props: { title: string; subtitle?: ReactNode; children: ReactNode }) {
    return (
        <figure className="viz" aria-label={props.title}>
            <figcaption>
                <span className="viz-title">{props.title}</span>
                {props.subtitle && <span className="viz-sub">{props.subtitle}</span>}
            </figcaption>
            {props.children}
        </figure>
    );
}

type Action = { text: string; run: () => void };

/** What the customer tapped, with what they can do next. */
function Focus(props: { label: ReactNode; ask?: Action; drill?: Action; onClose: () => void }) {
    return (
        <div className="viz-focus">
            <div className="viz-focus-head">
                <span>{props.label}</span>
                <button type="button" className="viz-close" onClick={props.onClose} aria-label="Close">
                    ×
                </button>
            </div>
            <div className="viz-focus-actions">
                {props.ask && (
                    <button type="button" className="viz-action primary" onClick={props.ask.run}>
                        <AskIcon />
                        {props.ask.text}
                    </button>
                )}
                {props.drill && (
                    <button type="button" className="viz-action" onClick={props.drill.run}>
                        <ExploreIcon />
                        {props.drill.text}
                    </button>
                )}
            </div>
        </div>
    );
}

/** Whole-chart actions and the small print about benchmarks. */
function Footer(props: Actions & { spec: VisualSpec }) {
    const { spec, onExplore } = props;
    const [open, setOpen] = useState(false);
    const link = props.hideExploreButton ? undefined : spec.explore;
    const onAsk = props.hideAskButton ? undefined : props.onAsk;
    const question = props.question;
    return (
        <>
            {((onAsk && question) || (onExplore && link)) && (
                <div className="viz-actions">
                    {onAsk && question && (
                        <button type="button" className="viz-action primary" onClick={() => onAsk(question)}>
                            <AskIcon />
                            Ask about this
                        </button>
                    )}
                    {onExplore && link && (
                        <button type="button" className="viz-action" onClick={() => onExplore(link)}>
                            <ExploreIcon />
                            Explore
                        </button>
                    )}
                </div>
            )}
            {!!spec.notes?.length && (
                <div className="viz-notes">
                    <button
                        type="button"
                        className="viz-notes-toggle"
                        onClick={() => setOpen(!open)}
                        aria-expanded={open}
                    >
                        <span aria-hidden="true">{open ? "−" : "+"}</span>
                        Where do these numbers come from?
                    </button>
                    {open && (
                        <ul>
                            {spec.notes.map((n) => (
                                <li key={n}>{n}</li>
                            ))}
                            {spec.source && (
                                <li>
                                    Source:{" "}
                                    <a href={spec.source.url} target="_blank" rel="noreferrer">
                                        {spec.source.source}, table {spec.source.table.split(":")[0]}
                                    </a>{" "}
                                    ({spec.source.license}).
                                </li>
                            )}
                        </ul>
                    )}
                </div>
            )}
        </>
    );
}

const lower = (s: string) => s.toLowerCase();

/* Horizontal bars: one value per row, every bar labelled. Tap a row.
   Rows can be grouped by cost type, and can carry the customer's "usual"
   month so a heavy month is read against their own normal. */
function Bars({ spec, onAsk, onExplore, question, hideExploreButton, hideAskButton }: Actions & { spec: BarsVisual }) {
    const [selected, setSelected] = useState<string | null>(null);
    const max = Math.max(...spec.items.flatMap((i) => [i.value, i.usual ?? 0]), 1);
    const kind = spec.explore?.group_by; // category | type | merchant | weekday
    const month = spec.explore?.month ?? null;
    const interactive =
        (kind === "category" || kind === "type" || kind === "merchant") && !!(onAsk || onExplore);
    const item = spec.items.find((i) => i.label === selected);
    const when = month ? ` in ${formatMonthYear(month)}` : "";

    let drill: Action | undefined;
    let askText = item ? `Tell me about my ${lower(item.label)} spending${when}.` : "";
    if (item && kind === "merchant") askText = `What did I buy from ${item.label}${when}?`;
    if (item && kind === "type") askText = `Tell me about my ${lower(item.label)}${when}.`;
    if (item && onExplore && kind === "type") {
        drill = {
            text: "See the categories",
            run: () => onExplore({ ...spec.explore, group_by: "category", categories: item.categories }),
        };
    } else if (item && onExplore && kind === "category") {
        drill = month
            ? {
                  text: "See the merchants",
                  run: () => onExplore({ month, group_by: "merchant", categories: [item.label] }),
              }
            : {
                  text: "See month by month",
                  run: () =>
                      onExplore({
                          group_by: "month",
                          categories: [item.label],
                          months: Math.max(spec.explore?.months ?? 6, 6),
                      }),
              };
    }

    const renderRow = (row: BarsVisual["items"][number]) => {
        const diff = row.usual === undefined ? 0 : row.value - row.usual;
        const body = (
            <>
                <div className="viz-row">
                    <span>{row.label}</span>
                    <span className="viz-value">
                        {formatEur(row.value)}
                        {spec.show_share !== false && (
                            <span className="viz-share">
                                {Math.round((row.value / (spec.total || 1)) * 100)}&nbsp;%
                            </span>
                        )}
                    </span>
                </div>
                <div className="viz-track">
                    <div className="viz-fill s1" style={{ width: `${(row.value / max) * 100}%` }} />
                    {row.usual !== undefined && (
                        <span className="viz-usual" style={{ left: `${(row.usual / max) * 100}%` }} />
                    )}
                </div>
                {row.usual !== undefined && (
                    <span className="viz-usual-text">
                        Usually {formatEur(row.usual)}
                        {Math.abs(diff) >= 20 && ` · ${formatEur(Math.abs(diff))} ${diff > 0 ? "more" : "less"} this month`}
                    </span>
                )}
                {row.note && <span className="viz-usual-text">{row.note}</span>}
            </>
        );
        return (
            <li key={row.label} className={row.label === selected ? "selected" : ""}>
                {interactive ? (
                    <button
                        type="button"
                        className="viz-tap"
                        onClick={() => setSelected(row.label === selected ? null : row.label)}
                        aria-pressed={row.label === selected}
                    >
                        {body}
                    </button>
                ) : (
                    body
                )}
                {row.label === selected && item && (
                    <Focus
                        label={
                            <>
                                <strong>{item.label}</strong> · {formatEur(item.value)}
                            </>
                        }
                        onClose={() => setSelected(null)}
                        ask={onAsk && { text: "Ask about this", run: () => onAsk(askText) }}
                        drill={drill}
                    />
                )}
            </li>
        );
    };

    return (
        <Figure
            title={spec.title}
            subtitle={
                <>
                    {spec.subtitle} <strong>{formatEur(spec.total)}</strong>
                </>
            }
        >
            {spec.groups ? (
                spec.groups.map((group) => (
                    <div key={group.key} className="viz-group">
                        <div className="viz-group-head">
                            <span>
                                <i className={`viz-swatch type-${group.key}`} />
                                {group.label}
                            </span>
                            <span>{formatEur(group.value)}</span>
                        </div>
                        <ul className="viz-bars">
                            {spec.items.filter((i) => i.group === group.key).map(renderRow)}
                        </ul>
                    </div>
                ))
            ) : (
                <ul className="viz-bars">{spec.items.map(renderRow)}</ul>
            )}
            {spec.items.some((i) => i.usual !== undefined) && (
                <p className="viz-hint">
                    <span className="viz-usual-key" /> The line marks your usual month (12-month average).
                </p>
            )}
            {interactive && !item && <p className="viz-hint">Tap a row to ask about it or look closer.</p>}
            <Footer spec={spec} onAsk={onAsk} onExplore={onExplore} hideExploreButton={hideExploreButton} hideAskButton={hideAskButton} question={question ?? "Where does my money go?"} />
        </Figure>
    );
}

/* Columns over months, 1-2 series. Tap a month to read it, ask or look inside. */
function Columns({ spec, onAsk, onExplore, question, hideExploreButton, hideAskButton }: Actions & { spec: ColumnsVisual }) {
    const [selected, setSelected] = useState(spec.labels.length - 1);
    const [touched, setTouched] = useState(false);
    const at = Math.min(selected, spec.labels.length - 1);
    const all = spec.series.flatMap((s) => s.values);
    const max = Math.max(...all, spec.reference?.value ?? 0, 0);
    const min = Math.min(...all, 0);
    const range = max - min || 1;
    const zero = (-min / range) * 100; // baseline position from the bottom, %
    const single = spec.series.length === 1;
    const colors = spec.colors ?? ["s1", "s2"];
    const label = spec.labels[at];
    const monthName = formatMonthYear(label);
    const cats = spec.explore?.categories;
    const isSpending = !spec.explore?.measure || spec.explore.measure === "spending";

    const pick = (i: number) => {
        setSelected(i);
        setTouched(true);
    };

    let askText = `What did I spend on in ${monthName}?`;
    if (!isSpending) askText = `What happened to my income and spending in ${monthName}?`;
    else if (cats?.length) askText = `What did I spend on ${cats.map(lower).join(" and ")} in ${monthName}?`;

    return (
        <Figure
            title={spec.title}
            subtitle={
                spec.total === undefined ? (
                    spec.subtitle
                ) : (
                    <>
                        {spec.subtitle} <strong>{formatEur(spec.total)}</strong>
                    </>
                )
            }
        >
            {/* The readout doubles as the legend: swatch + name + value. */}
            <div className={`viz-readout${single ? "" : " multi"}`} aria-live="polite">
                <span className="viz-readout-month">{monthName}</span>
                {spec.series.map((s, si) => (
                    <span key={s.name} className="viz-key">
                        <i className={`viz-swatch ${colors[si] ?? "s2"}`} />
                        {!single && `${s.name} `}
                        <strong>{formatEur(s.values[at])}</strong>
                    </span>
                ))}
            </div>
            <div className="viz-columns">
                {spec.reference && (
                    <span
                        className="viz-reference"
                        style={{ bottom: `${zero + (spec.reference.value / range) * 100}%` }}
                    >
                        <span>
                            {spec.reference.label.split(" (")[0]} {formatEur(spec.reference.value)}
                        </span>
                    </span>
                )}
                {spec.labels.map((month, i) => (
                    <button
                        key={month}
                        type="button"
                        className={`viz-month${i === at ? " selected" : ""}`}
                        onClick={() => pick(i)}
                        aria-label={`${formatMonthYear(month)}: ${spec.series
                            .map((s) => `${s.name} ${formatEur(s.values[i])}`)
                            .join(", ")}`}
                    >
                        <span className="viz-plot">
                            {spec.series.map((s, si) => {
                                const v = s.values[i];
                                const h = Math.max((Math.abs(v) / range) * 100, 0.8);
                                return (
                                    <span key={s.name} className="viz-slot">
                                        <span
                                            className={`viz-column ${colors[si] ?? "s2"}${v < 0 ? " negative" : ""}`}
                                            style={{ height: `${h}%`, bottom: `${v < 0 ? zero - h : zero}%` }}
                                        />
                                    </span>
                                );
                            })}
                            {min < 0 && <span className="viz-zero" style={{ bottom: `${zero}%` }} />}
                        </span>
                        <span className="viz-tick">{formatMonth(month)}</span>
                    </button>
                ))}
            </div>
            {!touched && <p className="viz-hint after-ticks">Tap a month to see its numbers.</p>}
            {touched && (onAsk || onExplore) && (
                <div className="after-ticks">
                    <Focus
                        label={<strong>{monthName}</strong>}
                        onClose={() => setTouched(false)}
                        ask={onAsk && { text: "Ask about this month", run: () => onAsk(askText) }}
                        drill={
                            onExplore && {
                                text: `Look inside ${formatMonth(label)}`,
                                // One category has nothing to split by category: show its merchants.
                                run: () =>
                                    onExplore({
                                        month: label,
                                        group_by: cats?.length === 1 ? "merchant" : "category",
                                        categories: cats,
                                    }),
                            }
                        }
                    />
                </div>
            )}
            <Footer
                spec={spec}
                onAsk={onAsk}
                onExplore={onExplore}
                hideExploreButton={hideExploreButton}
                hideAskButton={hideAskButton}
                question={question ?? `How has my ${lower(spec.title.replace(" by month", ""))} changed?`}
            />
        </Figure>
    );
}

/* One value over months (balance). Tap a month to read its value. */
function Line({ spec, onAsk, onExplore, question, hideExploreButton, hideAskButton }: Actions & { spec: LineVisual }) {
    const n = spec.values.length;
    const [selected, setSelected] = useState(n - 1);
    const at = Math.min(selected, n - 1);
    const lo = Math.min(...spec.values);
    const hi = Math.max(...spec.values);
    const pad = (hi - lo || 1) * 0.15;
    const min = lo - pad;
    const range = hi + pad - min;
    const x = (i: number) => (n === 1 ? 50 : (i / (n - 1)) * 100);
    const y = (v: number) => 100 - ((v - min) / range) * 100;
    const points = spec.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    const change = spec.values[n - 1] - spec.values[0];
    return (
        <Figure title={spec.title} subtitle={spec.subtitle}>
            <div className="viz-readout" aria-live="polite">
                <span className="viz-readout-month">{formatMonthYear(spec.labels[at])}</span>
                <span className="viz-key">
                    <i className="viz-swatch s1" />
                    <strong>{formatEur(spec.values[at])}</strong>
                </span>
            </div>
            <div className="viz-line">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                    <polygon className="viz-area" points={`0,100 ${points} 100,100`} />
                    <polyline className="viz-stroke" points={points} />
                </svg>
                <span className="viz-dot" style={{ left: `${x(at)}%`, top: `${y(spec.values[at])}%` }} />
                <div className="viz-hits">
                    {spec.labels.map((label, i) => (
                        <button
                            key={label}
                            type="button"
                            onClick={() => setSelected(i)}
                            aria-label={`${formatMonthYear(label)}: ${formatEur(spec.values[i])}`}
                        />
                    ))}
                </div>
            </div>
            <div className="viz-axis">
                <span>{formatMonthYear(spec.labels[0])}</span>
                <span>{formatMonthYear(spec.labels[n - 1])}</span>
            </div>
            <p className="viz-hint">
                {change >= 0 ? "Up" : "Down"} {formatEur(Math.abs(change))} over the period. Tap the chart to see a
                month.
            </p>
            <Footer spec={spec} onAsk={onAsk} onExplore={onExplore} hideExploreButton={hideExploreButton} hideAskButton={hideAskButton} question={question ?? "Is my balance growing?"} />
        </Figure>
    );
}

/* You vs a benchmark: you in green, similar customers in grey, Finland in blue. */
function Compare({ spec, onAsk, onExplore, question, hideExploreButton, hideAskButton }: Actions & { spec: CompareVisual }) {
    const [selected, setSelected] = useState<string | null>(null);
    const max = Math.max(...spec.items.flatMap((i) => [i.you, i.peers]), 1);
    const cls = spec.peer_class ?? "peer";
    const finland = spec.explore?.compare === "finland" || cls === "s2";
    const who = finland ? "the Finnish average" : "similar customers";
    const interactive = !!(onAsk || onExplore);
    const item = spec.items.find((i) => i.label === selected);

    return (
        <Figure title={spec.title} subtitle={spec.subtitle}>
            {spec.items.length === 0 ? (
                <p className="viz-empty">There is no fair benchmark for this selection.</p>
            ) : (
                <>
                    <div className="viz-legend">
                        <span className="viz-key">
                            <i className="viz-swatch s1" />
                            {spec.you_label}
                        </span>
                        <span className="viz-key">
                            <i className={`viz-swatch ${cls}`} />
                            {spec.peer_label}
                        </span>
                    </div>
                    <ul className="viz-compare">
                        {spec.items.map((row) => {
                            const body = (
                                <>
                                    <span className="viz-compare-label">{row.label}</span>
                                    <CompareBar className="s1" value={row.you} max={max} name={spec.you_label} />
                                    <CompareBar className={cls} value={row.peers} max={max} name={spec.peer_label} />
                                </>
                            );
                            return (
                                <li key={row.label} className={row.label === selected ? "selected" : ""}>
                                    {interactive ? (
                                        <button
                                            type="button"
                                            className="viz-tap"
                                            onClick={() => setSelected(row.label === selected ? null : row.label)}
                                            aria-pressed={row.label === selected}
                                        >
                                            {body}
                                        </button>
                                    ) : (
                                        body
                                    )}
                                    {row.label === selected && item && (
                <Focus
                    label={
                        <>
                            <strong>{item.label}</strong> · {formatEur(Math.abs(item.you - item.peers))}{" "}
                            {item.you > item.peers ? "more" : "less"} a month
                        </>
                    }
                    onClose={() => setSelected(null)}
                    ask={
                        onAsk && {
                            text: "Ask about this",
                            run: () =>
                                onAsk(item.question ?? `How does my ${lower(item.label)} spending compare with ${who}?`),
                        }
                    }
                    drill={
                        onExplore && {
                            text: "See month by month",
                            run: () =>
                                onExplore({
                                    group_by: "month",
                                    categories: [item.label],
                                    months: 12,
                                    compare: finland ? "finland" : "peers",
                                }),
                        }
                    }
                />
            )}
                                </li>
                            );
                        })}
                    </ul>
                </>
            )}
            {spec.percentile !== undefined && <Position percentile={spec.percentile} />}
            {interactive && !item && spec.items.length > 1 && (
                <p className="viz-hint">Tap a row to ask about it or look closer.</p>
            )}
            <Footer
                spec={spec}
                onAsk={onAsk}
                onExplore={onExplore}
                hideExploreButton={hideExploreButton}
                hideAskButton={hideAskButton}
                question={
                    question ??
                    (finland
                        ? "How do I compare with the Finnish average for my age?"
                        : "How do I compare with similar customers?")
                }
            />
        </Figure>
    );
}

function CompareBar(props: { className: string; value: number; max: number; name: string }) {
    return (
        <div className="viz-compare-bar" aria-label={`${props.name}: ${formatEur(props.value)}`}>
            <div
                className={`viz-fill ${props.className}`}
                style={{ width: `${Math.max((props.value / props.max) * 72, 0.5)}%` }}
            />
            <span className="viz-value">{formatEur(props.value)}</span>
        </div>
    );
}

/* Where the customer sits among similar customers, lowest to highest spender. */
function Position({ percentile }: { percentile: number }) {
    const p = Math.min(Math.max(percentile, 1), 99);
    const markerAt = Math.min(Math.max(p, 4), 96); // keep the "You" label inside the card
    const less = percentile < 50;
    return (
        <div className="viz-position">
            <div className="viz-position-track">
                <span className="viz-position-marker" style={{ left: `${markerAt}%` }}>
                    You
                </span>
            </div>
            <div className="viz-axis">
                <span>Spends least</span>
                <span>Spends most</span>
            </div>
            <p className="viz-hint">
                You spend {less ? "less" : "more"} than{" "}
                <strong>{less ? 100 - Math.round(p) : Math.round(p)}&nbsp;%</strong> of similar customers.
            </p>
        </div>
    );
}

/* Home price split into loan and own money. */
function PriceSplit(props: { price: number; loan: number; downPayment: number }) {
    const loanShare = (props.loan / props.price) * 100;
    return (
        <div className="viz-split">
            <div className="viz-split-bar">
                <span className="s1" style={{ width: `${loanShare}%` }} />
                <span className="s2" style={{ width: `${100 - loanShare}%` }} />
            </div>
            <div className="viz-legend spread">
                <span className="viz-key">
                    <i className="viz-swatch s1" />
                    Loan <strong>{formatEur(props.loan)}</strong>
                </span>
                <span className="viz-key">
                    <i className="viz-swatch s2" />
                    Your own money <strong>{formatEur(props.downPayment)}</strong>
                </span>
            </div>
        </div>
    );
}

/* Loan-to-value against the 90 % cap. */
function LtvMeter(props: { ltv: number; limit: number; typical?: number }) {
    const over = props.ltv > props.limit + 1e-9;
    return (
        <div className="viz-ltv">
            <div className="viz-row">
                <span>
                    <strong>Loan-to-value {formatPct(props.ltv)}</strong>
                </span>
                <Status ok={!over} okText="Within the cap" badText="Over the cap" />
            </div>
            <div className="viz-meter">
                <div
                    className={`viz-fill ${over ? "bad" : "s1"}`}
                    style={{ width: `${Math.min(props.ltv, 1) * 100}%` }}
                />
                <span className="viz-cap" style={{ left: `${props.limit * 100}%` }}>
                    <span>Cap {formatPct(props.limit)}</span>
                </span>
            </div>
            <p className="viz-hint">
                Loan-to-value is the loan as a share of the home's price. Banks can lend at most{" "}
                {formatPct(props.limit)}, the rest is your own money.
                {props.typical !== undefined &&
                    ` Approved applications typically had ${formatPct(props.typical)}.`}
            </p>
        </div>
    );
}

/* Where an average month's income goes: fixed, varies, free choice, left over.
   Tap a part to see what is in it. */
function Budget({ spec, onAsk, onExplore, question, hideExploreButton, hideAskButton }: Actions & { spec: BudgetVisual }) {
    const [open, setOpen] = useState<string | null>(null);
    const over = spec.left < 0;
    const whole = Math.max(spec.income, spec.income - spec.left, 1); // the bar is income, or spending if that is larger
    const part = (value: number) => `${(Math.max(value, 0) / whole) * 100}%`;
    const interactive = !!(onAsk || onExplore);

    return (
        <Figure
            title={spec.title}
            subtitle={
                <>
                    {spec.subtitle} <strong>{formatEur(spec.income)}</strong>
                </>
            }
        >
            <div className="viz-budget-bar" role="img" aria-label="Income split by cost type">
                {spec.segments.map((s) => (
                    <span key={s.key} className={`type-${s.key}`} style={{ width: part(s.value) }} />
                ))}
                {!over && <span className="type-left" style={{ width: part(spec.left) }} />}
            </div>
            <ul className="viz-budget">
                {spec.segments.map((s) => {
                    const head = (
                        <div className="viz-row">
                            <span className="viz-key">
                                <i className={`viz-swatch type-${s.key}`} />
                                {s.label}
                            </span>
                            <span className="viz-value">
                                {formatEur(s.value)}
                                <span className="viz-share">{s.share_pct ?? 0}&nbsp;%</span>
                            </span>
                        </div>
                    );
                    return (
                        <li key={s.key} className={open === s.key ? "selected" : ""}>
                            {interactive ? (
                                <button
                                    type="button"
                                    className="viz-tap"
                                    onClick={() => setOpen(open === s.key ? null : s.key)}
                                    aria-expanded={open === s.key}
                                >
                                    {head}
                                </button>
                            ) : (
                                head
                            )}
                            {open === s.key && (
                                <div className="viz-focus">
                                    <div className="viz-focus-head">
                                        <span className="viz-hint">{s.description}</span>
                                        <button
                                            type="button"
                                            className="viz-close"
                                            onClick={() => setOpen(null)}
                                            aria-label="Close"
                                        >
                                            ×
                                        </button>
                                    </div>
                                    <ul className="viz-budget-items">
                                        {s.items
                                            .filter((i) => i.value > 0)
                                            .map((i) => (
                                                <li key={i.label}>
                                                    <span>{i.label}</span>
                                                    <span>
                                                        <strong>{formatEur(i.value)}</strong> a month ·{" "}
                                                        {formatEur(i.yearly)} a year
                                                    </span>
                                                </li>
                                            ))}
                                    </ul>
                                    <div className="viz-focus-actions">
                                        {onAsk && (
                                            <button
                                                type="button"
                                                className="viz-action primary"
                                                onClick={() => onAsk(`Tell me about my ${lower(s.label)}.`)}
                                            >
                                                <AskIcon />
                                                Ask about this
                                            </button>
                                        )}
                                        {onExplore && (
                                            <button
                                                type="button"
                                                className="viz-action"
                                                onClick={() =>
                                                    onExplore({
                                                        group_by: "category",
                                                        categories: s.items.map((i) => i.label),
                                                    })
                                                }
                                            >
                                                <ExploreIcon />
                                                See the categories
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </li>
                    );
                })}
                <li className="viz-budget-left">
                    <div className="viz-row">
                        <span className="viz-key">
                            <i className={`viz-swatch ${over ? "bad" : "type-left"}`} />
                            {over ? "Spent beyond your income" : "Left over"}
                        </span>
                        <span className="viz-value">
                            {formatEur(Math.abs(spec.left))}
                            <span className="viz-share">{Math.abs(spec.left_share_pct ?? 0)}&nbsp;%</span>
                        </span>
                    </div>
                    {!over && spec.invested > 0 && (
                        <span className="viz-usual-text">
                            Of this, about {formatEur(spec.invested)} a month goes to investments.
                        </span>
                    )}
                </li>
            </ul>
            {interactive && !open && <p className="viz-hint">Tap a part to see what is in it.</p>}
            <Footer
                spec={spec}
                onAsk={onAsk}
                onExplore={onExplore}
                hideExploreButton={hideExploreButton}
                hideAskButton={hideAskButton}
                question={question ?? "How is my spending split between needs and wants?"}
            />
        </Figure>
    );
}

/* Status with icon and words, never colour alone. */
function Status(props: { ok: boolean; okText: string; badText: string }) {
    return (
        <span className={`viz-status ${props.ok ? "ok" : "bad"}`}>
            <span aria-hidden="true">{props.ok ? "✓" : "!"}</span>
            {props.ok ? props.okText : props.badText}
        </span>
    );
}

function Mortgage({ spec, onAsk, question, hideAskButton }: Actions & { spec: MortgageVisual }) {
    const approved = spec.decision === "approved";
    return (
        <Figure
            title={spec.title}
            subtitle={
                <>
                    Home price <strong>{formatEur(spec.property_price)}</strong>
                </>
            }
        >
            <div className="viz-decision">
                <Status ok={approved} okText="Approved" badText="Not approved" />
                <span className="viz-hint">{spec.approved_pct}&nbsp;% of applications were approved.</span>
            </div>
            {spec.reason && (
                <div className="viz-reason">
                    <strong>{spec.reason.title}</strong>
                    <p>{spec.reason.meaning}</p>
                    <p>
                        <strong>What can help:</strong> {spec.reason.what_helps}
                    </p>
                </div>
            )}
            <PriceSplit price={spec.property_price} loan={spec.loan} downPayment={spec.down_payment} />
            <LtvMeter ltv={spec.ltv} limit={spec.ltv_limit} typical={spec.ltv_typical_approved} />
            <Footer
                spec={spec}
                onAsk={onAsk}
                hideAskButton={hideAskButton}
                question={
                    question ??
                    (approved ? "What would my monthly loan payment be?" : "What could improve my chances next time?")
                }
            />
        </Figure>
    );
}

function Calc({ spec }: { spec: CalcVisual }) {
    const incomeOk = spec.income >= spec.required_income;
    const savingsOk = spec.balance >= spec.down_payment;
    return (
        <Figure
            title={spec.title}
            subtitle={
                <>
                    Home price <strong>{formatEur(spec.property_price)}</strong>
                </>
            }
        >
            <div className="viz-hero">
                <span className="viz-hero-value">
                    {formatEur(spec.monthly_payment)}
                    <span> / month</span>
                </span>
                <span className="viz-hint">
                    for {spec.years} years at {spec.rate_pct}&nbsp;% (example rate). If rates rise to{" "}
                    {spec.stress_rate_pct}&nbsp;%: <strong>{formatEur(spec.stress_payment)}</strong> / month.
                </span>
            </div>
            <PriceSplit price={spec.property_price} loan={spec.loan} downPayment={spec.down_payment} />
            <LtvMeter ltv={spec.ltv} limit={spec.ltv_limit} />
            <ul className="viz-checks">
                <li>
                    <Status ok={incomeOk} okText="Income is enough" badText="Income is too low" />
                    <span>
                        You earn about <strong>{formatEur(spec.income)}</strong> a month. The bank needs about{" "}
                        <strong>{formatEur(spec.required_income)}</strong> for this loan.
                    </span>
                </li>
                <li>
                    <Status ok={savingsOk} okText="Savings cover it" badText="Savings fall short" />
                    <span>
                        The down payment is <strong>{formatEur(spec.down_payment)}</strong>
                        {spec.down_payment_assumed && " (assumed)"}. You have{" "}
                        <strong>{formatEur(spec.balance)}</strong> on your account.
                    </span>
                </li>
            </ul>
            <p className="viz-hint">
                With your income, a home up to about{" "}
                <strong>{formatEur(Math.round(spec.max_price_for_income / 1000) * 1000)}</strong> could fit.{" "}
                {spec.note}
            </p>
        </Figure>
    );
}

function AskIcon() {
    return (
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path
                d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
            />
        </svg>
    );
}

function ExploreIcon() {
    return (
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
    );
}
