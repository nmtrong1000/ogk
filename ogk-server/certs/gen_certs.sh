#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)/out"
LAN_IP="${1:-$(ipconfig getifaddr en0 2>/dev/null || true)}"
mkdir -p "$DIR"
cd "$DIR"

if [[ ! -f ca.key || ! -f ca.crt ]]; then
  openssl ecparam -name prime256v1 -genkey -noout -out ca.key
  openssl req -x509 -new -key ca.key -sha256 -days 3650 -out ca.crt \
    -subj "/CN=OGK Lab CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  chmod 600 ca.key
  echo "Tạo CA mới: $DIR/ca.crt"
else
  echo "Dùng lại CA có sẵn: $DIR/ca.crt"
fi

SAN="DNS:localhost,IP:127.0.0.1"
if [[ -n "$LAN_IP" ]]; then
  SAN="$SAN,IP:$LAN_IP"
fi

openssl ecparam -name prime256v1 -genkey -noout -out server.key
openssl req -new -key server.key -out server.csr -subj "/CN=OGK-Server"
cat > server.ext <<EOF
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=$SAN
EOF
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile server.ext
rm -f server.csr server.ext
chmod 600 server.key

echo "Chứng chỉ server: $DIR/server.crt ($SAN)"
openssl verify -CAfile ca.crt server.crt
