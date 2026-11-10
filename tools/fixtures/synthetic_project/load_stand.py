"""Load the built synthetic project onto a stand through its public API (contract 1.42.0).

    SYN_LOGIN=... SYN_PASSWORD=... python -m synthetic_project.load_stand --base https://HOST/api/v1 \
        --data OUT_DIR [--check | --go] [--tag syn02-20261109]

`--check` only reads (/me, /system/version, /projects) and prints what it would do. `--go` writes:

1. one project; 2. every `sections/*.zip` as a portal-bundle document, classified with its key's stage and
section; 3. the АР version series ZIP through «Импорт ZIP с версиями», order v1→v4 confirmed, then the
deterministic matrix and adjacent-pair series (no model); 4. the stage documents П «СИНТ-02-АР» and Р
«СИНТ-02-АР.2» through a stage upload, a Р assembly {series document «СИНТ-02-АР.1», «СИНТ-02-АР.2»}, the
П→Р pair and the page profiles its sheet map needs. Nothing here asks for a cost estimate or consent:
no model is called.

Every write carries a deterministic Idempotency-Key derived from `--tag` and the step, so a rerun with
the same tag replays what was already done instead of duplicating it. The password is read from the
environment and never written anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

PROJECT_NAME = "СИНТ-02 «Синтез-2» — синтетические тестовые данные"
SERIES_DESIGNATION = "СИНТ-02-АР.1"
STAGE_MAP = {"П": "P", "Р": "R", "P": "P", "R": "R"}


class ApiError(RuntimeError):
    def __init__(self, status: int, body: dict | str, what: str):
        self.status, self.body = status, body
        super().__init__(f"{what}: HTTP {status}: {json.dumps(body, ensure_ascii=False)[:800] if isinstance(body, dict) else body[:800]}")


class Client:
    def __init__(self, base: str, login: str, password: str, tag: str):
        self.base = base.rstrip("/")
        self.login, self._password, self.tag = login, password, tag
        self.token: str | None = None

    # -- transport ----------------------------------------------------------------------
    def key(self, step: str) -> str:
        return f"{self.tag}.{hashlib.sha256(step.encode('utf-8')).hexdigest()[:24]}"

    def _request(self, method: str, path: str, *, body: bytes | None = None, ctype: str | None = None,
                 key: str | None = None, headers: dict | None = None, raw: bool = False, auth: bool = True):
        url = self.base + path
        h = {"Accept": "application/json", "X-Correlation-Id": f"cid-{uuid.uuid4().hex}"}
        if ctype:
            h["Content-Type"] = ctype
        if key:
            h["Idempotency-Key"] = key
        if auth:
            if self.token is None:
                self.sign_in()
            h["Authorization"] = f"Bearer {self.token}"
        h.update(headers or {})
        for attempt in range(12):
            req = urllib.request.Request(url, data=body, method=method, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=320) as resp:
                    data = resp.read()
                    if raw:
                        return resp.status, data
                    return resp.status, (json.loads(data) if data else {})
            except urllib.error.HTTPError as exc:
                data = exc.read()
                try:
                    payload = json.loads(data)
                except ValueError:
                    payload = data.decode("utf-8", "replace")
                code = payload.get("error_code") if isinstance(payload, dict) else None
                if exc.code == 401 and auth and attempt == 0:
                    self.sign_in()
                    h["Authorization"] = f"Bearer {self.token}"
                    continue
                if exc.code == 409 and code == "idempotency_key_in_progress":
                    time.sleep(3)
                    continue
                if exc.code in (429, 502, 503, 504) and (code in (None, "rate_limited", "dependency_unavailable")
                                                         and not (isinstance(payload, dict) and payload.get("details", {}).get("dependency", "").startswith("comparison_stage"))):
                    wait = int(exc.headers.get("Retry-After") or 5)
                    print(f"   .. {method} {path}: HTTP {exc.code} {code}, retry in {wait} s", flush=True)
                    time.sleep(wait)
                    continue
                raise ApiError(exc.code, payload, f"{method} {path}") from None
            except urllib.error.URLError as exc:
                print(f"   .. {method} {path}: {exc.reason}, retry", flush=True)
                time.sleep(5)
        raise RuntimeError(f"{method} {path}: gave up after retries")

    def get(self, path: str, **kw):
        return self._request("GET", path, **kw)[1]

    def post_json(self, path: str, payload: dict, step: str | None):
        return self._request("POST", path, body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             ctype="application/json", key=self.key(step) if step else None)[1]

    def put_json(self, path: str, payload: dict, step: str | None = None):
        return self._request("PUT", path, body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             ctype="application/json", key=self.key(step) if step else None)[1]

    def sign_in(self) -> None:
        status, data = self._request("POST", "/auth/token", auth=False, ctype="application/json",
                                     body=json.dumps({"login": self.login, "password": self._password}).encode())
        self.token = data["token"]
        if data.get("is_default_credential"):
            raise SystemExit("the account still has its default password: change it in the UI first")

    def multipart(self, path: str, fields: dict[str, str], file_name: str, file_bytes: bytes, step: str):
        boundary = f"----syn{uuid.uuid4().hex}"
        parts = []
        for name, value in fields.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n"
                         f"Content-Type: text/plain; charset=utf-8\r\n\r\n".encode("utf-8") + value.encode("utf-8") + b"\r\n")
        quoted = urllib.parse.quote(file_name)
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"upload.zip\"; "
                     f"filename*=UTF-8''{quoted}\r\nContent-Type: application/zip\r\n\r\n".encode("utf-8") + file_bytes + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self._request("POST", path, body=b"".join(parts), ctype=f"multipart/form-data; boundary={boundary}",
                             key=self.key(step))[1]


def poll(what: str, fetch, done, *, every: float = 3.0, limit: float = 900.0):
    start = time.time()
    last = None
    while True:
        value = fetch()
        state = done(value)
        if state is True:
            return value
        if state != last:
            print(f"   .. {what}: {state}", flush=True)
            last = state
        if time.time() - start > limit:
            raise RuntimeError(f"{what}: not done after {limit:.0f} s (last state {state})")
        time.sleep(every)


def _fail(m: dict):
    if m.get("state") == "failed":
        raise RuntimeError(f"failed: {json.dumps(m, ensure_ascii=False)[:600]}")
    return None


def all_items(c: Client, path: str) -> list:
    items, cursor = [], None
    while True:
        sep = "&" if "?" in path else "?"
        page = c.get(path + (f"{sep}cursor={urllib.parse.quote(cursor)}" if cursor else f"{sep}limit=100"))
        items += page.get("items", [])
        cursor = (page.get("page") or {}).get("next_cursor")
        if not cursor:
            return items


# ------------------------------------------------------------------------------------------------ steps

def check(c: Client, data: Path) -> dict:
    me = c.get("/me")
    print(f"account: roles {me.get('roles')}, profile_complete {me.get('profile_complete')}, "
          f"default_credential {me.get('is_default_credential')}")
    if "expert" not in (me.get("roles") or []):
        raise SystemExit("the account has no 'expert' role: every write would be refused")
    version = c.get("/system/version")
    print(f"stand: {json.dumps(version, ensure_ascii=False)}")
    projects = all_items(c, "/projects")
    print(f"projects on the stand: {len(projects)}" + (": " + "; ".join(p['name'] for p in projects[:10]) if projects else ""))
    sections = sorted((data / "sections").glob("*.zip"))
    print(f"to load: {len(sections)} section bundles, the АР version ZIP, the АР stage pair")
    return {"projects": projects, "version": version}


def load(c: Client, data: Path, state_path: Path) -> None:
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    def save():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    # 1. project
    if "project_uid" not in state:
        project = c.post_json("/projects", {"name": PROJECT_NAME}, "project")
        state["project_uid"] = project["project_uid"]
        save()
    p = state["project_uid"]
    print(f"project {p} «{PROJECT_NAME}»")

    # 2. section bundles
    keys = {k.name.split(".answer_key")[0]: json.loads(k.read_text()) for k in (data / "keys").glob("*.answer_key.json")}
    state.setdefault("documents", {})
    for z in sorted((data / "sections").glob("*.zip")):
        name = z.stem
        key = keys[name]
        code = key["section_code"]
        entry = state["documents"].get(code)
        if entry is None:
            title = f"{key['designation']} — {key['section_name']}"
            version = c.multipart(f"/projects/{p}/documents", {"display_title": title}, f"{key['designation']}.zip",
                                  z.read_bytes(), f"doc.{code}")
            entry = {"document_uid": version["document_uid"], "version_uid": version["version_uid"], "title": title,
                     "pages": version.get("page_count")}
            state["documents"][code] = entry
            save()
        if not entry.get("classified"):
            stage = STAGE_MAP[key.get("stage", "Р")]
            c.put_json(f"/projects/{p}/documents/{entry['document_uid']}/versions/{entry['version_uid']}/classification",
                       {"project_stage": stage, "section_code": code})
            entry["classified"] = f"{stage}/{code}"
            save()
        print(f"  {code:4} {entry['document_uid']} {entry['title']} ({entry.get('pages')} p.) classified {entry['classified']}")

    # 3. version series
    fam = data / "ar_family"
    series = state.setdefault("series", {})
    if "upload_id" not in series:
        body = (fam / "AR-versions-v1-v4.zip").read_bytes()
        up = c._request("POST", f"/projects/{p}/comparison-zip-uploads", body=body, ctype="application/zip",
                        key=c.key("series.zip"), headers={"X-Archive-Name": "AR-versions-v1-v4.zip"})[1]
        series["upload_id"] = up["upload_id"]
        save()
    uid = series["upload_id"]
    if "document_uid" not in series:
        poll("version upload", lambda: c.get(f"/comparison-uploads/{uid}"),
             lambda u: True if u.get("state") in ("proposed", "processing", "completed") else u.get("state"))
        proposal = c.get(f"/comparison-uploads/{uid}/proposal")
        sets = proposal.get("sets", [])
        if len(sets) != 1:
            raise RuntimeError(f"expected one proposed set, got {len(sets)}: {json.dumps(sets, ensure_ascii=False)[:600]}")
        s = sets[0]
        upload = c.get(f"/comparison-uploads/{uid}")
        names = {f["file_id"]: f["display_name"] for f in upload.get("files", [])}
        ordered = sorted((f["file_id"] for f in s["files"]), key=lambda fid: names[fid])  # ..._v1_ < _v2_ < ...
        print(f"   proposal: {[names[f] for f in ordered]}, warnings {s.get('warnings')}, "
              f"proposed stage {s.get('project_stage')} section {s.get('section_code')}")
        if s.get("state") != "done":
            done = c.post_json(f"/comparison-uploads/{uid}/sets/{s['set_id']}/confirmation", {
                "files": [{"file_id": fid, "version_label": f"V{i + 1} Изм.{i}"} for i, fid in enumerate(ordered)],
                "designation": SERIES_DESIGNATION, "project_stage": "R", "section_code": "AR"}, "series.confirm")
        else:
            done = s
        if not done.get("document_uid"):
            done = poll("series set", lambda: next(x for x in c.get(f"/comparison-uploads/{uid}/proposal")["sets"]
                                                    if x["set_id"] == s["set_id"]),
                        lambda x: True if x.get("state") == "done" else x.get("state"))
        series["document_uid"] = done["document_uid"]
        save()
    sd = series["document_uid"]
    print(f"  series document {sd} {SERIES_DESIGNATION} (4 versions)")
    if not series.get("matrix_ready"):
        c.post_json(f"/projects/{p}/documents/{sd}/comparison-matrix/preparation", {}, "series.matrix")
        poll("matrix", lambda: c.get(f"/projects/{p}/documents/{sd}/comparison-matrix"),
             lambda m: True if m.get("state") == "ready" else (_fail(m) or f"{m.get('state')} {m.get('progress')}"), limit=1800)
        series["matrix_ready"] = True
        save()
    if "series_id" not in series:
        run = c.post_json(f"/projects/{p}/documents/{sd}/comparison-series", {}, "series.run")
        series["series_id"] = run["series_id"]
        save()
    if not series.get("series_done"):
        final = poll("series", lambda: c.get(f"/comparison-series/{series['series_id']}"),
                     lambda r: True if r.get("state") in ("completed", "failed", "cancelled")
                     else f"{r.get('state')} {r.get('transitions_done')}/{r.get('transitions_total')}", limit=1800)
        series["series_done"] = final.get("state")
        save()
    print(f"  series {series['series_id']}: {series['series_done']}")

    # 4. stage pair
    st = state.setdefault("stage", {})
    files = {"П/СИНТ-02-АР.pdf": ("P", "СИНТ-02-АР"), "Р/СИНТ-02-АР.2.pdf": ("R", "СИНТ-02-АР.2")}
    blobs = {name: (fam / "stages" / name.replace("/", "_")).read_bytes() for name in files}
    if "upload_id" not in st:
        up = c.post_json(f"/projects/{p}/stage-uploads", {"files": [
            {"display_name": name, "media_kind": "pdf", "size_bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
            for name, b in blobs.items()]}, "stage.upload")
        st["upload_id"] = up["upload_id"]
        save()
    su = st["upload_id"]
    upload = c.get(f"/stage-uploads/{su}")
    by_name = {f["declaration"]["display_name"]: f for f in upload.get("files", [])}
    for name, b in blobs.items():
        f = by_name[name]
        if f.get("state") in ("declared", "receiving"):
            c._request("PUT", f"/stage-uploads/{su}/files/{f['file_id']}/parts?part_number=1", body=b,
                       ctype="application/octet-stream", key=c.key(f"stage.part.{name}"))
            c.post_json(f"/stage-uploads/{su}/files/{f['file_id']}/completion", {}, f"stage.complete.{name}")
    upload = poll("stage upload", lambda: c.get(f"/stage-uploads/{su}"),
                  lambda u: True if all(f.get("state") in ("ready", "failed", "cancelled") for f in u.get("files", []))
                  and u.get("candidates") else [f.get("state") for f in u.get("files", [])])
    for f in upload["files"]:
        if f.get("state") != "ready":
            raise RuntimeError(f"stage file {f['declaration']['display_name']}: {f.get('state')} {f.get('failure_reason')}")
    file_names = {f["file_id"]: f["declaration"]["display_name"] for f in upload["files"]}
    st.setdefault("documents", {})
    for cand in upload.get("candidates", []):
        stage, designation = files[file_names[cand["file_id"]]]
        print(f"   candidate {cand['display_name']}: {cand['state']}, proposed {cand.get('proposed_stage')}/"
              f"{cand.get('proposed_section')} «{cand.get('designation')}»")
        if cand["state"] == "proposed":
            c.post_json(f"/stage-upload-candidates/{cand['candidate_id']}/confirmation",
                        {"stage": stage, "section_code": "AR", "designation": designation}, f"stage.confirm.{designation}")
    upload = poll("stage candidates", lambda: c.get(f"/stage-uploads/{su}"),
                  lambda u: True if all(x["state"] in ("published", "rejected", "failed") for x in u["candidates"])
                  else [x["state"] for x in u["candidates"]])
    for cand in upload["candidates"]:
        if cand["state"] != "published":
            raise RuntimeError(f"stage candidate {cand['display_name']}: {cand['state']} {cand.get('failure_reason')}")
        st["documents"][files[file_names[cand["file_id"]]][1]] = cand["document_uid"]
    save()
    pdoc, r2doc = st["documents"]["СИНТ-02-АР"], st["documents"]["СИНТ-02-АР.2"]
    print(f"  stage documents: П {pdoc}, Р {r2doc}")
    if "assembly_id" not in st:
        a = c.post_json(f"/projects/{p}/stage-assemblies", {"label": "СИНТ-02-АР.1 + СИНТ-02-АР.2 (стадия Р)",
                                                             "document_uids": [sd, r2doc]}, "stage.assembly")
        st["assembly_id"] = a["assembly_id"]
        save()
    if "pair_id" not in st:
        pair = c.post_json(f"/projects/{p}/stage-pairs", {"left_document_uid": pdoc, "assembly_id": st["assembly_id"]},
                           "stage.pair")
        st["pair_id"] = pair["pair_id"]
        save()
    print(f"  stage pair {st['pair_id']} (assembly {st['assembly_id']})")
    for d, label in ((pdoc, "П"), (r2doc, "Р.2")):
        if not st.get(f"profiles.{d}"):
            try:
                c.post_json(f"/projects/{p}/documents/{d}/comparison-matrix/preparation", {}, f"stage.profiles.{d}")
            except ApiError as exc:
                print(f"   .. profiles for {label}: {exc}")
            poll(f"page profiles {label}", lambda d=d: c.get(f"/projects/{p}/documents/{d}/comparison-matrix"),
                 lambda m: True if (m.get("progress") or {}).get("total") and m["progress"].get("ready") == m["progress"]["total"]
                 or m.get("state") in ("ready",) else f"{m.get('state')} {m.get('progress')}", limit=1200)
            st[f"profiles.{d}"] = True
            save()
    try:
        sugg = c.get(f"/stage-pairs/{st['pair_id']}/sheet-suggestions?limit=100")
        st["suggestions"] = len(sugg.get("items", []))
        print(f"  sheet suggestions: {st['suggestions']} "
              f"({sum(1 for i in sugg.get('items', []) if i.get('confidence') == 'high')} high)")
    except ApiError as exc:
        print(f"  sheet suggestions not available yet: {exc}")
    save()
    print("LOAD OK")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--tag", default="syn02-20261109")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--go", action="store_true")
    args = ap.parse_args(argv)
    login, password = os.environ.get("SYN_LOGIN"), os.environ.get("SYN_PASSWORD")
    if not login or not password:
        raise SystemExit("set SYN_LOGIN and SYN_PASSWORD in the environment")
    c = Client(args.base, login, password, args.tag)
    info = check(c, args.data)
    if args.check:
        return 0
    if any(pr["name"] == PROJECT_NAME for pr in info["projects"]) and not (args.data / "load_state.json").exists():
        raise SystemExit("a project with this name already exists and there is no load_state.json: refusing to duplicate")
    load(c, args.data, args.data / "load_state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
