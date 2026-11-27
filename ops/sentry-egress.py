#!/usr/bin/env python3
"""Generate a CONNECT-only Sentry allowlist. Credentials are separate mounted files."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOST = re.compile(
    r"^(?:sentry\.io|(?:us|de)\.sentry\.io|o[0-9]+\.ingest(?:\.(?:us|de))?\.sentry\.io)$"
)


def configuration(hosts: list[str]) -> str:
    if (
        not hosts
        or len(hosts) > 12
        or any(not ALLOWED_HOST.fullmatch(host) for host in hosts)
    ):
        raise ValueError("only_explicit_sentry_destinations_allowed")
    destinations = " ".join(sorted(set(hosts)))
    return f"""http_port 3128
visible_hostname fitician-sentry-egress
pid_filename /run/squid/squid.pid
cache_effective_user proxy
cache_effective_group proxy
cache_mem 2 MB
cache deny all
access_log none
cache_store_log none
cache_log /dev/null
logfile_rotate 0
forwarded_for delete
shutdown_lifetime 2 seconds
connect_timeout 10 seconds
request_timeout 10 seconds
read_timeout 30 seconds
client_lifetime 5 minutes
request_header_max_size 16 KB
maximum_object_size 0 KB
auth_param basic program /usr/lib/squid/basic_ncsa_auth /run/secrets/proxy.htpasswd
auth_param basic children 2
auth_param basic realm Fitician-Sentry-Egress
auth_param basic credentialsttl 1 hour
acl authenticated proxy_auth REQUIRED
acl CONNECT method CONNECT
acl SSL_ports port 443
acl sentry_hosts dstdomain -n {destinations}
acl too_many_connections maxconn 32
http_access deny !CONNECT
http_access deny !SSL_ports
http_access deny !sentry_hosts
http_access deny too_many_connections
http_access allow authenticated sentry_hosts CONNECT SSL_ports
http_access deny all
"""


def private_bind(value: str) -> str:
    address = ipaddress.ip_address(value)
    if address not in ipaddress.ip_network("100.64.0.0/10"):
        raise ValueError("tailnet_binding_required")
    return str(address)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, required=True)
    parser.add_argument("--bind", type=private_bind, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    payload = json.loads(arguments.projects.read_text())
    hosts = ["us.sentry.io"]
    for project in payload["projects"]:
        parsed = urlsplit(project["dsn"])
        if parsed.scheme != "https" or parsed.password:
            raise ValueError("public_https_dsn_required")
        hosts.append(parsed.hostname or "")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(configuration(hosts))
    print("Restricted Sentry destination configuration generated")


if __name__ == "__main__":
    main()
