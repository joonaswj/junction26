import { useEffect, useState } from "react";
import {
    deleteHousehold,
    getHousehold,
    saveHousehold,
    type HouseholdInfo,
    type HouseholdInput,
} from "../api";

type Props = {
    customerId: string;
    /** Called after the details were saved or removed, so charts can reload. */
    onChange: () => void;
    /** Draw attention to the invitation (a comparison on screen would benefit). */
    highlight?: boolean;
};

const CHILD_OPTIONS = [0, 1, 2, 3, 4];
const DISMISS_KEY = "householdPromptDismissed";

function wasDismissed(): boolean {
    try {
        return sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch {
        return false;
    }
}

/**
 * Optional household details for fairer comparisons: who shares the costs,
 * and roughly how much of the shared costs a partner pays (a slider).
 * Never required. The customer can change or remove their answers any time.
 */
export default function HouseholdCard({ customerId, onChange, highlight }: Props) {
    const [info, setInfo] = useState<HouseholdInfo | null>(null);
    const [editing, setEditing] = useState(false);
    const [dismissed, setDismissed] = useState(wasDismissed);
    const [draft, setDraft] = useState<HouseholdInput>({ partner: false, children: 0, partner_share_pct: 50 });
    const [saving, setSaving] = useState(false);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        getHousehold(customerId)
            .then(setInfo)
            .catch(() => setInfo(null));
    }, [customerId]);

    if (!info) return null;
    const current = info.household;
    const shared = info.shared_categories.map((c) => c.toLowerCase()).join(", ");

    function startEditing() {
        setDraft(
            current
                ? {
                      partner: current.partner,
                      children: current.children,
                      // Keep a sensible slider position if they add a partner later.
                      partner_share_pct: current.partner ? current.partner_share_pct : 50,
                  }
                : { partner: false, children: 0, partner_share_pct: 50 },
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

                {draft.partner && (
                    <fieldset>
                        <legend>
                            <label htmlFor="partner-share">
                                How much of your shared costs does your partner pay?
                            </label>
                        </legend>
                        <p className="slider-value">
                            About <strong>{draft.partner_share_pct}&nbsp;%</strong>
                            <span className="muted">
                                {" "}
                                · you pay about {100 - draft.partner_share_pct}&nbsp;%
                            </span>
                        </p>
                        <input
                            id="partner-share"
                            type="range"
                            min={0}
                            max={info.max_partner_share_pct}
                            step={5}
                            value={draft.partner_share_pct}
                            onChange={(e) => setDraft({ ...draft, partner_share_pct: Number(e.target.value) })}
                        />
                        <div className="slider-ends">
                            <span>I pay everything</span>
                            <span>Partner pays most</span>
                        </div>
                        <p className="muted small">
                            Shared costs are {shared}. Costs like restaurants, clothes or hobbies count as
                            your own.
                        </p>
                    </fieldset>
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
                Your account only shows what you pay yourself. If you share costs with a partner or have
                children at home, tell us and we'll compare you with households like yours. It's optional.
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
