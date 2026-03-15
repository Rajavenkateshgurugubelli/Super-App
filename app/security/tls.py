"""
app/security/tls.py

mTLS credential helpers for gRPC server (backend) and channel (gateway).
Reads from CERTS_DIR env var (defaults to ./certs/).

Usage:
  # gRPC backend server
  from app.security.tls import get_server_credentials
  server.add_secure_port('[::]:50051', get_server_credentials())

  # Gateway channel
  from app.security.tls import get_channel_credentials
  channel = grpc.secure_channel(host, get_channel_credentials())
"""
import os
import grpc

CERTS_DIR = os.environ.get("CERTS_DIR", "./certs")


def _read(filename: str) -> bytes:
    path = os.path.join(CERTS_DIR, filename)
    with open(path, "rb") as f:
        return f.read()


def get_server_credentials() -> grpc.ServerCredentials:
    """
    Load server TLS credentials (mutual TLS — requires client cert signed by CA).
    Files required in CERTS_DIR:
      server.key, server.crt, ca.crt
    """
    ca = _read("ca.crt")
    server_key = _read("server.key")
    server_cert = _read("server.crt")

    return grpc.ssl_server_credentials(
        [(server_key, server_cert)],
        root_certificates=ca,
        require_client_auth=True,  # enforce mutual TLS
    )


def get_channel_credentials() -> grpc.ChannelCredentials:
    """
    Load channel credentials for mTLS (gateway → backend).
    Files required in CERTS_DIR:
      client.key, client.crt, ca.crt
    """
    ca = _read("ca.crt")
    client_key = _read("client.key")
    client_cert = _read("client.crt")

    return grpc.ssl_channel_credentials(
        root_certificates=ca,
        private_key=client_key,
        certificate_chain=client_cert,
    )
