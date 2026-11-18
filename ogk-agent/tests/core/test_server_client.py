import datetime
import ipaddress
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from service.core.server_client import ServerClient


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


def _make_ca(tmp_path, name):
    key = ec.generate_private_key(ec.SECP256R1())
    cert = _cert(name, name, key.public_key(), key, ca=True)
    path = tmp_path / f"{name}.crt"
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key, path


@pytest.fixture
def https_server(tmp_path):
    ca_key, ca_path = _make_ca(tmp_path, "test-ca")
    server_key = ec.generate_private_key(ec.SECP256R1())
    server_cert = _cert("server", "test-ca", server_key.public_key(), ca_key, ca=False)
    cert_path = tmp_path / "server.crt"
    key_path = tmp_path / "server.key"
    cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

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

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"https://127.0.0.1:{httpd.server_address[1]}", ca_path
    httpd.shutdown()
    httpd.server_close()


@pytest.mark.anyio
async def test_health_over_https_with_ca(https_server):
    url, ca_path = https_server
    client = ServerClient(url, ca_path)
    try:
        assert await client.health() == {"status": "ok"}
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_health_rejects_unknown_ca(https_server, tmp_path):
    url, _ = https_server
    _, other_ca = _make_ca(tmp_path, "other-ca")
    client = ServerClient(url, other_ca)
    try:
        with pytest.raises(httpx.ConnectError):
            await client.health()
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_health_raises_on_server_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"status": "error"}))
    client = ServerClient("https://server", transport=transport)
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.health()
    finally:
        await client.aclose()
