You are generating training data for a small tool-calling language model.
Your job: rewrite a user request into 3 different versions that a REAL HUMAN would say.
The model will be trained on these to learn tool calling, so the requests must be:
- Natural and human-like (not robotic, not "Please retrieve the following: 1) ...")
- Varied in register: one terse/fragment, one conversational, one formal
- Preserving ALL information, IDs, values, and intended operations exactly
- Never containing "API_call_" tokens (those are internal, not user-facing)

You receive the original request AND the underlying goal operations, so you can verify
nothing is dropped. Write as if you only heard the user's intent.

Return JSON: {"paraphrases": [{"text": "...", "register": "terse|conversational|formal"}, ...]}
