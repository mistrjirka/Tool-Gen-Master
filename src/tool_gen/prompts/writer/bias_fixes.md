Style guidance (soft preferences, not acceptance rules).

HARD requirements — a request failing these should be rejected:
- Fidelity and scope: express every supplied information need, no more and no
  fewer. Preserve any genuine supplied operation sequence or dependency.
  Never invent extra actions, values, lookup chains, deadlines, or temporal
  dependencies to connect independent operations.
- Literals: preserve exact literal content, opaque identifiers, numbers,
  dates, bounds, units, and decimal precision.
- No implementation identifiers: never write "API_call_N" tokens. When a
  later step genuinely depends on an earlier result, say so in plain
  language ("then get details for that item"); when operations are
  independent, do not invent a dependency between them.

SOFT preferences — measured by reporting, never enforced by rejection:
- Register diversity is welcome: a mix of imperative, terse fragments,
  formal requests, questions, and third-person phrasings reads human.
  No opener quota is enforced.
- Terse requests (even a few words) and longer ones are both fine; match the
  requested style. No length quota is enforced.
- Lists and bullets are allowed whenever a person would naturally use them.
  Argument-key order is an input convenience, not a required phrasing order.
  Independent needs may be worded flexibly; this does not permit changing an
  explicitly supplied operation sequence or dependency.
- Literal identifiers need not always be introduced with "ID" (a bare code
  a human would paste is fine), but never rename an opaque ID into an
  invented title, and never change name-to-ID semantics: a supplied display
  name stays a name, a supplied identifier stays an identifier.
