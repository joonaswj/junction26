import { useEffect, useState } from "react";
import { getDemoCustomers, type DemoCustomer } from "../api";

type Props = { onLogin: (customerId: string) => void };

// Dummy login: pick one of the demo customers.
export default function Login({ onLogin }: Props) {
    const [customers, setCustomers] = useState<DemoCustomer[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        getDemoCustomers()
            .then(setCustomers)
            .catch(() => setError("Could not connect to the backend. Is it running?"));
    }, []);

    return (
        <div className="screen login">
            <div className="login-header">
                <h1>Money assistant</h1>
                <p>Demo: choose a customer to log in as.</p>
            </div>

            {error && <p className="error">{error}</p>}
            {!customers && !error && <p className="muted">Loading…</p>}

            <ul className="customer-list">
                {customers?.map((c) => (
                    <li key={c.customer_id}>
                        <button className="customer" onClick={() => onLogin(c.customer_id)}>
                            <span className="customer-id">{c.customer_id}</span>
                            <span className="muted">
                                Age {c.age} · {c.peer_group.split(", ").pop()}
                            </span>
                            {c.mortgage_decision && (
                                <span className={`tag tag-${c.mortgage_decision}`}>
                                    Mortgage {c.mortgage_decision}
                                </span>
                            )}
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
