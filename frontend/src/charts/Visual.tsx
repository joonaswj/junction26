import { useState, type ReactNode } from "react";
import type {
    BarsVisual,
    CalcVisual,
    ColumnsVisual,
    CompareVisual,
    LineVisual,
    MortgageVisual,
    Visual as VisualSpec,
} from "../api";
import { formatEur, formatMonth, formatMonthYear, formatPct } from "../format";
import "./charts.css";

/** Draws one chart spec from the backend. Used on the overview and in chat. */
export default function Visual({ spec }: { spec: VisualSpec }) {
    switch (spec.type) {
        case "bars":
            return <Bars spec={spec} />;
        case "columns":
            return <Columns spec={spec} />;
        case "line":
            return <Line spec={spec} />;
        case "compare":
            return <Compare spec={spec} />;
        case "mortgage":
            return <Mortgage spec={spec} />;
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

/* Horizontal bars: one value per category, every bar labelled. */
function Bars({ spec }: { spec: BarsVisual }) {
    const max = Math.max(...spec.items.map((i) => i.value), 1);
    return (
        <Figure
            title={spec.title}
            subtitle={
                <>
                    {spec.subtitle} <strong>{formatEur(spec.total)}</strong>
                </>
            }
        >
            <ul className="viz-bars">
                {spec.items.map((item) => (
                    <li key={item.label}>
                        <div className="viz-row">
                            <span>{item.label}</span>
                            <span className="viz-value">
                                {formatEur(item.value)}
                                <span className="viz-share">
                                    {Math.round((item.value / spec.total) * 100)}&nbsp;%
                                </span>
                            </span>
                        </div>
                        <div className="viz-track">
                            <div
                                className="viz-fill s1"
                                style={{ width: `${(item.value / max) * 100}%` }}
                            />
                        </div>
                    </li>
                ))}
            </ul>
        </Figure>
    );
}

/* Columns over months, 1-2 series. Tap a month to read its values. */
function Columns({ spec }: { spec: ColumnsVisual }) {
    const [selected, setSelected] = useState(spec.labels.length - 1);
    const max = Math.max(...spec.series.flatMap((s) => s.values), 1);
    const single = spec.series.length === 1;
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
                <span className="viz-readout-month">{formatMonthYear(spec.labels[selected])}</span>
                {spec.series.map((s, si) => (
                    <span key={s.name} className="viz-key">
                        <i className={`viz-swatch s${si + 1}`} />
                        {!single && `${s.name} `}
                        <strong>{formatEur(s.values[selected])}</strong>
                    </span>
                ))}
            </div>
            <div className="viz-columns">
                {spec.labels.map((label, i) => (
                    <button
                        key={label}
                        type="button"
                        className={`viz-month${i === selected ? " selected" : ""}`}
                        onClick={() => setSelected(i)}
                        onMouseEnter={() => setSelected(i)}
                        aria-label={`${formatMonthYear(label)}: ${spec.series
                            .map((s) => `${s.name} ${formatEur(s.values[i])}`)
                            .join(", ")}`}
                    >
                        <span className="viz-plot">
                            {spec.series.map((s, si) => (
                                <span
                                    key={s.name}
                                    className={`viz-column s${si + 1}`}
                                    style={{ height: `${Math.max((s.values[i] / max) * 100, 1)}%` }}
                                />
                            ))}
                        </span>
                        <span className="viz-tick">{formatMonth(label)}</span>
                    </button>
                ))}
            </div>
            <p className="viz-hint">Tap a month to see its numbers.</p>
        </Figure>
    );
}

/* One value over months (balance). Tap a month to read its value. */
function Line({ spec }: { spec: LineVisual }) {
    const n = spec.values.length;
    const [selected, setSelected] = useState(n - 1);
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
                <span className="viz-readout-month">{formatMonthYear(spec.labels[selected])}</span>
                <span className="viz-key">
                    <i className="viz-swatch s1" />
                    <strong>{formatEur(spec.values[selected])}</strong>
                </span>
            </div>
            <div className="viz-line">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                    <polygon className="viz-area" points={`0,100 ${points} 100,100`} />
                    <polyline className="viz-stroke" points={points} />
                </svg>
                <span
                    className="viz-dot"
                    style={{ left: `${x(selected)}%`, top: `${y(spec.values[selected])}%` }}
                />
                <div className="viz-hits">
                    {spec.labels.map((label, i) => (
                        <button
                            key={label}
                            type="button"
                            onClick={() => setSelected(i)}
                            onMouseEnter={() => setSelected(i)}
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
                {change >= 0 ? "Up" : "Down"} {formatEur(Math.abs(change))} over the period. Tap the
                chart to see a month.
            </p>
        </Figure>
    );
}

/* You vs similar customers: you in green, peers in grey. */
function Compare({ spec }: { spec: CompareVisual }) {
    const max = Math.max(...spec.items.flatMap((i) => [i.you, i.peers]), 1);
    return (
        <Figure title={spec.title} subtitle={spec.subtitle}>
            <div className="viz-legend">
                <span className="viz-key">
                    <i className="viz-swatch s1" />
                    {spec.you_label}
                </span>
                <span className="viz-key">
                    <i className="viz-swatch peer" />
                    {spec.peer_label}
                </span>
            </div>
            <ul className="viz-compare">
                {spec.items.map((item) => (
                    <li key={item.label}>
                        <span className="viz-compare-label">{item.label}</span>
                        <CompareBar className="s1" value={item.you} max={max} name={spec.you_label} />
                        <CompareBar
                            className="peer"
                            value={item.peers}
                            max={max}
                            name={spec.peer_label}
                        />
                    </li>
                ))}
            </ul>
            {spec.percentile !== undefined && <Position percentile={spec.percentile} />}
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

/* Status with icon and words, never colour alone. */
function Status(props: { ok: boolean; okText: string; badText: string }) {
    return (
        <span className={`viz-status ${props.ok ? "ok" : "bad"}`}>
            <span aria-hidden="true">{props.ok ? "✓" : "!"}</span>
            {props.ok ? props.okText : props.badText}
        </span>
    );
}

function Mortgage({ spec }: { spec: MortgageVisual }) {
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
                <span className="viz-hint">
                    {spec.approved_pct}&nbsp;% of applications were approved.
                </span>
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
                        You earn about <strong>{formatEur(spec.income)}</strong> a month. The bank
                        needs about <strong>{formatEur(spec.required_income)}</strong> for this loan.
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
                <strong>{formatEur(Math.round(spec.max_price_for_income / 1000) * 1000)}</strong> could fit. {spec.note}
            </p>
        </Figure>
    );
}
