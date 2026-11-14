import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
    getChatStarters,
    streamChat,
    type ChatMessage,
    type ExploreQuery,
    type Starter,
} from "../api";
import Visual from "../charts/Visual";

const FALLBACK_STARTERS: Starter[] = [
    { text: "Where does my money go?", why: "", topic: "spending" },
    { text: "How do I compare with similar customers?", why: "", topic: "peers" },
    { text: "How big a home loan could my income support?", why: "", topic: "mortgage" },
];

const TOPICS = [
    "Your spending, income and savings",
    "How you compare with similar customers and the Finnish average",
    "Home loans and your mortgage application",
];

export type PendingQuestion = { id: number; text: string };

type Props = {
    customerId: string;
    /** A question sent from another screen ("Ask about this"). */
    pending: PendingQuestion | null;
    /** Open a chart from an answer in Explore. */
    onExplore: (query: ExploreQuery) => void;
};

type Streaming = { text: string; status: string };

export default function Chat({ customerId, pending, onExplore }: Props) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [streaming, setStreaming] = useState<Streaming | null>(null);
    const [failed, setFailed] = useState(false);
    const [starters, setStarters] = useState(FALLBACK_STARTERS);
    const [maxChars, setMaxChars] = useState(600);
    const endRef = useRef<HTMLDivElement>(null);
    const questionRef = useRef<HTMLDivElement>(null);
    const busy = useRef(false);
    const handledPending = useRef(0);

    useEffect(() => {
        getChatStarters(customerId)
            .then((s) => {
                setStarters(s.suggestions);
                setMaxChars(s.max_message_chars);
            })
            .catch(() => {
                // Keep the fallback suggestions.
            });
    }, [customerId]);

    // After sending, put the question at the top so the answer is read from
    // its start, instead of jumping to the end of a long answer with a chart.
    const lastRole = messages[messages.length - 1]?.role;
    useEffect(() => {
        if (lastRole === "user") {
            questionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, [messages.length, lastRole]);

    useEffect(() => {
        if (failed) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [failed]);

    const ask = useCallback(
        async (history: ChatMessage[]) => {
            if (busy.current) return;
            busy.current = true;
            setMessages(history);
            setFailed(false);
            setStreaming({ text: "", status: "Thinking" });
            try {
                const reply = await streamChat(customerId, history, {
                    onText: (delta) =>
                        setStreaming((s) => ({ status: "", text: (s?.text ?? "") + delta })),
                    onStatus: (label) => setStreaming((s) => ({ text: s?.text ?? "", status: label })),
                });
                setMessages([
                    ...history,
                    {
                        role: "assistant",
                        content: reply.reply,
                        visuals: reply.visuals,
                        suggestions: reply.suggestions,
                        guard: reply.guard,
                    },
                ]);
            } catch {
                setFailed(true);
            } finally {
                setStreaming(null);
                busy.current = false;
            }
        },
        [customerId],
    );

    const send = useCallback(
        (text: string) => {
            const content = text.trim();
            if (!content || busy.current) return;
            setInput("");
            ask([...messages, { role: "user", content }]);
        },
        [ask, messages],
    );

    // A question handed over from the overview screen.
    useEffect(() => {
        if (pending && pending.id !== handledPending.current && !busy.current) {
            handledPending.current = pending.id;
            send(pending.text);
        }
    }, [pending, send]);

    function onSubmit(e: FormEvent) {
        e.preventDefault();
        send(input);
    }

    function newChat() {
        setMessages([]);
        setFailed(false);
    }

    const waiting = streaming !== null;
    const lastIndex = messages.length - 1;
    const lastUserIndex = messages.findLastIndex((m) => m.role === "user");
    const nearLimit = input.length > maxChars - 100;

    return (
        <div className="chat">
            {messages.length > 0 && (
                <div className="chat-toolbar">
                    <span className="muted small">Your money assistant</span>
                    <button className="link-button" onClick={newChat} disabled={waiting}>
                        New chat
                    </button>
                </div>
            )}

            <div className="messages" role="log" aria-live="polite">
                {messages.length === 0 && !waiting && (
                    <div className="chat-empty">
                        <div className="assistant-avatar" aria-hidden="true">€</div>
                        <h2>Hi! I'm your money assistant</h2>
                        <p className="muted">I can explain your own finances at S-Pankki:</p>
                        <ul className="topics">
                            {TOPICS.map((t) => (
                                <li key={t}>
                                    <span aria-hidden="true">✓</span>
                                    {t}
                                </li>
                            ))}
                        </ul>
                        <p className="chips-label">Picked for you</p>
                        <div className="suggestions">
                            {starters.map((s) => (
                                <button key={s.text} className="suggestion starter" onClick={() => send(s.text)}>
                                    <span>{s.text}</span>
                                    {s.why && <span className="starter-why">{s.why}</span>}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) =>
                    m.role === "user" ? (
                        <div
                            key={i}
                            className="bubble bubble-user"
                            ref={i === lastUserIndex ? questionRef : undefined}
                        >
                            {m.content}
                        </div>
                    ) : (
                        <div key={i} className="assistant-turn">
                            {m.guard ? (
                                <div className="guide">
                                    <span className="guide-icon" aria-hidden="true">i</span>
                                    <div>
                                        <strong>Let's keep to your finances</strong>
                                        <p>{m.content}</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="bubble bubble-assistant">
                                    <RichText text={m.content} />
                                </div>
                            )}
                            {m.visuals?.map((v, vi) => (
                                <div key={vi} className="card chat-visual">
                                    <Visual
                                        spec={v}
                                        onAsk={waiting ? undefined : send}
                                        onExplore={onExplore}
                                        hideAskButton
                                    />
                                </div>
                            ))}
                            {i === lastIndex && !waiting && !!m.suggestions?.length && (
                                <>
                                    <p className="chips-label">
                                        {m.guard ? "Things I can help with" : "Ask next"}
                                    </p>
                                    <Chips items={m.suggestions} onPick={send} />
                                </>
                            )}
                        </div>
                    ),
                )}

                {streaming && (
                    <div className="assistant-turn">
                        {streaming.text ? (
                            <div className="bubble bubble-assistant">
                                <RichText text={streaming.text} />
                            </div>
                        ) : (
                            <div className="bubble bubble-assistant typing">
                                <span className="dots" aria-hidden="true">
                                    <i />
                                    <i />
                                    <i />
                                </span>
                                <span className="muted small">{streaming.status || "Thinking"}…</span>
                            </div>
                        )}
                    </div>
                )}

                {failed && (
                    <div className="chat-error" role="alert">
                        <p>Sorry, I couldn't answer just now.</p>
                        <button className="link-button" onClick={() => ask(messages)}>
                            Try again
                        </button>
                    </div>
                )}
                <div ref={endRef} />
            </div>

            <form className="composer" onSubmit={onSubmit}>
                <div className="composer-row">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about your money…"
                        aria-label="Message to your money assistant"
                        maxLength={maxChars}
                        enterKeyHint="send"
                    />
                    <button type="submit" disabled={!input.trim() || waiting} aria-label="Send">
                        <SendIcon />
                    </button>
                </div>
                <p className="composer-note">
                    {nearLimit
                        ? `${input.length} / ${maxChars} characters`
                        : "Based on your S-Pankki account data. Estimates, not financial advice."}
                </p>
            </form>
        </div>
    );
}

function Chips({ items, onPick }: { items: string[]; onPick: (text: string) => void }) {
    return (
        <div className="suggestions">
            {items.map((s) => (
                <button key={s} className="suggestion" onClick={() => onPick(s)}>
                    {s}
                </button>
            ))}
        </div>
    );
}

/** Minimal formatting for answers: paragraphs, "- " bullet lists and **bold**. */
function RichText({ text }: { text: string }) {
    const blocks: ReactNode[] = [];
    let bullets: string[] = [];
    const flush = () => {
        if (bullets.length) {
            blocks.push(
                <ul key={blocks.length}>
                    {bullets.map((b, i) => (
                        <li key={i}>{bold(b)}</li>
                    ))}
                </ul>,
            );
            bullets = [];
        }
    };
    for (const raw of text.split("\n")) {
        const line = raw.trim();
        const bullet = line.match(/^[-•*]\s+(.*)$/);
        if (bullet) {
            bullets.push(bullet[1]);
        } else {
            flush();
            if (line) blocks.push(<p key={blocks.length}>{bold(line)}</p>);
        }
    }
    flush();
    return <>{blocks}</>;
}

/** Keep "1 234 €" and "31 %" on one line. */
function unbreakable(text: string): string {
    return text.replace(/(\d) (?=\d{3}(\D|$))/g, "$1\u00a0").replace(/(\d) ?(€|%)/g, "$1\u00a0$2");
}

/** **bold** and *emphasis* (shown as bold too: italics read poorly at this size). */
function bold(text: string): ReactNode[] {
    return unbreakable(text)
        .split(/\*\*(.+?)\*\*|\*(.+?)\*/g)
        .filter((part) => part !== undefined)
        .map((part, i) => (i % 2 === 1 ? <strong key={i}>{part}</strong> : part));
}

function SendIcon() {
    return (
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path
                d="M4 12 20 4l-6 16-3-7z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
            />
        </svg>
    );
}
