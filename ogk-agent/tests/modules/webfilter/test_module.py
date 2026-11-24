import asyncio
import contextlib
from types import SimpleNamespace

from dnslib import QTYPE, RCODE, RR, A, DNSRecord

from service.core.web_state import WebState
from service.modules.webfilter import module
from service.modules.webfilter.module import blocked_reason, domain_matches, registered_domain


def test_domain_match_includes_all_subdomains():
    assert domain_matches("a.b.example.com", "example.com")
    assert not domain_matches("notexample.com", "example.com")


def test_registered_domain_uses_public_suffix_list():
    assert registered_domain("child.school.edu.vn") == "school.edu.vn"


def _context(*, child_id=None, rules=None):
    policy = SimpleNamespace(rules=rules or {}, version=1, source="cached", set_by="parent")
    session = None if child_id is None else SimpleNamespace(sid="child-sid")
    return SimpleNamespace(
        web_state=WebState(),
        platform=SimpleNamespace(current_session=lambda: session),
        policy_store=SimpleNamespace(
            child_for_sid=lambda _sid: child_id,
            rules_for=lambda _child: policy,
        ),
        event_queue=None,
        session=None,
    )


def test_allowlist_takes_precedence_over_blocklist_and_category():
    rules = {
        "web_allowlist": ["school.edu.vn"],
        "web_blocklist": ["edu.vn"],
        "blocked_categories": ["education"],
        "category_domains": {"education": ["edu.vn"]},
    }
    assert blocked_reason("portal.school.edu.vn", rules) is None
    assert blocked_reason("another.edu.vn", rules) == "domain"


def test_dns_over_https_names_are_blocked():
    assert blocked_reason("dns.google", {}) == "doh"


def test_dns_query_for_doh_endpoint_returns_nxdomain(monkeypatch):
    context = _context(child_id=7)
    resolver = module.PolicyResolver(context, [], asyncio.new_event_loop())
    request = DNSRecord.question("dns.google")
    response = resolver.resolve(request, SimpleNamespace(protocol="udp"))
    assert response.header.rcode == RCODE.NXDOMAIN
    assert context.web_state.snapshot()["domain"] == "dns.google"


def test_google_query_uses_safe_search_target(monkeypatch):
    target = "forcesafesearch.google.com"

    class FakeResponse:
        status = 200

        def read(self):
            response = DNSRecord.question(target).reply()
            response.add_answer(RR(target, QTYPE.A, rdata=A("216.239.38.120")))
            return response.pack()

    class FakeConnection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, method, path, body, headers):
            self.query = DNSRecord.parse(body)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(module, "FixedIPHTTPSConnection", FakeConnection)
    context = _context(child_id=7)
    resolver = module.PolicyResolver(context, [], asyncio.new_event_loop())
    request = DNSRecord.question("www.google.com")
    response = resolver.resolve(request, SimpleNamespace(protocol="udp"))
    assert response.q.qname == request.q.qname
    assert str(response.rr[0].rname) == "www.google.com."
    assert str(response.rr[0].rdata) == "216.239.38.120"


def test_parent_session_is_not_given_child_safe_search_or_domain_blocks(monkeypatch):
    queried = []

    class FakeResponse:
        status = 200

        def read(self):
            response = DNSRecord.question("youtube.com").reply()
            response.add_answer(RR("youtube.com", QTYPE.A, rdata=A("192.0.2.10")))
            return response.pack()

    class FakeConnection:
        def __init__(self, host, *_args, **_kwargs):
            self.host = host

        def request(self, _method, _path, body, headers):
            queried.append(str(DNSRecord.parse(body).q.qname).rstrip("."))

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(module, "FixedIPHTTPSConnection", FakeConnection)
    resolver = module.PolicyResolver(_context(), [], asyncio.new_event_loop())

    response = resolver.resolve(DNSRecord.question("youtube.com"), SimpleNamespace(protocol="udp"))

    assert queried == ["youtube.com"]
    assert response.header.rcode == RCODE.NOERROR
    assert str(response.rr[0].rdata) == "192.0.2.10"


def test_child_session_still_blocks_parent_configured_domain(monkeypatch):
    class UnexpectedConnection:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("blocked domains must not be sent upstream")

    monkeypatch.setattr(module, "FixedIPHTTPSConnection", UnexpectedConnection)
    resolver = module.PolicyResolver(
        _context(child_id=7, rules={"web_blocklist": ["youtube.com"]}),
        [],
        asyncio.new_event_loop(),
    )

    response = resolver.resolve(DNSRecord.question("www.youtube.com"), SimpleNamespace(protocol="udp"))

    assert response.header.rcode == RCODE.NXDOMAIN


def test_resolver_uses_second_doh_upstream_when_first_fails(monkeypatch):
    attempted = []

    class FakeResponse:
        status = 200

        def read(self):
            response = DNSRecord.question("example.com").reply()
            response.add_answer(RR("example.com", QTYPE.A, rdata=A("203.0.113.10")))
            return response.pack()

    class FakeConnection:
        def __init__(self, host, *_args, **_kwargs):
            attempted.append(host)
            if host == module.DOH_RESOLVERS[0][0]:
                raise OSError("upstream unavailable")

        def request(self, *_args, **_kwargs):
            return None

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(module, "FixedIPHTTPSConnection", FakeConnection)
    context = SimpleNamespace(web_state=WebState(), platform=SimpleNamespace(current_session=lambda: None))
    resolver = module.PolicyResolver(context, [], asyncio.new_event_loop())

    response = resolver.resolve(DNSRecord.question("example.com"), SimpleNamespace(protocol="udp"))

    assert attempted == [host for host, _address in module.DOH_RESOLVERS]
    assert str(response.rr[0].rdata) == "203.0.113.10"


def test_all_doh_failures_restore_network_and_fall_back_to_saved_dns(monkeypatch):
    failed_open = []

    class FailedConnection:
        def __init__(self, *_args, **_kwargs):
            raise OSError("DoH unavailable")

    def send(_request, _destination, **_kwargs):
        response = DNSRecord.question("example.com").reply()
        response.add_answer(RR("example.com", QTYPE.A, rdata=A("192.0.2.53")))
        return response.pack()

    monkeypatch.setattr(module, "FixedIPHTTPSConnection", FailedConnection)
    monkeypatch.setattr(DNSRecord, "send", send)
    context = SimpleNamespace(web_state=WebState(), platform=SimpleNamespace(current_session=lambda: None))
    resolver = module.PolicyResolver(
        context,
        ["192.168.1.1"],
        asyncio.new_event_loop(),
        lambda: failed_open.append(True),
    )

    response = resolver.resolve(DNSRecord.question("example.com"), SimpleNamespace(protocol="udp"))

    assert failed_open == [True]
    assert str(response.rr[0].rdata) == "192.0.2.53"


def test_upstream_failure_keeps_agent_module_alive_in_fail_open(monkeypatch, tmp_path):
    restored = []
    monkeypatch.setattr(module.netconfig, "configure_dns", lambda _path: None)
    monkeypatch.setattr(module.firewall, "configure", lambda _path: None)
    monkeypatch.setattr(module.netconfig, "disable_doh", lambda _path: None)
    monkeypatch.setattr(module.firewall, "restore", lambda _path: restored.append("firewall"))
    monkeypatch.setattr(module.netconfig, "restore_dns", lambda _path: restored.append("dns"))
    monkeypatch.setattr(module.netconfig, "restore_doh", lambda _path: restored.append("doh"))

    class FakeServer:
        def __init__(self, resolver, **_kwargs):
            self.resolver = resolver

        def start_thread(self):
            self.resolver.on_upstream_failure()

        def stop(self):
            pass

    monkeypatch.setattr(module, "DNSServer", FakeServer)
    context = SimpleNamespace(data_dir=tmp_path)
    async def scenario():
        task = asyncio.create_task(module.WebFilterModule(context).run())
        for _ in range(100):
            if restored:
                break
            await asyncio.sleep(0.01)

        assert not task.done()
        assert {"firewall", "dns", "doh"}.issubset(restored)

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
