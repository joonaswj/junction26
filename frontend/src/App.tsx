import { useState } from "react";
import "./App.css";
import Chat from "./screens/Chat";
import Home from "./screens/Home";
import Login from "./screens/Login";

type Tab = "home" | "chat";

function App() {
    const [customerId, setCustomerId] = useState<string | null>(null);
    const [tab, setTab] = useState<Tab>("home");

    if (!customerId) {
        return (
            <div className="app">
                <Login onLogin={(id) => { setCustomerId(id); setTab("home"); }} />
            </div>
        );
    }

    return (
        <div className="app">
            <header className="topbar">
                <span className="topbar-title">{tab === "home" ? "Overview" : "Assistant"}</span>
                <button className="link" onClick={() => setCustomerId(null)}>
                    Log out
                </button>
            </header>

            <main className="content">
                {tab === "home" ? <Home customerId={customerId} /> : <Chat />}
            </main>

            <nav className="tabbar">
                <button className={tab === "home" ? "active" : ""} onClick={() => setTab("home")}>
                    Overview
                </button>
                <button className={tab === "chat" ? "active" : ""} onClick={() => setTab("chat")}>
                    Assistant
                </button>
            </nav>
        </div>
    );
}

export default App;
