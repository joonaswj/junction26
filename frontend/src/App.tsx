import { useState } from "react";
import "./App.css";
import Chat from "./screens/Chat";
import Home from "./screens/Home";
import Login from "./screens/Login";

type Tab = "home" | "chat";

const SESSION_KEY = "customerId";

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

    function login(id: string) {
        saveSession(id);
        setCustomerId(id);
        setTab("home");
    }

    function logout() {
        saveSession(null);
        setCustomerId(null);
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
                {tab === "home" && <Home customerId={customerId} />}
                {/* Kept mounted so the conversation survives switching tabs. */}
                <div className="tab-panel" hidden={tab !== "chat"}>
                    <Chat key={customerId} customerId={customerId} />
                </div>
            </main>

            <nav className="tabbar">
                <button className={tab === "home" ? "active" : ""} onClick={() => setTab("home")}>
                    <HomeIcon />
                    <span>Overview</span>
                </button>
                <button className={tab === "chat" ? "active" : ""} onClick={() => setTab("chat")}>
                    <ChatIcon />
                    <span>Assistant</span>
                </button>
            </nav>
        </div>
    );
}

function HomeIcon() {
    return (
        <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
            <path
                d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
            />
        </svg>
    );
}

function ChatIcon() {
    return (
        <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
            <path
                d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
            />
        </svg>
    );
}

export default App;
