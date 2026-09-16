import React, { useEffect, useRef, useState } from "react";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useSocket } from "../context/SocketContext";
import { Empty, ErrorBox, Loading } from "../components/States";

export default function Messages() {
  const { user } = useAuth();
  const socket = useSocket();
  const [cs, setCs] = useState([]);
  const [id, setId] = useState(null);
  const [ms, setMs] = useState([]);
  const [text, setText] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.get("/conversations")
      .then((r) => setCs(r.data.data || []))
      .catch((e) => setErr(messageOf(e)))
      .finally(() => setLoading(false));
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [ms]);

  useEffect(() => {
    if (!socket || !id) return;
    socket.emit("join_conversation", { conversation_id: id, auth: { token: localStorage.getItem("ll_token") } });
    const handler = (payload) => {
      if (payload.conversation_id === id) setMs((list) => [...list, payload]);
    };
    socket.on("chat:message", handler);
    return () => socket.off("chat:message", handler);
  }, [socket, id]);

  const open = async (x) => {
    setId(x);
    try {
      const r = await api.get("/conversations/" + x + "/messages");
      setMs(r.data.data || []);
    } catch (e) { setErr(messageOf(e)); }
  };

  const send = async () => {
    if (!text.trim() || !id) return;
    try {
      const r = await api.post("/conversations/" + id + "/messages", { text });
      setMs((list) => [...list, r.data.data]);
      setText("");
    } catch (e) { setErr(messageOf(e)); }
  };

  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <h1>Messages</h1>
      <ErrorBox text={err} />
      {cs.length === 0 ? (
        <Empty title="No conversations yet." text="Chat starts after an application or assignment." />
      ) : (
        <div className="message-layout">
          <div className="card">
            {cs.map((c) => (
              <button
                className={`conversation ${id === c.id ? "active" : ""}`}
                key={c.id}
                onClick={() => open(c.id)}
              >
                <b>{c.other_user?.name || "Conversation"}</b>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{c.job_title}</div>
                <small style={{ color: "var(--muted)" }}>{c.last_message}</small>
              </button>
            ))}
          </div>
          <div className="card" style={{ display: "flex", flexDirection: "column" }}>
            {!id ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--muted)" }}>
                Select a conversation to start chatting
              </div>
            ) : (
              <>
                <div className="messages">
                  {ms.map((m) => (
                    <div key={m.id} className={`bubble ${m.sender_id === user.id ? "mine" : "theirs"}`}>
                      <span>{m.text}</span>
                      <div className="bubble-meta">
                        <small>{m.date ? new Date(m.date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}</small>
                        {/* Tick marks — only show for own messages */}
                        {m.sender_id === user.id && (
                          <span className={`tick ${m.is_read ? "tick-read" : "tick-sent"}`} title={m.is_read ? "Seen" : "Sent"}>
                            {m.is_read ? "✓✓" : "✓"}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={bottomRef} />
                </div>
                <div className="search-row" style={{ marginTop: "auto", borderTop: "1px solid var(--line)", paddingTop: 10 }}>
                  <input
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Write a message…"
                    onKeyDown={(e) => e.key === "Enter" && send()}
                    style={{ flex: 1 }}
                  />
                  <button className="btn primary" onClick={send}>Send</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
