# ADR 0003 — Access to the mechanic's day view

## Context
The day view shows clients' names and phone numbers, so it must not be public.

## Decision
Add a small **staff access module**: a `staff` table (login, password hash, role), three roles
— `owner`, `mechanic`, `viewer` — and a permission check on every day-view route. The owner
role manages staff accounts on a `/staff` page. Sessions are server-side, in a `sessions`
table. This is defined once, as the cross-cutting auth convention, so later features do not
reinvent it.

## Alternatives considered
- HTTP basic auth with one password in the server config — rejected: no way to tell who made
  a change, and no way to give read-only access.
- An external identity provider — rejected: a managed service, against the one-cheap-server
  constraint.

## Consequences
Two more tables, one more page, a permission check per route. Reversible: the module can be
replaced without touching bookings.

## Звірка з цілями
- служить: G2, D1
- вибір між варіантами розв'язав: P2 — one auth convention is simpler to maintain than ad-hoc checks
- не-цілі й обмеження: C1 — the day view is protected, so personal data is not exposed; C2 — no managed service
