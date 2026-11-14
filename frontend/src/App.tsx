import { useState } from "react";
import "./App.css";
import type { ExploreQuery } from "./api";
import Chat, { type PendingQuestion } from "./screens/Chat";
import Explore from "./screens/Explore";
import Home from "./screens/Home";
import Login from "./screens/Login";

type Tab = "home" | "explore" | "chat";

const SESSION_KEY = "customerId";
const DEFAULT_VIEW: ExploreQuery = { measure: "spending", group_by: "category", months: 3 };

function loadSession(): string | null {
    try {
        return sessionStorage.getItem(SESSION_KEY);
    } catch {
        return null;
    }
}

function saveSession(id: string | null) {
    try {
        if (id) sessionStorage.setItem(SESSION_KEY, id);
        else sessionStorage.removeItem(SESSION_KEY);
    } catch {
        // Storage can be blocked, login just won't survive a reload.
    }
}

function App() {
    const [customerId, setCustomerId] = useState<string | null>(loadSession);
    const [tab, setTab] = useState<Tab>("home");
    const [pending, setPending] = useState<PendingQuestion | null>(null);
    const [view, setView] = useState<ExploreQuery>(DEFAULT_VIEW);

    // Any chart or button can hand a question to the assistant...
    function askAssistant(text: string) {
        setPending({ id: Date.now(), text });
        setTab("chat");
    }

    // ...or open a view in Explore. A partial view starts from the defaults.
    function openExplore(query: ExploreQuery) {
        setView({ measure: "spending", compare: "none", ...query });
        setTab("explore");
    }

    function login(id: string) {
        saveSession(id);
        setCustomerId(id);
        setView(DEFAULT_VIEW);
        setTab("home");
    }

    function logout() {
        saveSession(null);
        setCustomerId(null);
        setPending(null);
    }

    if (!customerId) {
        return (
            <div className="app">
                <Login onLogin={login} />
            </div>
        );
    }

    return (
        <div className="app">
            <header className="topbar">
                <span className="wordmark">S-Pankki</span>
                <button className="topbar-button" onClick={logout}>
                    Log out
                </button>
            </header>

            <main className="content">
                {tab === "home" && (
                    <Home customerId={customerId} onAsk={askAssistant} onExplore={openExplore} />
                )}
                {tab === "explore" && (
                    <Explore customerId={customerId} query={view} onQuery={setView} onAsk={askAssistant} />
                )}
                {/* Kept mounted so the conversation survives switching tabs. */}
                <div className="tab-panel" hidden={tab !== "chat"}>
                    <Chat key={customerId} customerId={customerId} pending={pending} onExplore={openExplore} />
                </div>
            </main>

            <nav className="tabbar">
                <TabButton active={tab === "home"} onClick={() => setTab("home")} label="Overview">
                    <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />
                </TabButton>
                <TabButton active={tab === "explore"} onClick={() => setTab("explore")} label="Explore">
                    <path d="M4 20V10M10 20V4M16 20v-7M21 20H3" strokeLinecap="round" />
                </TabButton>
                <TabButton active={tab === "chat"} onClick={() => setTab("chat")} label="Assistant">
                    <path d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1z" />
                </TabButton>
            </nav>
        </div>
    );
}

function TabButton(props: { active: boolean; onClick: () => void; label: string; children: React.ReactNode }) {
    return (
        <button
            className={props.active ? "active" : ""}
            onClick={props.onClick}
            aria-current={props.active ? "page" : undefined}
        >
            <svg
                viewBox="0 0 24 24"
                width="24"
                height="24"
                aria-hidden="true"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
            >
                {props.children}
            </svg>
            <span>{props.label}</span>
        </button>
    );
}

export default App;
