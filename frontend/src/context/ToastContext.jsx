import React, { createContext, useContext, useMemo, useState } from "react";

const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = (text, kind = "info") => {
    const id = Date.now() + Math.random();
    setToasts((list) => [...list, { id, text, kind }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3500);
  };
  const value = useMemo(() => ({ push, success: (t) => push(t, "ok"), error: (t) => push(t, "err") }), []);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-wrap">
        {toasts.map((t) => (
          <div className="toast" key={t.id}>{t.text}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
