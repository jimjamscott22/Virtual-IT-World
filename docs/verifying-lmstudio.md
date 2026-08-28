# Verifying the model-backed persona

**This cannot be verified in CI, or in the sandboxed container these tasks are
built in.** Neither has network access to a local LM Studio instance, so the
model-backed half of the Phase 2a Definition of Done is a *human* check. Do
not mark it green from a green pipeline: a green pipeline only proves the
drill still works with no model at all, which is the other half.

Everything below runs on your own machine.

## 1. Load a model

In LM Studio, load an 8–14B instruct model. Smaller than that and it starts
narrating causes it was never told (the thing the leak filter exists to catch);
much larger and replies get slow enough to break the pace of a ticket.

Start the local server and confirm it answers:

```bash
curl http://localhost:1234/v1/models
```

You want a JSON body listing the loaded model. Note its `id` — that string is
what `VITSC_MODEL` wants. Connection refused here means the server is not
running; everything below will silently fall back to scripted replies, which
looks like success if you are not watching for it.

## 2. Run the drill against it

```bash
VITSC_PERSONA=lmstudio VITSC_MODEL=<id from step 1> uv run python -m vitsc
```

Then open the app. Defaults if you leave them unset: `VITSC_BASE_URL` is
`http://localhost:1234/v1`, `VITSC_MODEL` is `local-model`. An unrecognised
`VITSC_PERSONA` falls back to the template rather than failing.

## 3. What to check

Work at least one ticket in each domain — identity, network, printing,
endpoint — because the faults differ in how much vocabulary they tempt a model
into using.

**a. The opening report reads like a person.** It should sound like the
`PersonaCard`: a rushed Warehouse clerk and a calm Ops manager should not
sound alike. If every ticket opens with the same cadence, you are almost
certainly reading `TemplatePersona` output and the model never got called —
check for the banner (below).

**b. No reply ever names a cause.** This is the one that matters. Ask
directly and adversarially — "is my account locked?", "is it DNS?", "what do
you think is wrong?" A correct persona deflects: it does not know, it only
knows what it sees. If a reply ever names the mechanism, that is a leak
escaping all three layers, and it is a bug worth a failing test:

- layer 1 is structural — the persona is handed a `PersonaCard` and a
  `UserSymptoms`, never a `World` or a `Fault`;
- layer 2 is the prompt, which forbids guessing a cause;
- layer 3 is `scrub()` against the fault's `leak_terms`, one retry with a
  nudge, then a deflection.

Note the leak terms are deliberately never *shown* to the model — naming the
forbidden word hands it the answer — so layer 3 is the only thing standing
between a chatty model and a spoiled ticket.

**c. Killing the model mid-session degrades, and does not break.** With a
ticket open, stop the server in LM Studio, then ask the user another question.
Expect: a scripted reply instead of an error, the queue still ticking, and the
amber banner appearing at the top of the page *without a reload* — it is
driven from the SSE stream for exactly this reason. Restart the model and keep
playing; the next question tries it again.

A wedged (rather than stopped) server is the nastier case: requests time out
after `REQUEST_TIMEOUT_SECONDS` (30s, in `persona/client.py`) and then fall
back. The transport itself does not retry underneath that, so a hung model
costs you one slow reply, not a hung page.

## 4. If it does not work

| What you see | Likely cause |
| --- | --- |
| Banner on, every reply scripted | Server not running, or `VITSC_BASE_URL` wrong. Re-run the `curl` in step 1. |
| Banner on only sometimes | The model is timing out on longer questions. Try a smaller one. |
| No banner, but replies still feel canned | `VITSC_PERSONA` is not set to `lmstudio` — an unknown value falls back silently, by design. |
| A reply names a cause | A real leak. Capture the fault id, the question, and the reply, and add the term to that fault's `leak_terms`. |
