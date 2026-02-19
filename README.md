# Global Genesis Super App

The **Global Genesis Super App** is a next-generation financial operating system built with a high-performance gRPC backend, a scalable FastAPI gateway, and a modern React frontend.

## 🏗️ Architecture

The system follows a **Microservices-ready** architecture:

1.  **Frontend**: React (Vite) + Tailwind CSS (Port `5173`)
    -   Interactive Dashboard for Wallets and Transactions.
    -   Authentication (Login/Signup) via JWT.
    -   Connects to the API Gateway.
2.  **API Gateway**: FastAPI (Port `8000`)
    -   Acts as a **BFF (Backend for Frontend)**.
    -   Translates REST/JSON requests to gRPC Protobuf messages.
    -   Enforces **JWT Authentication** on protected routes.
3.  **Core Backend**: Python gRPC Services (Port `50051`)
    -   **User Service**: Identity management, password hashing (Bcrypt).
    -   **Wallet Service**: Ledger, currency conversion, atomic transactions.
    -   **Database**: SQLite (Local) / CockroachDB (Production).

---

## 🚀 Getting Started (Local Development)

### Prerequisites
-   Python 3.10+
-   Node.js 18+
-   Docker (Optional)

### 1. Manual Setup (Without Docker)

#### Backend
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.main
```

#### Gateway
```bash
# New Terminal
.\venv\Scripts\activate
python gateway/main.py
```

#### Frontend
```bash
# New Terminal
cd web
npm install
npm run dev
```

### 2. Docker Setup (Recommended)

Run the entire stack with a single command:
```bash
docker-compose up --build
```
-   **Frontend**: [http://localhost:5173](http://localhost:5173)
-   **API**: [http://localhost:8000](http://localhost:8000)

---

## 🧪 Features & Usage

1.  **Authentication**:
    -   **Sign Up**: Create an account with password (hashed securely).
    -   **Login**: Obtain a JWT token to access wallet features.
2.  **Banking**:
    -   **Wallet**: View balance in multiple currencies (USD, INR, EUR).
    -   **Transfer**: Send money globally with real-time currency conversion.
    -   **History**: Track all transactions instantly.

## 🛠️ Tech Stack
-   **Language**: Python 3.11, JavaScript (React)
-   **Communication**: gRPC (Protobuf), HTTP/REST
-   **Security**: JWT, Bcrypt, HTTPBearer
-   **Database**: SQLAlchemy (ORM), Alembic (Migrations), SQLite
-   **Containerization**: Docker, Nginx