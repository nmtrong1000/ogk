"""https_server runs a real TLS server on 127.0.0.1 with a cert from a throwaway CA.
rotate() swaps in a new server certificate from the same CA, like re-running gen_certs.sh.
"""

import datetime
import ipaddress
import json
import ssl
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


def _cert(subject, issuer_name, public_key, signing_key, *, ca):
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_name)]))
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if ca:
        builder = builder.add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True
        )
    else:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
    return builder.sign(signing_key, hashes.SHA256())


def make_ca(tmp_path, name):
    key = ec.generate_private_key(ec.SECP256R1())
    cert = _cert(name, name, key.public_key(), key, ca=True)
    path = tmp_path / f"{name}.crt"
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key, path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok"}).encode()
        self.send_response(200 if self.path == "/api/health" else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@dataclass
class TlsServer:
    url: str
    ca_path: Path
    cert_der: bytes
    context: ssl.SSLContext


def _server_cert(tmp_path: Path, ca_key, name: str) -> tuple[Path, Path, bytes]:
    server_key = ec.generate_private_key(ec.SECP256R1())
    server_cert = _cert("server", "test-ca", server_key.public_key(), ca_key, ca=False)
    cert_path = tmp_path / f"{name}.crt"
    key_path = tmp_path / f"{name}.key"
    cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path, server_cert.public_bytes(serialization.Encoding.DER)


@pytest.fixture
def https_server(tmp_path):
    ca_key, ca_path = make_ca(tmp_path, "test-ca")
    cert_path, key_path, der = _server_cert(tmp_path, ca_key, "server")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    server = TlsServer(f"https://127.0.0.1:{httpd.server_address[1]}", ca_path, der, context)

    def rotate() -> None:
        new_cert, new_key, new_der = _server_cert(tmp_path, ca_key, "server2")
        server.context.load_cert_chain(new_cert, new_key)
        server.cert_der = new_der

    server.rotate = rotate
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield server
    httpd.shutdown()
    httpd.server_close()
