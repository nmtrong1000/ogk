import asyncio
import http.client
import logging
import socket
import socketserver
import ssl
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import tldextract
from dnslib import QTYPE, RCODE, RR, DNSRecord
from dnslib.server import BaseResolver, DNSServer

from service.core.agent import ModuleContext
from service.platform import firewall, netconfig

log = logging.getLogger("ogk.webfilter")
PSL = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=(), fallback_to_snapshot=True)
SAFESEARCH = {
    "google.com": "forcesafesearch.google.com",
    "www.google.com": "forcesafesearch.google.com",
    "bing.com": "strict.bing.com",
    "www.bing.com": "strict.bing.com",
    "youtube.com": "restrict.youtube.com",
    "www.youtube.com": "restrict.youtube.com",
    "duckduckgo.com": "safe.duckduckgo.com",
    "www.duckduckgo.com": "safe.duckduckgo.com",
}
DOH_HOSTS = {"dns.google", "cloudflare-dns.com", "mozilla.cloudflare-dns.com", "dns.quad9.net", "doh.opendns.com"}
DOH_RESOLVERS = (
    ("cloudflare-dns.com", "1.1.1.1"),
    ("dns.google", "8.8.8.8"),
)
PERMANENT_ALLOWLIST = {"localhost", "127.0.0.1", "::1"}
DEFAULT_CATEGORY_DOMAINS = {
    "social": (
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "snapchat.com",
        "pinterest.com",
        "reddit.com",
        "x.com",
        "twitter.com",
        "threads.net",
        "discord.com",
    ),
    "adult": (
        "adultfriendfinder.com",
        "onlyfans.com",
        "pornhub.com",
        "xvideos.com",
        "xnxx.com",
        "xhamster.com",
        "redtube.com",
        "youporn.com",
        "tube8.com",
        "spankbang.com",
        "chaturbate.com",
        "stripchat.com",
        "livejasmin.com",
        "cam4.com",
        "bongacams.com",
        "brazzers.com",
        "realitykings.com",
        "naughtyamerica.com",
        "bangbros.com",
        "penthouse.com",
        "playboy.com",
        "literotica.com",
        "lushstories.com",
        "manyvids.com",
        "fansly.com",
        "faphouse.com",
        "erome.com",
        "motherless.com",
        "xfreehd.com",
        "youjizz.com",
        "hclips.com",
        "thumbzilla.com",
        "tnaflix.com",
        "yespornplease.com",
    ),
}
QUERY_INTERVAL = 300


class UDPServerIPv6(socketserver.ThreadingUDPServer):
    address_family = socket.AF_INET6
    daemon_threads = True
    allow_reuse_address = True


class TCPServerIPv6(socketserver.ThreadingTCPServer):
    address_family = socket.AF_INET6
    daemon_threads = True
    allow_reuse_address = True


class FixedIPHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float) -> None:
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self.address, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def domain_matches(host: str, rule: str) -> bool:
    return host == rule or host.endswith("." + rule)


def registered_domain(host: str) -> str:
    result = PSL(host)
    return result.top_domain_under_public_suffix or host


def blocked_reason(host: str, rules: dict[str, Any]) -> str | None:
    if any(domain_matches(host, item) for item in PERMANENT_ALLOWLIST):
        return None
    if any(domain_matches(host, item) for item in rules.get("web_allowlist", [])):
        return None
    if any(domain_matches(host, item) for item in rules.get("web_blocklist", [])):
        return "domain"
    categories = rules.get("category_domains", {})
    for category in rules.get("blocked_categories", []):
        if any(domain_matches(host, item) for item in categories.get(category, [])):
            return category
    if any(domain_matches(host, item) for item in DOH_HOSTS) or host == "use-application-dns.net":
        return "doh"
    return None


class PolicyResolver(BaseResolver):
    def __init__(
        self,
        context: ModuleContext,
        upstreams: list[str],
        loop: asyncio.AbstractEventLoop,
        on_upstream_failure: Callable[[], None] | None = None,
    ) -> None:
        self.context = context
        self.upstreams = upstreams or ["1.1.1.1"]
        self.loop = loop
        self.on_upstream_failure = on_upstream_failure
        self.upstream_failed = False
        self.last_events: dict[tuple[int, str, str], float] = {}
        self.last_notices: dict[str, float] = {}
        self.state_lock = threading.Lock()
        self.policy_lock = threading.Lock()
        self.policy_cached_at = 0.0
        self.policy_cache: tuple[int | None, int, dict[str, Any], str] = (None, 0, {}, "")

    def _policy(self) -> tuple[int | None, int, dict[str, Any], str]:
        now = time.monotonic()
        with self.policy_lock:
            if now - self.policy_cached_at < 1.0:
                return self.policy_cache
            session = self.context.platform.current_session()
            if session is None or not session.sid:
                result = (None, 0, {}, "")
            else:
                child_id = self.context.policy_store.child_for_sid(session.sid)
                if child_id is None:
                    result = (None, 0, {}, "")
                else:
                    policy = self.context.policy_store.rules_for(child_id)
                    if policy is None:
                        result = (child_id, 0, {}, "")
                    else:
                        rules = dict(policy.rules)
                        if policy.source == "default" and not rules.get("category_domains"):
                            rules["category_domains"] = DEFAULT_CATEGORY_DOMAINS
                        result = (child_id, policy.version, rules, policy.set_by)
            self.policy_cache = result
            self.policy_cached_at = now
            return result

    def _event(self, child_id: int | None, version: int, host: str, event_type: str) -> None:
        if child_id is None or self.context.event_queue is None or self.context.session is None:
            return
        device_id = self.context.session.device_id
        if device_id is None:
            return
        key = (child_id, registered_domain(host), event_type)
        now = time.monotonic()
        with self.state_lock:
            if key in self.last_events and now - self.last_events[key] < QUERY_INTERVAL:
                return
            self.last_events[key] = now
            if len(self.last_events) > 10000:
                self.last_events = {item: at for item, at in self.last_events.items() if now - at < QUERY_INTERVAL}
        payload = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "device_id": device_id,
            "child_id": child_id,
            "type": event_type,
            "subject": key[1],
            "duration_sec": 0,
            "policy_id": version,
        }
        self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.context.event_queue.enqueue([payload])))

    def resolve(self, request: DNSRecord, handler) -> DNSRecord:
        qname = str(request.q.qname).rstrip(".").lower()
        qtype = QTYPE[request.q.qtype]
        child_id, version, rules, set_by = self._policy()
        if child_id is not None and (
            qname == "use-application-dns.net" or any(domain_matches(qname, host) for host in DOH_HOSTS)
        ):
            self._event(child_id, version, qname, "blocked_domain")
            self._notify(qname, "DoH bị tắt để không vượt qua bộ lọc.", set_by)
            reply = request.reply(ra=1, aa=1)
            reply.header.rcode = RCODE.NXDOMAIN
            return reply
        reason = blocked_reason(qname, rules) if child_id is not None else None
        if reason is not None:
            self._event(child_id, version, qname, "blocked_domain")
            self._notify(qname, self._reason(reason), set_by)
            reply = request.reply(ra=1, aa=1)
            reply.header.rcode = RCODE.NXDOMAIN
            return reply
        self._event(child_id, version, qname, "domain_query")
        target = SAFESEARCH.get(qname) if child_id is not None else None
        query_name = target or qname
        forwarded = DNSRecord.question(query_name, qtype)
        reply = None
        last_error = None
        for host, address in DOH_RESOLVERS:
            connection = None
            try:
                connection = FixedIPHTTPSConnection(host, address, timeout=2)
                connection.request(
                    "POST",
                    "/dns-query",
                    forwarded.pack(),
                    headers={"accept": "application/dns-message", "content-type": "application/dns-message"},
                )
                response = connection.getresponse()
                if response.status != 200:
                    raise OSError(f"DoH upstream {host} returned HTTP {response.status}")
                reply = DNSRecord.parse(response.read())
                break
            except Exception as exc:
                last_error = exc
            finally:
                if connection is not None:
                    connection.close()
        if reply is None:
            log.error(
                "all DNS-over-HTTPS upstreams failed for %s; disabling web filtering to restore network access",
                qname,
                exc_info=None
                if last_error is None
                else (type(last_error), last_error, last_error.__traceback__),
            )
            should_fail_open = False
            with self.state_lock:
                if not self.upstream_failed:
                    self.upstream_failed = True
                    should_fail_open = True
            if should_fail_open and self.on_upstream_failure is not None:
                self.on_upstream_failure()
            for upstream in self.upstreams:
                try:
                    fallback = DNSRecord.parse(
                        forwarded.send(upstream, port=53, timeout=1, ipv6=":" in upstream)
                    )
                    fallback.header.id = request.header.id
                    if target:
                        out = request.reply(ra=1)
                        for answer in fallback.rr:
                            out.add_answer(RR(request.q.qname, answer.rtype, rdata=answer.rdata, ttl=answer.ttl))
                        return out
                    return fallback
                except Exception:
                    log.warning("saved DNS fallback %s also failed", upstream)
            reply = request.reply(ra=1)
            reply.header.rcode = RCODE.SERVFAIL
            return reply
        if target:
            out = request.reply(ra=1)
            for answer in reply.rr:
                out.add_answer(RR(request.q.qname, answer.rtype, rdata=answer.rdata, ttl=answer.ttl))
            return out
        reply.header.id = request.header.id
        return reply

    def _notify(self, host: str, reason: str, set_by: str) -> None:
        key = registered_domain(host)
        now = time.monotonic()
        with self.state_lock:
            if key in self.last_notices and now - self.last_notices[key] < QUERY_INTERVAL:
                return
            self.last_notices[key] = now
            if len(self.last_notices) > 10000:
                self.last_notices = {item: at for item, at in self.last_notices.items() if now - at < QUERY_INTERVAL}
        if self.context.web_state is not None:
            self.context.web_state.blocked(host, reason, set_by)

    @staticmethod
    def _reason(code: str) -> str:
        names = {
            "domain": "danh sách tên miền bị chặn",
            "education": "nhóm Giáo dục",
            "entertainment": "nhóm Giải trí",
            "social": "nhóm Mạng xã hội",
            "games": "nhóm Trò chơi",
            "adult": "nhóm Không phù hợp lứa tuổi",
            "unclassified": "nhóm Chưa phân loại",
            "doh": "bảo vệ DNS",
        }
        return f"Tên miền thuộc {names.get(code, 'luật gia đình')}"


class WebFilterModule:
    def __init__(self, context: ModuleContext) -> None:
        self.context = context
        self.servers: list[DNSServer] = []

    def _upstreams(self) -> list[str]:
        path = self.context.data_dir / "dns_config.json"
        try:
            import json

            entries = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(entries, dict):
                entries = [entries]
            return [
                ip
                for entry in entries
                for ip in entry.get("servers", entry.get("ServerAddresses", []))
                if ip.split("%", 1)[0] not in {"127.0.0.1", "::1"}
            ]
        except (OSError, ValueError, TypeError):
            return []

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        upstream_failure = asyncio.Event()

        def fail_open() -> None:
            # DNS resolver callbacks run in dnslib worker threads. Restore network
            # settings there immediately so a failed upstream cannot strand every
            # Windows account on the local proxy.
            for restore in (
                lambda: firewall.restore(self.context.data_dir),
                lambda: netconfig.restore_dns(self.context.data_dir),
                lambda: netconfig.restore_doh(self.context.data_dir),
            ):
                try:
                    restore()
                except Exception:
                    log.exception("failed to restore network configuration after DNS upstream failure")
            loop.call_soon_threadsafe(upstream_failure.set)

        try:
            await asyncio.to_thread(netconfig.configure_dns, self.context.data_dir)
            await asyncio.to_thread(firewall.configure, self.context.data_dir)
            await asyncio.to_thread(netconfig.disable_doh, self.context.data_dir)
            resolver = PolicyResolver(self.context, self._upstreams(), loop, fail_open)
            for address in ("127.0.0.1", "::1"):
                for tcp in (False, True):
                    server_type = (TCPServerIPv6 if tcp else UDPServerIPv6) if address == "::1" else None
                    server = DNSServer(resolver, address=address, port=53, tcp=tcp, server=server_type)
                    server.start_thread()
                    self.servers.append(server)
            log.info("DNS proxy listening on 127.0.0.1 and ::1 port 53")
            await upstream_failure.wait()
            log.error("web filtering stopped because every DNS upstream failed; network DNS was restored")
        finally:
            for server in self.servers:
                server.stop()
            await asyncio.to_thread(firewall.restore, self.context.data_dir)
            await asyncio.to_thread(netconfig.restore_dns, self.context.data_dir)
            await asyncio.to_thread(netconfig.restore_doh, self.context.data_dir)


def create(context: ModuleContext) -> WebFilterModule:
    return WebFilterModule(context)
