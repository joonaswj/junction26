import { useEffect, useRef, useState, type FormEvent } from "react";
import { sendChat, type ChatMessage } from "../api";

const SUGGESTIONS = [
    "Where does my money go?",
    "How do I compare to similar users?",
    "How much did I spend on restaurants last month?",
];

type Props = { customerId: string };

export default function Chat({ customerId }: Props) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [waiting, setWaiting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, waiting, error]);

    async function send(text: string) {
        const content = text.trim();
        if (!content || waiting) return;
        const history: ChatMessage[] = [...messages, { role: "user", content }];
        setMessages(history);
        setInput("");
        setError(null);
        setWaiting(true);
        try {
            const { reply } = await sendChat(customerId, history);
            setMessages([...history, { role: "assistant", content: reply }]);
        } catch {
            setError("Sorry, I couldn't answer right now. Please try again.");
        } finally {
            setWaiting(false);
        }
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
                {waiting && (
                    <div className="bubble bubble-assistant typing" aria-label="Assistant is typing">
                        <span />
                        <span />
                        <span />
                    </div>
                )}
                {error && <p className="form-error chat-error">{error}</p>}
                <div ref={endRef} />
            </div>

            <form className="composer" onSubmit={onSubmit}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask something…"
                    aria-label="Message"
                />
                <button type="submit" disabled={!input.trim() || waiting}>
                    Send
                </button>
            </form>
        </div>
    );
}
