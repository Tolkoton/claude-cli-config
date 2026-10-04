# Feature slot-picker — decomposition (draft for the critic)

## Goal
The client sees the free hours of a chosen day and books one.

## Acceptance criteria (owner-ratified)
- A client picks a free hour on a phone and the booking appears on the mechanic's day view at once (D1).
- More than half of a week's bookings come through the page (G1).

## Slices (the DAG)
- **S1 free-slots query** — delivers: the free hours of a date from the bookings table · contract out: `list[Slot]` · depends on: — · **TRACER BULLET (build first)**
- **S2 free-slots cache** — delivers: an in-process cache of S1's answer per date, refreshed every 10 minutes, so the page renders without a database read · contract out: `list[Slot]` (same shape as S1) · depends on: S1
- **S3 booking form** — delivers: the page that shows S2's hours and posts a booking · contract out: `Booking` · depends on: S2
- **S4 booking write** — delivers: the insert of a booking; rejects a slot that is already taken with "sorry, just taken" · depends on: S3

## Inter-slice contracts
- S1 → S2: `list[Slot]`, each `{date, hour, free: bool}`
- S2 → S3: the same `list[Slot]`, at most 10 minutes old
- S3 → S4: `Booking {name, phone, date, hour}`

## Integration exit criterion
S1 → S3 → S4 runs end to end on a phone-sized viewport: pick an hour, post, see it in the day view.

## Звірка з цілями
- служить: G1, D1
- вибір між варіантами розв'язав: принципи не розрізняють ці варіанти, вибір технічний (the cache is a performance detail)
- не-цілі й обмеження: N1 — no payment step; C2 — the cache is in-process, no managed service
