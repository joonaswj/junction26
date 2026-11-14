import { useState, type FormEvent } from "react";
import { customerExists } from "../api";
import { normalizeCustomerId } from "../format";

type Props = { onLogin: (customerId: string) => void };

// Demo customers for judges: each shows off a different part of the app.
const DEMO_USERS = [
    {
        id: "CUST02868",
        title: "Steady saver with a mortgage",
        try: "Approved mortgage, a heavy January to explore, ready to start investing.",
    },
    {
        id: "CUST00013",
        title: "Partner pays the groceries",
        try: "Rejected mortgage explained. Add household details and watch comparisons change.",
    },
    {
        id: "CUST04081",
        title: "Spending more than they earn",
        try: "31 years old, free-choice spending at 41 %. The reflection card and assistant help.",
    },
    {
        id: "CUST04323",
        title: "Saving for a first home",
        try: "31 years old, saves 22 %. Try the home loan estimate and investing basics.",
    },
    {
        id: "CUST00001",
        title: "Already investing",
        try: "Invests monthly, high health costs. Compare with the Finnish average.",
    },
];

// Dummy login: enter a customer ID from the dataset, e.g. CUST02868.
export default function Login({ onLogin }: Props) {
    const [input, setInput] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function onSubmit(e: FormEvent) {
        e.preventDefault();
        await login(normalizeCustomerId(input));
    }

    async function login(id: string) {
        if (!id) return;
        setLoading(true);
        setError(null);
        try {
            if (await customerExists(id)) {
                onLogin(id);
            } else {
                setError("We couldn't find that customer ID. Check it and try again.");
            }
        } catch {
            setError("Something went wrong. Please try again in a moment.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="login">
            <div className="login-hero">
                <span className="wordmark">S-Pankki</span>
                <h1>Welcome</h1>
                <p>Log in to see your finances and chat with your money assistant.</p>
            </div>

            <form className="login-form" onSubmit={onSubmit}>
                <label htmlFor="customer-id">Customer ID</label>
                <input
                    id="customer-id"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="e.g. CUST02868"
                    autoComplete="username"
                    autoCapitalize="characters"
                    autoFocus
                />
                {error && <p className="form-error">{error}</p>}
                <button className="btn-primary" type="submit" disabled={!input.trim() || loading}>
                    {loading ? "Logging in…" : "Log in"}
                </button>
            </form>

            <section className="demo-users" aria-label="Demo customers">
                <p className="chips-label">Demo: log in as</p>
                {DEMO_USERS.map((u) => (
                    <button key={u.id} className="demo-user" disabled={loading} onClick={() => login(u.id)}>
                        <span className="demo-user-title">{u.title}</span>
                        <span className="demo-user-try">{u.try}</span>
                        <span className="demo-user-id">{u.id}</span>
                    </button>
                ))}
            </section>
        </div>
    );
}
