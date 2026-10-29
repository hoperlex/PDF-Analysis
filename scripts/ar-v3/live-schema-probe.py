# Diagnostic probe for the model route of the AR v3 response schema (read only; four tiny paid calls).
#
# Run inside the worker container of the live host, which already holds PROXY_LLM_BASE_URL, PROXY_LLM_TOKEN and
# PROXY_LLM_MODEL in its environment (the token is never printed):
#   docker compose --env-file infra/deploy/env/alpha.env --file infra/deploy/compose.server.yml exec -T worker python - < scripts/ar-v3/live-schema-probe.py
#
# T1/T2: plain calls (route, model, max_tokens 16000). T3: the AR v3 schema exactly as the code sends it.
# T4: the same schema without the keywords a strict structured-output provider rejects (oneOf -> anyOf; no
# minLength, maxLength, pattern, minimum, maximum, maxItems). Written 2026-10-29 for the first live AR v3 failure
# (AR-V3-WIRE-SCHEMA-01): T1 200, T2 200, T3 400 "Schema type 'oneOf' is not supported", T4 200.
import json, os, sys, urllib.error, urllib.request, uuid
sys.path.insert(0, "/app/src")
from auditmanager.analysis.text.proxy import _completions_url
from auditmanager.analysis.profiles.ar_v3 import response_schema as rs

base = os.environ.get("PROXY_LLM_BASE_URL", "")
token = os.environ.get("PROXY_LLM_TOKEN", "")
model = os.environ.get("PROXY_LLM_MODEL", "")
print("base:", base, "| model:", model, "| token set:", bool(token))
if not (base and token and model):
    sys.exit("PROXY_LLM_* is not in this container's environment: send me this line")

schema = rs.response_schema
if callable(schema):
    schema = schema()
if isinstance(schema, str):
    schema = json.loads(schema)

DROP = {"minLength", "maxLength", "pattern", "minimum", "maximum", "maxItems"}


def clean(o):
    if isinstance(o, dict):
        return {("anyOf" if k == "oneOf" else k): clean(v) for k, v in o.items() if k not in DROP}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def rf(s):
    return {"type": "json_schema", "json_schema": {"name": "text_observations", "schema": s, "strict": True}}


tests = [
    ("T1 plain, small max_tokens", {"max_tokens": 16}),
    ("T2 plain, max_tokens 16000", {"max_tokens": 16000}),
    ("T3 v3 schema as sent", {"max_tokens": 64, "response_format": rf(schema)}),
    ("T4 v3 schema without unsupported keywords", {"max_tokens": 64, "response_format": rf(clean(schema))}),
]
for label, extra in tests:
    body = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word ok."}], **extra}
    req = urllib.request.Request(
        _completions_url(base), data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "X-Request-Id": str(uuid.uuid4())})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            print(label, "->", r.status)
    except urllib.error.HTTPError as e:
        print(label, "->", e.code, e.read(600).decode("utf-8", "replace"))
    except Exception as e:
        print(label, "-> error", type(e).__name__)
