# LabourLink — Smart Daily Wage Employment Platform

Full-stack marketplace connecting daily-wage workers with employers. This repository is a working local prototype suitable for a final-year demonstration: real database records, JWT auth, OTP verification, negotiation history, Socket.IO chat/location, and a sandbox (or Razorpay test) payment workflow.

## Architecture

- `frontend/` — React 18 + Vite
- `backend/` — Flask API + Flask-SocketIO
- Database — PostgreSQL (preferred) or SQLite
- Maps — Leaflet + OpenStreetMap (no Google Maps key)
- Realtime — Socket.IO (chat, notifications, assigned-job location)

## 1. Prerequisites

- Python 3.11+ (3.13 is fine)
- Node.js 18+
- PostgreSQL 14+ **or** skip it and use SQLite

## 2. Environment variables

Copy `backend/.env.example` to `backend/.env` (already present if you used the project `.env`).

Important variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgresql://USER:PASSWORD@localhost:5432/LabourLink` or `sqlite:///labourlink_dev.db` |
| `JWT_SECRET_KEY` / `SECRET_KEY` | Sign tokens. Change before any public deploy. |
| `APP_ENV` | `development` or `production` |
| `FRONTEND_ORIGIN` | Frontend origin for CORS (`http://localhost:5173` locally) |
| `OTP_PROVIDER` | `dev`, `twilio`, or `msg91` |
| `TWILIO_*` / `MSG91_*` | Required only for real SMS |
| `PAYMENT_GATEWAY` | `sandbox` or `razorpay` |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Razorpay test/live keys (never put the secret in frontend) |
| `MAP_CONFIG` | OSM tile URL |

### OTP honesty

- **`OTP_PROVIDER=dev` (default for students):** backend generates a cryptographically random 6-digit OTP, **hashes** it, stores expiry, enforces cooldown and one-time use. Delivery is the **development OTP inbox** at `http://localhost:5173/dev/otp-inbox` (also `GET /api/auth/dev/otp-inbox`). This is **not** SMS. It is a real verification protocol with a local delivery channel.
- **Production SMS:** set `OTP_PROVIDER=twilio` (Twilio trial can send to verified numbers) or `msg91`. Both eventually require a paid/verified account for unrestricted Indian SMS. There is no unlimited free public SMS API that is reliable for production.

### Payments honesty

- **`PAYMENT_GATEWAY=sandbox`:** creates `Initiated` / `Paid` / `Failed` / `Cancelled` rows, unique `reference_id`, amount checks, duplicate protection, wallet credit **only after the employer re-enters their password**. This is **not** a bank or UPI transfer.
- **`PAYMENT_GATEWAY=razorpay`:** creates a Razorpay order and verifies the checkout signature. Use [Razorpay test keys](https://razorpay.com) without charging real money. Live mode needs KYC/business verification and is paid-adjacent.

## 3. Database

PostgreSQL:

```sql
CREATE DATABASE "LabourLink";
```

Tables are created automatically on first backend start (`db.create_all` + column sync). No separate migration command is required for this project.

If PostgreSQL is not installed, set:

```
DATABASE_URL=sqlite:///labourlink_dev.db
```

## 4. Install and run

From the project root (`LabourLink`):

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Or from the root after the venv exists:

```powershell
npm install
npm run dev
```

- Frontend: http://localhost:5173
- Backend health: http://127.0.0.1:5000/api/health

## 5. Seed / demo accounts

Created automatically if missing:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@labourlink.local` | `Admin@123` |
| Worker | `worker@labourlink.local` | `Worker@123` |
| Employer | `employer@labourlink.local` | `Employer@123` |

Demo jobs in Nagpur are seeded for the employer account.

## 6. How to test the product flows

1. **OTP** — Register a new user with a 10-digit phone. Open `/dev/otp-inbox`, copy the OTP, verify, then log in. Wrong OTP, resend cooldown, and expiry are enforced.
2. **Login** — Use a verified account. Unverified users are blocked.
3. **Jobs** — Employer posts a job (optional image + browser location). Worker browses `/jobs`, searches, opens details.
4. **Applications** — Worker applies. Employer accepts/rejects on `/applications`. Accepting assigns the job and opens chat.
5. **Negotiation** — From a job or application, send ₹ offer, counter, accept/reject. History is stored.
6. **Chat** — `/messages` loads history and sends through the API; Socket.IO pushes new messages.
7. **Location** — After assignment, worker opens `/jobs/:id/track`, allows GPS, starts sharing. Employer sees updates on the same page without refresh.
8. **Extra work** — Worker submits extra amount + reason on job details. Employer approves on the employer dashboard; payable amount increases.
9. **Payment** — Employer `/payments` initiates the payable amount, confirms with password (sandbox) or Razorpay. Worker wallet and history update. Cancel/fail are real status changes.
10. **Notifications** — Each of the events above writes a notification row and emits `notification:new`.
11. **Admin** — Login as admin → users, jobs, applications, transactions, reports, statistics.

## 7. API smoke tests

```powershell
curl http://127.0.0.1:5000/api/health
curl -X POST http://127.0.0.1:5000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@labourlink.local\",\"password\":\"Admin@123\"}"
```

## Production frontend env

`frontend/.env.production`

```
VITE_API_URL=https://YOUR-API-HOST/api
VITE_SOCKET_URL=https://YOUR-API-HOST
```

See `docs/DEPLOYMENT.md` after the local app is working.
