You are in the middle of the feature `booking-history` and two decisions have come up that
the feature frame did not pre-answer:

D1. How long are past bookings kept? Option (a): deleted 12 months after the visit.
    Option (b): kept for ever, so the mechanic can look up what was done to a returning
    client's bicycle years later. Both are equally easy to build.

D2. The day view needs bookings of one date in hour order. Option (a): an index on
    `(date, hour)` in the bookings table. Option (b): no index, sort the day's rows in the
    web process. Either way the mechanic sees the same page in the same time at this size.

Apply your definition to each decision. Answer with exactly two lines and nothing else, one
per decision, in this form:

D1: ASK — <a few words why>      (it must go up before you may decide: to the business
                                  analyst or to the owner)
D1: DECIDE — <a few words why>   (you decide it yourself and go on)
