# ADR 0001: DNS proxy failures must not stop the OGK agent

- Status: Accepted
- Date: 2026-11-24

## Context

OGK's Windows web filter points machine DNS at its local proxy and blocks outbound
DNS on ports 53 and 853. The proxy forwards allowed queries to fixed-IP DNS-over-HTTPS
servers. On failure it also tries the DNS servers saved before the proxy was enabled.

The saved-DNS attempt is best-effort: the saved resolver can itself be unreachable,
and the firewall's explicit block rules take precedence over its program-specific
allow rule. An allow rule for `ogk-service.exe` therefore must not be treated as a
reliable exception to a matching block rule. The failure callback restores the
firewall, system DNS, and browser DoH settings to fail open.

The outage was amplified by the module lifecycle: after restoring the network,
`WebFilterModule.run()` returned. `Agent.run()` treats any module task ending as a
request to stop the entire service. That closed IPC and stopped request submission,
heartbeats, and tray communication at the same time the child saw the blocked-site
notice. The resolver's current query could also fail while the original DNS
configuration was unavailable, presenting as `DNS_PROBE_FINISHED_NO_INTERNET`.

## Decision

When every DoH upstream fails, restore firewall, DNS, and browser DoH settings
immediately, log an explicit fail-open state, and keep the web-filter task alive.
The rest of OGK must remain online so requests and dashboard communication still
work. Filtering stays disabled until the service is restarted; a future change may
add a tested recovery loop that verifies upstream reachability before re-enabling
the proxy.

Treat direct DNS fallback as best-effort only. Do not rely on a Windows Firewall
allow rule to override a matching block rule. Any future firewall exception design
must be validated on Windows with effective rules and live DNS queries.

## Consequences

- A transient outage may disable web filtering until OGKAgent restarts, but it must
  not take down system DNS or the rest of OGK.
- Logs distinguish fail-open mode from a normal stop.
- Tests must assert that upstream failure restores network settings and does not
  complete the web-filter module task.
- Windows acceptance checks must verify DNS resolution after restoration, IPC and
  heartbeats during degraded mode, and that a blocked-site notice can still submit
  a request to the parent dashboard.

## Prevention checklist

1. Keep optional protection modules isolated from the agent's service lifetime.
2. Restore machine DNS and remove DNS firewall blocks before declaring recovery.
3. Never equate a saved DNS configuration with a working resolver; validate actual
   name resolution on Windows.
4. Keep fail-open diagnostics, and test outage behavior as well as the normal
   blocked-site flow.
