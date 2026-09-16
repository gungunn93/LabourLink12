# Deployment (do this only after local run works)

Free-tier architecture that matches this codebase:

| Piece | Suggested free host | Notes |
| --- | --- | --- |
| Frontend | Cloudflare Pages, Netlify, or Vercel | Static `npm run build` |
| Backend | Render free web service | Python, `socketio.run` or gunicorn + eventlet later |
| Database | [Neon](https://neon.tech) or [Supabase](https://supabase.com) PostgreSQL | Free tier; SSL required |

## Frontend

Build:

```powershell
cd frontend
npm install
npm run build
```

Environment:

```
VITE_API_URL=https://labourlink-api.onrender.com/api
VITE_SOCKET_URL=https://labourlink-api.onrender.com
```

Set the backend `FRONTEND_ORIGIN` to the exact Pages/Netlify URL (`https://xxx.pages.dev`). HTTPS is provided by the host.

## Backend

Start command (Render):

```
pip install -r requirements.txt
python app.py
```

Better production command once you add a process manager:

```
gunicorn -k eventlet -w 1 app:app
```

(eventlet on Windows local is optional; Render Linux is fine.)

Required env vars: `DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY`, `APP_ENV=production`, `FRONTEND_ORIGIN`, `OTP_PROVIDER`, payment keys if using Razorpay.

`DATABASE_URL` from Neon often needs `?sslmode=require`.

On first boot the app still runs `create_all()` + seed. Disable seed in a real production fork if you do not want demo users.

## CORS and WebSockets

- REST: Flask-CORS using `FRONTEND_ORIGIN`
- Socket.IO: same origin list. On Render, use the public HTTPS URL as `VITE_SOCKET_URL`. Some free hosts sleep; the first Socket.IO connect may wait for a cold start.

## OTP / payments in production

- OTP: `OTP_PROVIDER=twilio` or `msg91` plus provider keys. Dev inbox is **disabled** when `APP_ENV=production`.
- Payments: Razorpay test keys for the viva/demo; live keys need business KYC. Sandbox password-confirm remains available if you keep `PAYMENT_GATEWAY=sandbox`.

## Maps

No key. OpenStreetMap tiles are subject to [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/). Fine for a college demo; heavy public traffic should use a tile proxy.

## Limitations of free hosts

Render free web services spin down. Neon free compute can also pause. This is acceptable for a project demo, not for a commercial SLA.
