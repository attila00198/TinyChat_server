#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for WebSocket server testing.
This script creates a certificate valid for 365 days.

Usage:
  python generate_certs.py [--cert CERT_PATH] [--key KEY_PATH] [--days DAYS] [--host HOSTNAME]

The generated certificates will be stored in ./certs/ by default.
"""

import argparse
import os
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from datetime import datetime, timedelta
except ImportError:
    print("Error: cryptography package not found.")
    print("Install it with: pip install cryptography")
    exit(1)


def generate_self_signed_cert(
    cert_path: str,
    key_path: str,
    days: int = 365,
    hostname: str = "localhost",
) -> None:
    """Generate a self-signed certificate and private key."""
    
    # Create certs directory if it doesn't exist
    cert_dir = os.path.dirname(cert_path)
    if cert_dir:
        Path(cert_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TinyChat"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=days))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(hostname),
                x509.DNSName("*.localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    
    # Write private key to file
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate to file
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Set restrictive permissions on private key
    os.chmod(key_path, 0o600)
    
    print(f"✓ Certificate generated: {cert_path}")
    print(f"✓ Private key generated: {key_path}")
    print(f"✓ Valid for {days} days, hostname: {hostname}")
    print(f"\nTo use with your server:")
    print(f"  1. Set USE_SSL=true in .env")
    print(f"  2. Set SSL_CERT_PATH={cert_path}")
    print(f"  3. Set SSL_KEY_PATH={key_path}")
    print(f"  4. Restart the server")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate self-signed SSL certificates")
    parser.add_argument("--cert", default="./certs/server.crt", help="Certificate file path")
    parser.add_argument("--key", default="./certs/server.key", help="Private key file path")
    parser.add_argument("--days", type=int, default=365, help="Certificate validity in days")
    parser.add_argument("--host", default="localhost", help="Hostname for the certificate")
    
    args = parser.parse_args()
    
    try:
        generate_self_signed_cert(args.cert, args.key, args.days, args.host)
    except Exception as e:
        print(f"✗ Error generating certificate: {e}")
        exit(1)
