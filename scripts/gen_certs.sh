#!/usr/bin/env bash
# =============================================================================
# gen_certs.sh — Generate self-signed CA + backend server + gateway client
# certs for mTLS between the gRPC backend and FastAPI gateway.
#
# Usage: bash scripts/gen_certs.sh
# Output: certs/ directory (gitignored)
# =============================================================================
set -euo pipefail

CERTS_DIR="$(dirname "$0")/../certs"
mkdir -p "$CERTS_DIR"

DAYS=3650   # 10 years — rotate in production via cert-manager
C="US"
O="SuperApp"

echo "🔐 Generating self-signed CA..."
openssl genrsa -out "$CERTS_DIR/ca.key" 4096
openssl req -new -x509 -key "$CERTS_DIR/ca.key" \
    -out "$CERTS_DIR/ca.crt" \
    -days "$DAYS" \
    -subj "/C=$C/O=$O/CN=SuperApp-CA"

echo "🔐 Generating gRPC backend server cert (CN=backend)..."
openssl genrsa -out "$CERTS_DIR/server.key" 2048
openssl req -new -key "$CERTS_DIR/server.key" \
    -out "$CERTS_DIR/server.csr" \
    -subj "/C=$C/O=$O/CN=backend"
# SAN for docker-compose service name
cat > "$CERTS_DIR/server_ext.cnf" <<EOF
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = backend
DNS.2 = backend-eu
DNS.3 = localhost
IP.1  = 127.0.0.1
EOF
openssl x509 -req \
    -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
    -out "$CERTS_DIR/server.crt" \
    -days "$DAYS" \
    -extfile "$CERTS_DIR/server_ext.cnf" \
    -extensions v3_req

echo "🔐 Generating gateway client cert (CN=gateway)..."
openssl genrsa -out "$CERTS_DIR/client.key" 2048
openssl req -new -key "$CERTS_DIR/client.key" \
    -out "$CERTS_DIR/client.csr" \
    -subj "/C=$C/O=$O/CN=gateway"
openssl x509 -req \
    -in "$CERTS_DIR/client.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" \
    -out "$CERTS_DIR/client.crt" \
    -days "$DAYS"

# Cleanup CSR + ext files (keep only crt/key/ca)
rm -f "$CERTS_DIR/server.csr" "$CERTS_DIR/client.csr" "$CERTS_DIR/server_ext.cnf"

echo ""
echo "✅ Certificates written to: $CERTS_DIR"
echo "   ca.crt        — Root CA (shared with all services)"
echo "   server.crt/key — gRPC backend server cert"
echo "   client.crt/key — Gateway client cert"
echo ""
echo "🚀 To use mTLS, set:"
echo "   backend:  GRPC_TLS=true  CERTS_DIR=/app/certs"
echo "   gateway:  GRPC_SECURE=true  CERTS_DIR=/app/certs"
