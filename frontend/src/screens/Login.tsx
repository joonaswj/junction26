import { useState, type FormEvent } from "react";
import { customerExists } from "../api";
import { normalizeCustomerId } from "../format";

type Props = { onLogin: (customerId: string) => void };

// Dummy login: enter a customer ID from the dataset, e.g. CUST02868.
export default function Login({ onLogin }: Props) {
    const [input, setInput] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function onSubmit(e: FormEvent) {
        e.preventDefault();
        const id = normalizeCustomerId(input);
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
        </div>
    );
}
