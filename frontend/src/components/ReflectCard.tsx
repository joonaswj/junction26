import { useState } from "react";
import type { BudgetVisual } from "../api";
import { formatEur } from "../format";

type Props = {
    budget: BudgetVisual;
    onAsk: (question: string) => void;
};

/**
 * A pause to think, not a verdict. It shows free-choice spending as a yearly
 * amount (a year makes small habits visible), lets the customer try "what if
 * I trimmed this", and asks whether the split feels right to them. Only they
 * can answer that. If they want a change, the assistant picks it up.
 */
export default function ReflectCard({ budget, onAsk }: Props) {
    const [trim, setTrim] = useState(10);
    const [answer, setAnswer] = useState<"right" | null>(null);
    const free = budget.segments.find((s) => s.key === "free");
    if (!free || free.value <= 0) return null;

    const yearly = free.value * 12;
    const saved = (yearly * trim) / 100;
    const biggest = free.items.filter((i) => i.value > 0).slice(0, 3);
    const over = budget.left < 0;

    return (
        <section className="card reflect">
            <span className="reflect-kicker">A moment to reflect</span>
            <p className="reflect-lead">
                Your free-choice spending is {formatEur(free.value)} a month. Over a year that adds up to{" "}
                <strong>{formatEur(yearly)}</strong>.
            </p>
            <ul className="reflect-list">
                {biggest.map((i) => (
                    <li key={i.label}>
                        <span>{i.label}</span>
                        <span>
                            <strong>{formatEur(i.yearly)}</strong> a year
                        </span>
                    </li>
                ))}
            </ul>

            <div className="reflect-whatif">
                <label htmlFor="trim">What if you trimmed it by {trim}&nbsp;%?</label>
                <input
                    id="trim"
                    type="range"
                    min={0}
                    max={50}
                    step={5}
                    value={trim}
                    onChange={(e) => setTrim(Number(e.target.value))}
                />
                <p>
                    {trim === 0 ? (
                        "Move the slider to try a change."
                    ) : (
                        <>
                            You would keep <strong>{formatEur(saved)}</strong> more a year (
                            {formatEur(saved / 12)} a month).
                        </>
                    )}
                </p>
            </div>

            {over ? (
                <>
                    <p className="reflect-question">
                        In an average month you spend {formatEur(-budget.left)} more than you earn.
                    </p>
                    <button className="btn-primary" onClick={() => onAsk("How can I stop spending more than I earn?")}>
                        Help me turn this around
                    </button>
                </>
            ) : answer === "right" ? (
                <p className="reflect-ack">
                    Good to know. Checking in on your numbers now and then is what keeps it that way.
                </p>
            ) : (
                <>
                    <p className="reflect-question">Does this feel right for you?</p>
                    <div className="button-row">
                        <button className="btn-secondary" onClick={() => setAnswer("right")}>
                            Yes, it feels right
                        </button>
                        <button
                            className="btn-primary"
                            onClick={() =>
                                onAsk(
                                    trim > 0
                                        ? `How could I reduce my free-choice spending by about ${trim} %?`
                                        : "How could I reduce my free-choice spending?",
                                )
                            }
                        >
                            I'd change it
                        </button>
                    </div>
                </>
            )}
        </section>
    );
}
