# Global Genesis Super App

The **Global Genesis Super App** is a next-generation financial operating system built with a high-performance gRPC backend, a scalable FastAPI gateway, and a modern React frontend.

## 🏗️ Architecture

The system follows a **Microservices-ready** architecture:

1.  **Frontend**: React (Vite) + Tailwind CSS (Port `5173/5174`)
    -   Interactive Dashboard for Wallets and Transactions.
    -   Connects to the API Gateway.
2.  **API Gateway**: FastAPI (Port `8000`)
    -   Acts as a **BFF (Backend for Frontend)**.
    -   Translates REST/JSON requests to gRPC Protobuf messages.
3.  **Core Backend**: Python gRPC Services (Port `50051`)
    -   **User Service**: Identity management.
    -   **Wallet Service**: Ledger, currency conversion, atomic transactions.
    -   **Policy Service**: Compliance and geo-fencing (Placeholder).
4.  **Database**: SQLite (Local) / CockroachDB (Production)
    -   Persists Users, Wallets, and Transaction Logs.

---

## 🚀 Getting Started (Local Development)

### Prerequisites
-   Python 3.10+
-   Node.js 18+
-   `virtualenv`

### 1. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Database Migrations
alembic upgrade head

# Start gRPC Server
python -m app.main
```

### 2. API Gateway Setup

Open a new terminal:
```bash
.\venv\Scripts\activate
python gateway/main.py
```
*   Gateway API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Setup

Open a new terminal:
```bash
cd web
npm install
npm run dev
```
*   Frontend UI: [http://localhost:5173](http://localhost:5173) (or 5174 if 5173 is busy)

---

## 🧪 Features & Usage

1.  **Sign Up**: Create a new user (Select Region: India, USA, or Europe).
2.  **Wallet Creation**: A wallet is automatically created for the user.
3.  **Fund Transfer**:
    -   Enter a Recipient Wallet ID and Amount.
    -   Supports **Cross-Currency Transfers** (e.g., USD -> INR) with auto-conversion.
4.  **Transaction History**: View real-time history of credits and debits.

---

## 🛠️ Tech Stack
-   **Language**: Python 3.11, JavaScript (React)
-   **Communication**: gRPC (Protobuf), HTTP/REST
-   **Frameworks**: `grpcio`, `FastAPI`, `React`, `Vite`, `TailwindCSS`
-   **Database**: SQLAlchemy (ORM), Alembic (Migrations), SQLite
-   **Testing**: `pytest`