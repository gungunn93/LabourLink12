import React, { useEffect, useState } from "react";
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

  useEffect(() => {
    api.get("/conversations").then((r) => setCs(r.data.data || [])).catch((e) => setErr(messageOf(e))).finally(() => setLoading(false));
  }, []);

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
      {cs.length === 0 ? <Empty title="No conversations yet." text="Chat starts after an application or assignment." /> : (
        <div className="message-layout">
          <div className="card">
            {cs.map((c) => (
              <button className={`conversation ${id === c.id ? "active" : ""}`} key={c.id} onClick={() => open(c.id)}>
                <b>{c.other_user?.name || "Conversation"}</b>
                <div>{c.job_title}</div>
                <small>{c.last_message}</small>
              </button>
            ))}
          </div>
          <div className="card">
            <div className="messages">
              {ms.map((m) => (
                <div key={m.id} className={`bubble ${m.sender_id === user.id ? "mine" : "theirs"}`}>
                  {m.text}<br /><small>{m.date}</small>
                </div>
              ))}
            </div>
            {id && (
              <div className="search-row">
                <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Write a message" onKeyDown={(e) => e.key === "Enter" && send()} />
                <button className="btn primary" onClick={send}>Send</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
