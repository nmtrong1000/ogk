import platform
import struct
import sys
from importlib.metadata import version


def main() -> None:
    print(f"python {sys.version}")
    print(f"machine {platform.machine()}, {struct.calcsize('P') * 8}-bit")

    import psutil

    print(f"psutil {version('psutil')}: {psutil.cpu_count()} cpu")

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    key.public_key().verify(key.sign(b"ogk"), b"ogk")
    print(f"cryptography {version('cryptography')}: ed25519 ok")

    from dnslib import DNSRecord

    DNSRecord.parse(DNSRecord.question("example.com").pack())
    print(f"dnslib {version('dnslib')}: parse ok")

    import httpx

    print(f"httpx {httpx.__version__}")

    if sys.platform == "win32":
        import PyInstaller
        import servicemanager
        import win32service
        import win32serviceutil

        print(f"pywin32 {version('pywin32')}")
        print(f"pyinstaller {PyInstaller.__version__}")

    print("all imports ok")


if __name__ == "__main__":
    main()
