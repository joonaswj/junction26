// Backend address. Set VITE_API_URL in frontend/.env.local to override.
// Default: same host as the page, port 8000, so it also works when the app
// is opened on a phone via the laptop's IP address.
const API_URL =
    import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`;

async function get<T>(path: string): Promise<T> {
    const response = await fetch(`${API_URL}${path}`);
    if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${path}`);
    }
    return response.json() as Promise<T>;
}

export type DemoCustomer = {
    customer_id: string;
    age: number;
    peer_group: string;
    mortgage_decision: "approved" | "rejected" | null;
};

export type Overview = {
    customer_id: string;
    age: number;
    data_until: string;
    current_balance_eur: number;
    avg_monthly_income_eur: number;
    avg_monthly_spending_eur: number;
    avg_monthly_invested_eur: number;
    savings_rate_pct: number | null;
    top_categories_last_12_months: { category: string; avg_monthly_eur: number }[];
    peer_group: string;
    low_activity: boolean;
    has_mortgage_application: boolean;
};

export type Insight = {
    category: string;
    you_eur: number;
    peer_median_eur: number;
    diff_eur: number;
    diff_pct: number;
    percentile: number;
    direction: "more" | "less";
    text: string;
};

export type Insights = {
    peer_group: string;
    peer_count: number;
    low_activity: boolean;
    insights: Insight[];
};

export type Spending = {
    months: number;
    until: string;
    total_eur: number;
    by_category_eur: Record<string, number>;
};

export type ChatMessage = { role: "user" | "assistant"; content: string };

export const getDemoCustomers = () => get<DemoCustomer[]>("/demo-customers?limit=10");

export type ChatReply = { reply: string; tools_used: string[] };

// Send the whole conversation, get the assistant's next message.
export async function sendChat(customerId: string, messages: ChatMessage[]): Promise<ChatReply> {
    const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, messages }),
    });
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Chat failed: ${response.status}`);
    }
    return response.json() as Promise<ChatReply>;
}

// Dummy login: true if the customer exists.
export async function customerExists(id: string): Promise<boolean> {
    const response = await fetch(`${API_URL}/customers/${encodeURIComponent(id)}`);
    if (response.status === 404) return false;
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    return true;
}
export const getOverview = (id: string) => get<Overview>(`/customers/${id}/overview`);
export const getInsights = (id: string) => get<Insights>(`/customers/${id}/insights?limit=3`);
export const getSpending = (id: string, months = 3) =>
    get<Spending>(`/customers/${id}/spending?months=${months}`);
