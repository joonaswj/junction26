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
    /** Why this difference may simply reflect their household, if they told us. */
    expected_because: string | null;
};

export type Insights = {
    peer_group: string;
    peer_count: number;
    low_activity: boolean;
    insights: Insight[];
};

// What the customer chose to look at in Explore (explore.py).
export type Measure = "spending" | "income" | "saved" | "balance";
export type GroupBy = "month" | "category" | "merchant" | "weekday";
export type CompareWith = "none" | "peers" | "finland";
export type ExploreQuery = {
    measure?: Measure;
    group_by?: GroupBy;
    months?: number;
    categories?: string[];
    compare?: CompareWith;
    month?: string | null; // "2026-01": look inside one month
};

export type DataSource = {
    source: string;
    table: string;
    measure: string;
    year: number;
    url: string;
    license: string;
};

// Shared by every chart: how to open the same view in Explore, and where
// any benchmark in it comes from.
type VisualBase = {
    explore?: ExploreQuery;
    notes?: string[];
    source?: DataSource | null;
};

// Chart specs, built by the backend from the customer's data (visuals.py).
export type BarsVisual = VisualBase & {
    type: "bars";
    title: string;
    subtitle: string;
    total: number;
    show_share?: boolean;
    items: { label: string; value: number }[];
};
export type ColumnsVisual = VisualBase & {
    type: "columns";
    title: string;
    subtitle: string;
    total?: number;
    labels: string[]; // months, "2026-04"
    series: { name: string; values: number[] }[];
    colors?: string[]; // one class per series: s1, s2, peer
};
export type LineVisual = VisualBase & {
    type: "line";
    title: string;
    subtitle: string;
    labels: string[];
    values: number[];
};
export type CompareVisual = VisualBase & {
    type: "compare";
    title: string;
    subtitle: string;
    you_label: string;
    peer_label: string;
    peer_class?: string; // "peer" (grey) or "s2" (Finnish average)
    items: { label: string; you: number; peers: number }[];
    percentile?: number;
};
export type MortgageVisual = VisualBase & {
    type: "mortgage";
    title: string;
    decision: "approved" | "rejected";
    reason: { title: string; meaning: string; what_helps: string } | null;
    property_price: number;
    loan: number;
    down_payment: number;
    ltv: number;
    ltv_limit: number;
    ltv_typical_approved: number;
    approved_pct: number;
};
export type CalcVisual = VisualBase & {
    type: "calc";
    title: string;
    property_price: number;
    down_payment: number;
    down_payment_assumed: boolean;
    loan: number;
    ltv: number;
    ltv_limit: number;
    years: number;
    rate_pct: number;
    monthly_payment: number;
    stress_payment: number;
    stress_rate_pct: number;
    income: number;
    required_income: number;
    current_housing_cost: number;
    balance: number;
    max_price_for_income: number;
    note: string;
};
export type Visual =
    | BarsVisual
    | ColumnsVisual
    | LineVisual
    | CompareVisual
    | MortgageVisual
    | CalcVisual;

export type DashboardVisuals = {
    income_vs_spending: ColumnsVisual;
    spending: BarsVisual;
    peers: CompareVisual;
    mortgage: MortgageVisual | null;
};

export type Guard = "off_topic" | "injection" | "other_customer" | "too_long" | null;

export type ChatMessage = {
    role: "user" | "assistant";
    content: string;
    // Assistant messages only:
    visuals?: Visual[];
    suggestions?: string[];
    guard?: Guard;
};

export type ChatReply = {
    reply: string;
    visuals: Visual[];
    suggestions: string[];
    guard: Guard;
    tools_used: string[];
};

export type Starter = { text: string; why: string; topic: string };
export type ChatStarters = { suggestions: Starter[]; max_message_chars: number };

export type ExploreResult = {
    query: Required<ExploreQuery>;
    visual: Visual;
    table: { columns: string[]; rows: (string | number)[][] };
    summary: string;
    notes: string[];
    source: DataSource | null;
    questions: string[];
    household: Household | null;
    /** True when a comparison would be fairer with household details. */
    household_hint: boolean;
    options: {
        measures: { id: Measure; label: string }[];
        group_by: GroupBy[];
        periods: number[];
        categories: string[];
        compare: CompareWith[];
    };
};

// Optional, self-reported household details (household.py).
export type Household = {
    partner: boolean;
    children: number;
    partner_share_pct: number;
    description: string;
    consumption_units: number;
};
export type HouseholdInfo = {
    household: Household | null;
    shared_categories: string[];
    max_partner_share_pct: number;
};
export type HouseholdInput = Pick<Household, "partner" | "children" | "partner_share_pct">;

async function send<T>(method: "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error(`API request failed: ${response.status} ${path}`);
    return response.json() as Promise<T>;
}

export const getHousehold = (id: string) => get<HouseholdInfo>(`/customers/${id}/household`);
export const saveHousehold = (id: string, input: HouseholdInput) =>
    send<HouseholdInfo>("PUT", `/customers/${id}/household`, input);
export const deleteHousehold = (id: string) =>
    send<HouseholdInfo>("DELETE", `/customers/${id}/household`);

export type Transaction = {
    tx_date: string;
    category: string;
    tx_amount_eur: number;
    merchant_id: string | null;
    balance_after_eur: number;
};

export type MyData = {
    transactions: number;
    first_date: string;
    last_date: string;
    peer_group: string;
    peer_count: number;
    customers_in_dataset: number;
    open_data: DataSource;
};

function queryString(q: ExploreQuery, extra: Record<string, string | number> = {}): string {
    const params = new URLSearchParams();
    if (q.measure) params.set("measure", q.measure);
    if (q.group_by) params.set("group_by", q.group_by);
    if (q.months) params.set("months", String(q.months));
    if (q.categories?.length) params.set("categories", q.categories.join(","));
    if (q.compare) params.set("compare", q.compare);
    if (q.month) params.set("month", q.month);
    for (const [k, v] of Object.entries(extra)) params.set(k, String(v));
    return params.toString();
}

export const getExplore = (id: string, q: ExploreQuery) =>
    get<ExploreResult>(`/customers/${id}/explore?${queryString(q)}`);
export const getExploreTransactions = (id: string, q: ExploreQuery, limit: number) =>
    get<{ total: number; items: Transaction[] }>(
        `/customers/${id}/explore/transactions?${queryString(
            { months: q.months, categories: q.categories, month: q.month },
            { limit },
        )}`,
    );
export const getMyData = (id: string) => get<MyData>(`/customers/${id}/my-data`);
export const exportUrl = (id: string, format: "csv" | "json") =>
    `${API_URL}/customers/${id}/export?format=${format}`;

export const getOverview = (id: string) => get<Overview>(`/customers/${id}/overview`);
export const getInsights = (id: string) => get<Insights>(`/customers/${id}/insights?limit=3`);
export const getDashboardVisuals = (id: string) =>
    get<DashboardVisuals>(`/customers/${id}/visuals`);
export const getChatStarters = (id: string) =>
    get<ChatStarters>(`/customers/${id}/chat/starters`);

type StreamHandlers = {
    onText: (delta: string) => void; // part of the answer arrived
    onStatus: (label: string) => void; // e.g. "Adding up your spending"
};

/**
 * Send the whole conversation and stream the assistant's answer.
 * Resolves with the complete reply (text, charts, next questions).
 */
export async function streamChat(
    customerId: string,
    messages: ChatMessage[],
    handlers: StreamHandlers,
): Promise<ChatReply> {
    const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Only role and content go to the backend, charts stay in the app.
        body: JSON.stringify({
            customer_id: customerId,
            messages: messages.map(({ role, content }) => ({ role, content })),
        }),
    });
    if (!response.ok || !response.body) {
        throw new Error(`Chat failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Server-sent events: one "data: {json}" block per event.
        let end: number;
        while ((end = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, end);
            buffer = buffer.slice(end + 2);
            if (!block.startsWith("data: ")) continue;
            const event = JSON.parse(block.slice(6));
            if (event.type === "text") handlers.onText(event.delta);
            else if (event.type === "tool") handlers.onStatus(event.label);
            else if (event.type === "done") return event as ChatReply;
            else if (event.type === "error") throw new Error(event.message);
        }
    }
    throw new Error("The answer was cut off");
}

// Dummy login: true if the customer exists.
export async function customerExists(id: string): Promise<boolean> {
    const response = await fetch(`${API_URL}/customers/${encodeURIComponent(id)}`);
    if (response.status === 404) return false;
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    return true;
}
