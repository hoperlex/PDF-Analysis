# Supplying the provider credential, and closing Gate C

One value is missing and nothing else. This is how to supply it.

## 1. What the key is

An **Anthropic API key** — the kind issued at `console.anthropic.com` under *API keys*. It
begins `sk-ant-`. `OD-02` pins the provider to the Anthropic first-party API with
`claude-opus-5`, and `anthropic==1.4.0` is already in the root lock, so no software changes.

If your key belongs to a workspace with its own spend controls, note that `OD-03` sets a
**per-run ceiling of USD 1.00** enforced in the application. One run over the eight-page
synthetic corpus costs roughly **$0.20** at the rates recorded in `P02_LOCK.json`, so a full
Gate C pass is well under a dollar.

## 2. Where to put it — and where not to

**Do not paste the key into a chat message.** Anything in a conversation transcript is stored
and may be read later. Put it on disk yourself, in a file git already ignores.

```bash
cd /root/projects/PDF-Analysis
cat > .env.provider <<'SECRET'
ANTHROPIC_API_KEY=sk-ant-...your key...
AUDITMANAGER_PROVIDER_MODE=live
SECRET
chmod 600 .env.provider
```

`.gitignore` line 2 is `.env.*`, so `.env.provider` is already ignored — verified with
`git check-ignore -v .env.provider`. Nothing needs to change for it to stay out of the
repository.

**Do not put the key in `.env`.** The Makefile enforces a strict allowlist of exactly the
fifteen names `FF-01` §3 freezes, and it refuses everything else on purpose: `.env`
configures this lane's PostgreSQL and MinIO and "does not carry tool options, credentials for
other systems, or anything that selects what code runs". `AUDITMANAGER_PROVIDER_MODE` is
precisely something that selects what code runs. A key placed there makes `make up` fail with
a message naming the offending line.

## 3. What the application does with it

Read at startup, by the composition root, from the **process environment**:

| Name | Meaning | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | the credential | none — required when the mode is `live` |
| `AUDITMANAGER_PROVIDER_MODE` | `live` or `recorded` | `recorded` |
| `AUDITMANAGER_MODEL_ID` | the model | `claude-opus-5` |
| `AUDITMANAGER_RUN_COST_CEILING_USD` | per-run ceiling | `1.00` (`OD-03`) |

**`live` without a credential is refused at startup**, not at the first run. That refusal is
tested. A process that starts can serve, so a mistyped variable name is discovered in a
second rather than after a document has been uploaded and a run row written.

## 4. Checking it before anything expensive

```bash
cd /root/projects/PDF-Analysis
set -a; . ./.env; . ./.env.provider; set +a
PYTHONPATH=src .venv/bin/python -m auditmanager.api.app
```

Expected: `auditmanager: wired, provider_mode=live` and `operations=12`.

If the key is absent or the name is misspelled you get exit 2 and a sentence naming the
variable. **No API call is made by this check** — it builds the application and stops, so it
costs nothing and proves the wiring before any spend.

## 5. Then say the word

With that in place, `C2` is dispatched from `docs/program/dispatch/C2.md`, which is already
written. It certifies the ten criteria of `PROTOTYPE_PROFILE.md` §8 through the composed
application, and its criterion 5 runs live when a credential is present.

The live run is **one call over one eight-page document**. What it settles is the question the
whole programme exists to answer and that no recording can: given this prompt, does
`claude-opus-5` find the two seeded cross-page contradictions and the explicit placeholder,
and does it leave the six near-miss controls alone.

Either answer is a result. A run that finds nothing is not a failed gate — it is the product
finding that `PROTOTYPE_PROFILE.md` risk 1 names in advance, and it would redirect P04 rather
than stop it.

## 6. If you would rather not issue a key at all

`OD-02` can be revised to another provider or a local model. That is a new root pin and a new
adapter — a serial session **before** `C2`, not a variation of it — and it changes what the
live run measures, since the prompt was written against `claude-opus-5`.
