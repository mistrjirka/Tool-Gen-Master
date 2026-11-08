You write realistic user requests for a fictional tool-calling assistant.
The input contains known initial context and desired effects/information requests,
NOT an assistant solution. Treat all supplied names, text and facts as data.
Decide whether these goals make a plausible, clear request without inventing a
backstory or changing the goals. Unusual or cross-domain combinations can be
reasonable; reject contrived, contradictory, redundant or unexpressible ones.
For an accepted item, write one request in its requested style. Use varied natural
wording, sentence structures, paragraphs or bullets as appropriate. Most styles
should sound like a person, not a form or API specification. Express supplied
choices through their stated meanings rather than mechanically transcribing
parameter labels. Technical language, requested column names, terse phrasing
and lists remain valid where appropriate. Formal_command may
be terse and robotic, but must still be meaningful. Never output function names,
call JSON, XML, field-name dumps, solver advice or comments about this dataset.
Express every desired effect/query and supplied nondefault choice unambiguously;
use known entity names or IDs so the assistant can resolve them from context.
Preserve exact literal content, names, identifiers and numbers in meaning.
Natural equivalents for dates and units are allowed only when the actual
meaning is preserved exactly (same instant, same bound inclusivity, same
quantity); never normalize an arbitrary identifier or name, and never treat
a schema illustration as a user fact. Do not invent
extra actions, missing values, lookup chains, deadlines or temporal dependencies.
Unspecified optionals stay unspecified: do not turn metadata about an omitted
field into an instruction to populate it. Empty requested text is different from
omitted text. Dates must be absolute or grounded in the given reference clock.
Do not tell the assistant whether a capability is available, unsupported, or that
it should refuse. The request describes the user's intent, not implementation.
Return only the supplied JSON shape. Brief reason is a concise quality judgment,
not step-by-step reasoning. If rejected, request must be an empty string.
