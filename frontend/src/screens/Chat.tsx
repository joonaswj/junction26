import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatMessage } from "../api";

const SUGGESTIONS = [
    "Where does my money go?",
    "How do I compare to similar users?",
    "How much did I spend on restaurants last month?",
];

// Chat UI only. Messages are shown but not sent to the backend yet.
// To connect: POST { customer_id, messages } to /chat and append the reply.
export default function Chat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    function send(text: string) {
        const content = text.trim();
        if (!content) return;
        setMessages((m) => [...m, { role: "user", content }]);
        setInput("");
    }

    function onSubmit(e: FormEvent) {
        e.preventDefault();
        send(input);
    }

    return (
        <div className="chat">
            <div className="messages">
                {messages.length === 0 && (
                    <div className="chat-empty">
                        <div className="assistant-avatar" aria-hidden="true">€</div>
                        <h2>Hi! I'm your money assistant</h2>
                        <p className="muted">
                            Ask me about your spending, your income or how you compare with people
                            like you.
                        </p>
                        <div className="suggestions">
                            {SUGGESTIONS.map((s) => (
                                <button key={s} className="suggestion" onClick={() => send(s)}>
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                {messages.map((m, i) => (
                    <div key={i} className={`bubble bubble-${m.role}`}>
                        {m.content}
                    </div>
                ))}
                <div ref={endRef} />
            </div>

            <form className="composer" onSubmit={onSubmit}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask something…"
                    aria-label="Message"
                />
                <button type="submit" disabled={!input.trim()}>
                    Send
                </button>
            </form>
        </div>
    );
}
