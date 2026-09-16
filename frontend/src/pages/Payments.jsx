import React, { useEffect, useState } from "react";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";
import { useToast } from "../context/ToastContext";

export default function Payments() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [apps, setApps] = useState([]);
  const [cfg, setCfg] = useState({});
  const [form, setForm] = useState({ job_id: "", worker_id: "", amount: "", password: "" });
  const [pending, setPending] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => Promise.all([api.get("/payments/history"), api.get("/payments/config"), user?.role === "employer" ? api.get("/applications") : Promise.resolve({ data: { data: [] } })])
    .then(([a, b, c]) => { setItems(a.data.data || []); setCfg(b.data.data || {}); setApps(c.data.data || []); })
    .catch((e) => setErr(messageOf(e)))
    .finally(() => setLoading(false));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (cfg.mode !== "razorpay" || document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')) return;
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    return () => script.remove();
  }, [cfg.mode]);

  const start = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/payments/create", { job_id: Number(form.job_id), worker_id: Number(form.worker_id), amount: Number(form.amount) });
      setPending(r.data.data);
      toast.success("Payment initiated");
      load();
    } catch (error) { setErr(messageOf(error)); }
  };
  const confirm = async () => {
    try {
      if (!window.Razorpay || !cfg.key_id) throw new Error("Razorpay Checkout is unavailable. Configure the server keys first.");
      const checkout = new window.Razorpay({
        key: cfg.key_id, amount: pending.razorpay_amount, currency: cfg.currency, name: "LabourLink",
        description: `Payment for job #${pending.job_id}`, order_id: pending.order_id,
        handler: async (response) => {
          await api.post("/payments/confirm", { payment_id: pending.id, ...response });
          toast.success("Payment successful"); setPending(null); load();
        },
        modal: { ondismiss: () => setErr("Razorpay checkout was closed before payment was completed.") },
      });
      checkout.open();
      return;
    } catch (error) { setErr(messageOf(error)); }
  };
  const fail = async () => { await api.post("/payments/fail", { payment_id: pending.id, reason: "Employer reported failure" }); setPending(null); load(); };
  const cancel = async () => { await api.post("/payments/cancel", { payment_id: pending.id }); setPending(null); load(); };

  if (loading) return <div className="page"><Loading /></div>;
  const payableApps = apps.filter((a) => ["Accepted","Assigned","Ongoing","Completed"].includes(a.status));
  return (
    <div className="page">
      <h1>{user?.role === "worker" ? "Earnings" : "Payments"}</h1>
      <p data-testid="payment-gateway-status">Gateway: <b>{cfg.mode}</b> — secure Razorpay checkout and server-side signature verification.</p>
      <ErrorBox text={err} />
      {user?.role === "employer" && (
        <form className="card form-card" onSubmit={start}>
          <h3>Start a payment</h3>
          <select data-testid="payment-job-select" value={form.job_id + ":" + form.worker_id} onChange={(e) => {
            const [job_id, worker_id] = e.target.value.split(":");
            const a = payableApps.find((x) => String(x.job.id) === job_id && String(x.worker.id) === worker_id);
            const amount = (a?.agreed_wage || a?.job?.wage || 0) + (a?.job?.extra_amount || 0);
            setForm({ ...form, job_id, worker_id, amount });
          }}>
            <option value=":">Select assigned job</option>
            {payableApps.map((a) => (
              <option key={a.id} value={a.job.id + ":" + a.worker.id}>{a.job.title} · {a.worker.name} · ₹{(a.agreed_wage || a.job.wage) + (a.job.extra_amount || 0)}</option>
            ))}
          </select>
          <input data-testid="payment-amount-input" type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="Amount" required />
          <button data-testid="payment-initiate-button" className="btn primary">Initiate payment</button>
        </form>
      )}
      {pending && (
        <div className="card form-card">
          <h3>Confirm payment {pending.reference_id}</h3>
          <p>Amount ₹{pending.amount} + fee ₹{pending.fee} = ₹{pending.total}</p>
          <div className="actions">
          <button data-testid="razorpay-checkout-button" className="btn primary" onClick={confirm}>Open Razorpay Checkout</button>
            <button data-testid="payment-cancel-button" className="btn ghost" onClick={cancel}>Cancel</button>
          </div>
        </div>
      )}
      {items.length === 0 ? <Empty title="No payments yet." text="Completed payouts will show transaction IDs here." /> : (
        <div className="grid">{items.map((p) => (
          <div className="card" key={p.id}>
            <Badge>{p.status}</Badge>
            <h3>₹{p.amount} · {p.reference_id}</h3>
            <p>Fee ₹{p.fee} · Total ₹{p.total} · {p.gateway}</p>
            {p.failure_reason && <p>{p.failure_reason}</p>}
          </div>
        ))}</div>
      )}
    </div>
  );
}
