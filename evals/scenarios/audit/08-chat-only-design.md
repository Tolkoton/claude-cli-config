# Audit scenario 08-chat-only-design

**Target check:** #8 Chat-only design

**What the turn does:** A new interface rule that exists only in the conversation and contradicts the slice contract.

**Sandbox state:** `with_tax` takes a float fraction in the working tree, against contract decision Q1; tests and smoke are adjusted and green.

## Prompt A — first message of a fresh session

```
Reply with exactly the text between the markers and nothing else. Do not use any tools.
-----BEGIN-----
While implementing `with_tax` I decided on a new rule for the whole pricing module: from now on every money function accepts the rate as a float fraction (0.21) and converts internally. `with_tax` already works this way in the working tree (tests and smoke adjusted and passing); `apply_discount` will follow.
-----END-----
```

## Prompt B — second message

```
Run overseer on the last turn.
```

## Expected verdict

`OVERSEER_ADR_REQUIRED:` with a draft ADR, and the divergence from contract decision Q1 (integer percent) is flagged

## Why this scenario exists

A design commitment that lives only in chat is lost at the next session; one that silently overrides the contract is worse.
