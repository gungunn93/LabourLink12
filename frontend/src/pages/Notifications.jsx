import React, { useEffect, useState } from "react";
import api, { messageOf } from "../services/api";
import { useSocket } from "../context/SocketContext";
import { Empty, ErrorBox, Loading } from "../components/States";

export default function Notifications() {
  const socket = useSocket();
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => api.get("/notifications").then((r) => setItems(r.data.data || [])).catch((e) => setErr(messageOf(e))).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!socket) return;
    const handler = (n) => setItems((list) => [n, ...list]);
    socket.on("notification:new", handler);
    return () => socket.off("notification:new", handler);
  }, [socket]);
  const read = async (id) => { await api.put("/notifications/" + id + "/read"); load(); };
  const all = async () => { await api.put("/notifications/read-all"); load(); };
  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <div className="job-head"><h1>Notifications</h1><button className="btn ghost" onClick={all}>Mark all read</button></div>
      <ErrorBox text={err} />
      {items.length === 0 ? <Empty title="No notifications yet." text="Applications, chats, payments and offers will appear here." /> : items.map((n) => (
        <div className="card" key={n.id} style={{ marginBottom: 10, opacity: n.is_read ? 0.7 : 1 }}>
          <h3>{n.title}</h3>
          <p>{n.message}</p>
          <small>{n.kind} · {n.date}</small>
          {!n.is_read && <div><button className="btn ghost" onClick={() => read(n.id)}>Mark as read</button></div>}
        </div>
      ))}
    </div>
  );
}
