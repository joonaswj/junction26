import { useEffect, useState } from "react";
import {
    deleteHousehold,
    getHousehold,
    saveHousehold,
    type HouseholdInfo,
    type HouseholdInput,
} from "../api";
import { formatEur } from "../format";

type Props = {
    customerId: string;
    /** Called after the details were saved or removed, so charts can reload. */
    onChange: () => void;
    /** Draw attention to the invitation (a comparison on screen would benefit). */
    highlight?: boolean;
};

const CHILD_OPTIONS = [0, 1, 2, 3, 4];
const DISMISS_KEY = "householdPromptDismissed";
const EMPTY: HouseholdInput = {
    partner: false,
    children: 0,
    partner_housing_pct: 50,
    partner_groceries_pct: 50,
    partner_utilities_pct: 50,
};
// The costs a couple shares, each with its own slider.
const SLIDERS = [
    { field: "partner_housing_pct", category: "Housing", label: "housing" },
    { field: "partner_groceries_pct", category: "Groceries", label: "groceries" },
    { field: "partner_utilities_pct", category: "Utilities", label: "utilities" },
] as const;

function wasDismissed(): boolean {
    try {
        return sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch {
        return false;
    }
}

/**
 * Optional household details for fairer comparisons: who shares the costs,
 * and roughly how much of the housing, groceries and utilities a partner
 * pays (one slider each, because couples often split them differently).
 * Never required. The customer can change or remove their answers any time.
 */
export default function HouseholdCard({ customerId, onChange, highlight }: Props) {
    const [info, setInfo] = useState<HouseholdInfo | null>(null);
    const [editing, setEditing] = useState(false);
    const [dismissed, setDismissed] = useState(wasDismissed);
    const [draft, setDraft] = useState<HouseholdInput>(EMPTY);
    const [saving, setSaving] = useState(false);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        getHousehold(customerId)
            .then(setInfo)
            .catch(() => setInfo(null));
    }, [customerId]);

    if (!info) return null;
    const current = info.household;

    function startEditing() {
        setDraft(
            current?.partner
                ? {
                      partner: true,
                      children: current.children,
                      partner_housing_pct: current.partner_housing_pct,
                      partner_groceries_pct: current.partner_groceries_pct,
                      partner_utilities_pct: current.partner_utilities_pct,
                  }
                : // Keep the sliders in the middle in case they add a partner.
                  { ...EMPTY, children: current?.children ?? 0 },
        );
        setFailed(false);
        setEditing(true);
    }

    async function apply(action: () => Promise<HouseholdInfo>) {
        setSaving(true);
        setFailed(false);
        try {
            setInfo(await action());
            setEditing(false);
            onChange();
        } catch {
            setFailed(true);
        } finally {
            setSaving(false);
        }
    }

    function dismiss() {
        try {
            sessionStorage.setItem(DISMISS_KEY, "1");
        } catch {
            // Not being able to remember this is fine.
        }
        setDismissed(true);
    }

    if (editing) {
        return (
            <section className="card household">
                <strong>Your household</strong>
                <p className="muted small">
                    Optional. A rough answer is fine, and you can change or remove it any time.
                </p>

                <fieldset>
                    <legend>Do you live with a partner?</legend>
                    <div className="chips">
                        <Choice active={!draft.partner} onClick={() => setDraft({ ...draft, partner: false })}>
                            No
                        </Choice>
                        <Choice active={draft.partner} onClick={() => setDraft({ ...draft, partner: true })}>
                            Yes
                        </Choice>
                    </div>
                </fieldset>

                <fieldset>
                    <legend>Children living at home</legend>
                    <div className="chips">
                        {CHILD_OPTIONS.map((n) => (
                            <Choice
                                key={n}
                                active={Math.min(draft.children, 4) === n}
                                onClick={() => setDraft({ ...draft, children: n })}
                            >
                                {n === 4 ? "4+" : n}
                            </Choice>
                        ))}
                    </div>
                </fieldset>

                {draft.partner &&
                    SLIDERS.map(({ field, category, label }) => {
                        const pct = draft[field];
                        const mine = info.my_monthly_eur[category] ?? 0;
                        // What the slider position means for the whole household, in euros.
                        const household = mine / (1 - pct / 100);
                        return (
                            <fieldset key={field}>
                                <legend>
                                    <label htmlFor={field}>How much of the {label} does your partner pay?</label>
                                </legend>
                                <p className="slider-value">
                                    About <strong>{pct}&nbsp;%</strong>
                                </p>
                                <input
                                    id={field}
                                    type="range"
                                    min={0}
                                    max={info.max_partner_share_pct}
                                    step={5}
                                    value={pct}
                                    onChange={(e) => setDraft({ ...draft, [field]: Number(e.target.value) })}
                                />
                                <div className="slider-ends">
                                    <span>I pay it all</span>
                                    <span>Partner pays most</span>
                                </div>
                                <p className="slider-preview">
                                    You pay <strong>{formatEur(mine)}</strong> a month for {label}, so your household
                                    pays about <strong>{formatEur(household)}</strong>
                                    {pct > 0 && <> ({formatEur(household - mine)} from your partner)</>}.
                                </p>
                            </fieldset>
                        );
                    })}
                {draft.partner && (
                    <p className="muted small">
                        Only housing, groceries and utilities count as shared. Everything else is treated
                        as your own spending.
                    </p>
                )}

                {failed && <p className="form-error">We couldn't save that. Please try again.</p>}
                <div className="button-row">
                    <button
                        className="btn-primary"
                        disabled={saving}
                        onClick={() => apply(() => saveHousehold(customerId, draft))}
                    >
                        {saving ? "Saving…" : "Save"}
                    </button>
                    <button className="btn-secondary" disabled={saving} onClick={() => setEditing(false)}>
                        Cancel
                    </button>
                </div>
                {current && (
                    <button
                        className="link-button danger"
                        disabled={saving}
                        onClick={() => apply(() => deleteHousehold(customerId))}
                    >
                        Remove my answers
                    </button>
                )}
            </section>
        );
    }

    if (current) {
        return (
            <section className="card household set">
                <div>
                    <strong>Your household</strong>
                    <p className="muted small">{current.description} Comparisons take this into account.</p>
                </div>
                <button className="link-button" onClick={startEditing}>
                    Edit
                </button>
            </section>
        );
    }

    if (dismissed && !highlight) return null;
    return (
        <section className={`card household invite${highlight ? " highlight" : ""}`}>
            <strong>Make your comparisons fairer</strong>
            <p className="muted small">
                Your account only shows what you pay yourself. If you share housing, groceries or bills
                with a partner, or have children at home, tell us and we'll compare you with households like
                yours. It's optional.
            </p>
            <div className="button-row">
                <button className="btn-primary" onClick={startEditing}>
                    Add details
                </button>
                {!highlight && (
                    <button className="btn-secondary" onClick={dismiss}>
                        Not now
                    </button>
                )}
            </div>
        </section>
    );
}

function Choice(props: { active: boolean; onClick: () => void; children: React.ReactNode }) {
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
