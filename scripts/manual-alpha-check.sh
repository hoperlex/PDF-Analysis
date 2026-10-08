#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RUNBOOK_REL="docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md"
ORIGIN=""
MODE="preflight"
CANDIDATE_SHA=""
DEPLOYED_SHA=""
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$REPO_ROOT/.local/manual-alpha/$STAMP-$$"

usage() {
  cat <<'EOF'
Использование:
  ./scripts/manual-alpha-check.sh --origin https://alpha.example.test --preflight-only
  E2E_PC01_LOGIN=<login> E2E_PC01_PASSWORD=<password> \
    ./scripts/manual-alpha-check.sh --origin https://alpha.example.test --automated \
    --candidate-sha <full-sha> --deployed-sha <full-sha>
  ./scripts/manual-alpha-check.sh --origin https://alpha.example.test --interactive
  ./scripts/manual-alpha-check.sh --files-only

Параметры:
  --origin URL        Проверяемый origin без пути. Обязателен, кроме --files-only.
  --preflight-only    Проверить PDF, TLS/redirect/login и закрытый API (по умолчанию).
  --automated         Выполнить sign-in, 3 записи, cold routes и 6 PDF-отказов из manifest.
  --candidate-sha SHA Полный SHA проверяемого чистого checkout.
  --deployed-sha SHA  Полный SHA, засвидетельствованный оператором из deployment evidence.
  --interactive       После preflight записать ручные A01-A20 как PASS/FAIL/BLOCKED.
  --files-only        Проверить только локальные PDF; сеть не используется.
  --evidence-dir DIR  Каталог отчёта (по умолчанию .local/manual-alpha/<UTC timestamp>-<pid>).
  -h, --help          Показать эту справку.

Автоматический режим читает логин и пароль только из E2E_PC01_LOGIN и
E2E_PC01_PASSWORD. Ни credential, ни cookie не записываются в evidence.
EOF
}

die() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

blocked() {
  printf 'ALPHA ACCEPTANCE BLOCKED: %s\n' "$*" >&2
  exit 2
}

while (($# > 0)); do
  case "$1" in
    --origin)
      (($# >= 2)) || die "после --origin нужен URL"
      ORIGIN="$2"
      shift 2
      ;;
    --preflight-only)
      MODE="preflight"
      shift
      ;;
    --automated)
      MODE="automated"
      shift
      ;;
    --candidate-sha)
      (($# >= 2)) || blocked "после --candidate-sha нужен SHA"
      CANDIDATE_SHA="$2"
      shift 2
      ;;
    --deployed-sha)
      (($# >= 2)) || blocked "после --deployed-sha нужен SHA"
      DEPLOYED_SHA="$2"
      shift 2
      ;;
    --interactive)
      MODE="interactive"
      shift
      ;;
    --files-only)
      MODE="files"
      shift
      ;;
    --evidence-dir)
      (($# >= 2)) || die "после --evidence-dir нужен каталог"
      EVIDENCE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "неизвестный параметр: $1"
      ;;
  esac
done

for command_name in sha256sum stat git; do
  command -v "$command_name" >/dev/null 2>&1 || die "не найдена команда $command_name"
done

if [[ "$MODE" != "files" ]]; then
  command -v curl >/dev/null 2>&1 || die "не найдена команда curl"
  command -v python3 >/dev/null 2>&1 || die "не найдена команда python3"
  [[ -n "$ORIGIN" ]] || blocked "укажите --origin"
  ORIGIN="${ORIGIN%/}"
  case "$ORIGIN" in
    https://*) ;;
    http://127.0.0.1:*|http://localhost:*|http://\[::1\]:*) ;;
    *) die "удалённый origin обязан использовать HTTPS; HTTP разрешён только для loopback" ;;
  esac
  ORIGIN_AUTHORITY="${ORIGIN#*://}"
  [[ "$ORIGIN_AUTHORITY" != */* ]] || die "--origin должен содержать только scheme и authority, без пути"
  [[ "$ORIGIN_AUTHORITY" != *@* ]] || die "credentials в --origin запрещены"
  [[ "$ORIGIN" != *'?'* && "$ORIGIN" != *'#'* ]] || die "origin не должен содержать query или fragment"
fi

if [[ "$MODE" == "automated" ]]; then
  command -v node >/dev/null 2>&1 || blocked "не найдена команда node"
  [[ -n "$CANDIDATE_SHA" ]] || blocked "укажите --candidate-sha"
  [[ -n "$DEPLOYED_SHA" ]] || blocked "укажите --deployed-sha"
  [[ "$CANDIDATE_SHA" =~ ^[0-9a-f]{40}$ ]] || die "candidate SHA должен быть полным lowercase SHA-1"
  [[ "$DEPLOYED_SHA" =~ ^[0-9a-f]{40}$ ]] || die "deployed SHA должен быть полным lowercase SHA-1"
  [[ -n "${E2E_PC01_LOGIN:-}" ]] || blocked "E2E_PC01_LOGIN не задан"
  [[ -n "${E2E_PC01_PASSWORD:-}" ]] || blocked "E2E_PC01_PASSWORD не задан"
fi

case "$EVIDENCE_DIR" in
  "$REPO_ROOT"/.local/manual-alpha/*|/tmp/*) ;;
  *) die "--evidence-dir разрешён только внутри .local/manual-alpha или /tmp" ;;
esac

[[ ! -e "$EVIDENCE_DIR" ]] || die "каталог evidence уже существует: $EVIDENCE_DIR"
mkdir -p -- "$EVIDENCE_DIR"
REPORT="$EVIDENCE_DIR/report.md"
TMP_DIR="$(mktemp -d -t alpha-manual.XXXXXX)"
cleanup() {
  [[ "$TMP_DIR" == /tmp/alpha-manual.* ]] && rm -rf -- "$TMP_DIR"
}
trap cleanup EXIT

HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')"
DEV_SHA="$(git -C "$REPO_ROOT" rev-parse origin/dev 2>/dev/null || printf 'unknown')"

if [[ "$MODE" == "automated" ]]; then
  [[ "$HEAD_SHA" == "$CANDIDATE_SHA" ]] || die \
    "candidate SHA $CANDIDATE_SHA не равен HEAD $HEAD_SHA"
  [[ "$DEPLOYED_SHA" == "$CANDIDATE_SHA" ]] || die \
    "deployed SHA $DEPLOYED_SHA не равен candidate SHA $CANDIDATE_SHA"
  git -C "$REPO_ROOT" diff --quiet --ignore-submodules -- || die \
    "checkout содержит незакоммиченные изменения"
  git -C "$REPO_ROOT" diff --cached --quiet --ignore-submodules -- || die \
    "index содержит незакоммиченные изменения"
  [[ -z "$(git -C "$REPO_ROOT" ls-files --others --exclude-standard)" ]] || die \
    "checkout содержит untracked-файлы"

  # Measure the candidate tree independently of the API implementation. Read
  # the runtime COPY inventory from Dockerfile.api on every invocation.
  CANDIDATE_BUILD_ID="$(python3 - "$REPO_ROOT" <<'PY'
import hashlib
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
dockerfile = (root / "infra/deploy/Dockerfile.api").read_text(encoding="utf-8")
expected = {
    "src/", "db/", "contracts/", "fixtures/recorded/", "release-notes/",
    "docs/program/P02_LOCK.json", "VERSION", "uv.lock",
}
copied = {
    source
    for source, destination in re.findall(r"^COPY (\S+) (/app/\S+)$", dockerfile, re.M)
    if destination == f"/app/{source}"
}
missing = expected - copied
if missing:
    raise SystemExit(f"Dockerfile.api lacks build inputs: {', '.join(sorted(missing))}")
paths = []
for source in sorted(expected & copied):
    candidate = root / source
    if candidate.is_symlink() or not candidate.exists():
        raise SystemExit(f"build input is absent or linked: {source}")
    members = candidate.rglob("*") if candidate.is_dir() else (candidate,)
    for member in members:
        relative = member.relative_to(root)
        if "__pycache__" in relative.parts or member.suffix == ".pyc":
            continue
        if member.is_symlink():
            raise SystemExit(f"build input is linked: {relative.as_posix()}")
        if member.is_file():
            paths.append(member)
manifest = hashlib.sha256()
for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
    name = path.relative_to(root).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.update(f"{name}\t{digest}\n".encode("utf-8"))
print("b" + manifest.hexdigest()[:16])
PY
)" || blocked "не удалось измерить кандидатскую сборку API"
fi

cat >"$REPORT" <<EOF
# Alpha manual acceptance evidence

- started_at_utc: $STAMP
- origin: ${ORIGIN:-not-used}
- local_head: $HEAD_SHA
- local_origin_dev: $DEV_SHA
- candidate_sha: ${CANDIDATE_SHA:-not-required}
- attested_deployed_sha: ${DEPLOYED_SHA:-not-required}
- candidate_api_build_id_measured: ${CANDIDATE_BUILD_ID:-not-required}
- deployed_sha_attestation: operator_input; this command does not identify the served revision
- runbook: $RUNBOOK_REL
- credentials_recorded: no

## Automatic preflight

| Check | Result | Evidence |
| --- | --- | --- |
EOF

AUTO_FAILURES=0
AUTO_BLOCKED=0

record_auto() {
  local check_id="$1"
  local result="$2"
  local evidence="$3"
  evidence="${evidence//|/\\|}"
  printf '| %s | %s | %s |\n' "$check_id" "$result" "$evidence" >>"$REPORT"
  printf '%-18s %-4s %s\n' "$check_id" "$result" "$evidence"
  if [[ "$result" == "FAIL" ]]; then
    AUTO_FAILURES=$((AUTO_FAILURES + 1))
  elif [[ "$result" == "BLOCKED" ]]; then
    AUTO_BLOCKED=$((AUTO_BLOCKED + 1))
  fi
}

check_fixture() {
  local check_id="$1"
  local relative_path="$2"
  local expected_sha="$3"
  local expected_size="$4"
  local file_path="$REPO_ROOT/$relative_path"

  if [[ ! -f "$file_path" ]]; then
    record_auto "$check_id" "FAIL" "missing: $relative_path"
    return
  fi

  local actual_sha actual_size magic
  actual_sha="$(sha256sum -- "$file_path" | awk '{print $1}')"
  actual_size="$(stat -c '%s' -- "$file_path")"
  magic="$(LC_ALL=C head -c 5 -- "$file_path")"
  if [[ "$actual_sha" == "$expected_sha" && "$actual_size" == "$expected_size" && "$magic" == '%PDF-' ]]; then
    record_auto "$check_id" "PASS" "$relative_path; $actual_size B; sha256=${actual_sha:0:12}…"
  else
    record_auto "$check_id" "FAIL" "$relative_path; size=$actual_size/$expected_size; sha256=$actual_sha/$expected_sha; magic=$magic"
  fi
}

check_fixture "PDF-positive" "fixtures/synthetic/ar/ar_baseline.pdf" \
  "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f" "58978"
check_fixture "PDF-encrypted" "fixtures/synthetic/ar/negative/encrypted.pdf" \
  "9513362c5d85dec1438406ffd4e77fef6d08bb18f104a5b107afc610dde8faba" "40514"
check_fixture "PDF-image-only" "fixtures/synthetic/ar/negative/image_only.pdf" \
  "8917d48af68cffac071fdf75040d181a548d27d952baa05defbca48a2ca94325" "246242"
check_fixture "PDF-pages" "fixtures/synthetic/ar/negative/too_many_pages.pdf" \
  "acb3c347dbfe4b38efbc7e56f4389e97725b529966defa2a39c21e34f74da12a" "66487"
check_fixture "PDF-size" "fixtures/synthetic/ar/negative/oversize.pdf" \
  "623bf92bbbf989c1d350f9c8038f9dd6379ee1538100374fd230a81812a665ef" "27303204"

if [[ "$MODE" == "files" ]]; then
  if ((AUTO_FAILURES > 0)); then
    printf '\nFILES FAIL: %d проверок не прошло; отчёт: %s\n' "$AUTO_FAILURES" "$REPORT" >&2
    exit 1
  fi
  printf '\nFILES OK: пять синтетических PDF совпадают с manifest; отчёт: %s\n' "$REPORT"
  exit 0
fi

http_status() {
  local url="$1"
  local header_file="$2"
  curl --silent --show-error --output /dev/null --dump-header "$header_file" \
    --max-time 20 --connect-timeout 10 --write-out '%{http_code}' "$url"
}

root_redirect_is_same_origin_sign_in() {
  local origin="$1"
  local location="$2"
  python3 - "$origin" "$location" <<'PY'
import sys
from urllib.parse import parse_qs, urljoin, urlsplit


def normalized_origin(value: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"}:
            return None
        if parsed.username is not None or parsed.password is not None or parsed.hostname is None:
            return None
        port = parsed.port
    except ValueError:
        return None
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), parsed.hostname.lower(), port


origin, location = sys.argv[1:]
if not location:
    raise SystemExit(1)
target = urlsplit(urljoin(f"{origin}/", location))
same_origin = normalized_origin(origin) == normalized_origin(target.geturl())
# W50: a guest's `/` is sent to sign in and back to `/` -- exactly `/login?next=/`.
query = parse_qs(target.query, keep_blank_values=True)
exact_route = target.path == "/login" and query == {"next": ["/"]} and not target.fragment
raise SystemExit(0 if same_origin and exact_route else 1)
PY
}

ROOT_STATUS="$(http_status "$ORIGIN/" "$TMP_DIR/root.headers")" || ROOT_STATUS="curl-error"
ROOT_LOCATION="$(awk 'BEGIN {IGNORECASE=1} /^location:/ {sub(/^[^:]+:[[:space:]]*/, ""); sub(/\r$/, ""); print; exit}' "$TMP_DIR/root.headers")"
if [[ ("$ROOT_STATUS" == "307" || "$ROOT_STATUS" == "308") ]] && \
  root_redirect_is_same_origin_sign_in "$ORIGIN" "$ROOT_LOCATION"; then
  record_auto "HTTP-root" "PASS" "$ROOT_STATUS -> $ROOT_LOCATION"
elif [[ "$ROOT_STATUS" == "curl-error" ]]; then
  record_auto "HTTP-root" "BLOCKED" "origin недоступен по сети/TLS"
else
  record_auto "HTTP-root" "FAIL" "expected 307/308 -> /login?next=%2F; got status=$ROOT_STATUS location=${ROOT_LOCATION:-none}"
fi

LOGIN_STATUS="$(http_status "$ORIGIN/login" "$TMP_DIR/login.headers")" || LOGIN_STATUS="curl-error"
if [[ "$LOGIN_STATUS" == "200" ]]; then
  record_auto "HTTP-login" "PASS" "GET /login -> 200"
elif [[ "$LOGIN_STATUS" == "curl-error" ]]; then
  record_auto "HTTP-login" "BLOCKED" "GET /login недоступен по сети/TLS"
else
  record_auto "HTTP-login" "FAIL" "expected 200; got $LOGIN_STATUS"
fi

API_STATUS="$(http_status "$ORIGIN/api/v1/openapi.json" "$TMP_DIR/api.headers")" || API_STATUS="curl-error"
if [[ "$API_STATUS" == "401" ]]; then
  record_auto "HTTP-auth-boundary" "PASS" "unauthenticated GET /api/v1/openapi.json -> 401"
elif [[ "$API_STATUS" == "curl-error" ]]; then
  record_auto "HTTP-auth-boundary" "BLOCKED" "закрытый API недоступен по сети/TLS"
else
  record_auto "HTTP-auth-boundary" "FAIL" "expected unauthenticated 401; got $API_STATUS"
fi

if ((AUTO_FAILURES > 0)); then
  printf '\nPREFLIGHT FAIL: %d проверок не прошло; ручной сценарий остановлен; отчёт: %s\n' \
    "$AUTO_FAILURES" "$REPORT" >&2
  exit 1
fi
if ((AUTO_BLOCKED > 0)); then
  printf '\nPREFLIGHT BLOCKED: %d проверок заблокировано; отчёт: %s\n' \
    "$AUTO_BLOCKED" "$REPORT" >&2
  exit 2
fi

printf '\nPREFLIGHT OK: origin доступен, API закрыт, пять PDF целы; отчёт: %s\n' "$REPORT"

if [[ "$MODE" == "preflight" ]]; then
  exit 0
fi

if [[ "$MODE" == "automated" ]]; then
  JOURNEY_DIR="$EVIDENCE_DIR/journey"
  REFUSALS_DIR="$EVIDENCE_DIR/refusals"
  mkdir -p -- "$JOURNEY_DIR" "$REFUSALS_DIR"

  set +e
  node "$REPO_ROOT/tests/e2e/pc01/journey/journey.mjs" \
    --origin "$ORIGIN" --phase all --out "$JOURNEY_DIR" \
    >"$EVIDENCE_DIR/journey.log" 2>&1
  JOURNEY_EXIT=$?
  set -e
  printf '\n--- automated journey ---\n'
  sed -n '1,240p' "$EVIDENCE_DIR/journey.log"

  REFUSALS_EXIT=99
  if ((JOURNEY_EXIT == 0)); then
    set +e
    node "$REPO_ROOT/tests/e2e/pc01/journey/refusals.mjs" \
      --origin "$ORIGIN" --out "$REFUSALS_DIR" \
      >"$EVIDENCE_DIR/refusals.log" 2>&1
    REFUSALS_EXIT=$?
    set -e
    printf '\n--- automated refusals ---\n'
    sed -n '1,240p' "$EVIDENCE_DIR/refusals.log"
  else
    printf '%s\n' \
      'refusals were not run because the full journey did not complete; this cannot pass.' \
      >"$EVIDENCE_DIR/refusals.log"
  fi

  set +e
  node "$REPO_ROOT/tests/e2e/pc01/journey/verify-acceptance.mjs" \
    --journey "$JOURNEY_DIR/journey.json" \
    --refusals "$REFUSALS_DIR/refusals.json" \
    --out "$EVIDENCE_DIR/automated-verdict.json" \
    --candidate-sha "$CANDIDATE_SHA" \
    --deployed-sha "$DEPLOYED_SHA" \
    --origin "$ORIGIN" \
    --candidate-build-id "$CANDIDATE_BUILD_ID" \
    --journey-exit "$JOURNEY_EXIT" \
    --refusals-exit "$REFUSALS_EXIT" \
    >"$EVIDENCE_DIR/verifier.log" 2>&1
  VERIFIER_EXIT=$?
  set -e
  printf '\n--- acceptance verifier ---\n'
  sed -n '1,240p' "$EVIDENCE_DIR/verifier.log"

  cat >>"$REPORT" <<EOF

## Automated release phases

- journey_exit: $JOURNEY_EXIT
- refusals_exit: $REFUSALS_EXIT
- verifier_exit: $VERIFIER_EXIT
- machine_evidence: automated-verdict.json
- served_api_build_id_measured: $(python3 - "$EVIDENCE_DIR/automated-verdict.json" <<'PY'
import json
import pathlib
import re
import sys

value = json.loads(pathlib.Path(sys.argv[1]).read_text())["phases"]["apiBuild"]["servedMeasured"]
print(value if isinstance(value, str) and re.fullmatch(r"b[0-9a-f]{16}", value) else "unavailable")
PY
)
- human_A01_A20: required separately; not executed by this command
EOF

  if ((VERIFIER_EXIT == 0)); then
    printf '%s\n' '- automated_verdict: PASS' >>"$REPORT"
    printf '\nALPHA ACCEPTANCE PASS: automated phases complete; human A01-A20 remains required; evidence: %s\n' \
      "$EVIDENCE_DIR"
    exit 0
  fi
  if ((VERIFIER_EXIT == 2)); then
    printf '%s\n' '- automated_verdict: BLOCKED' >>"$REPORT"
    printf '\nALPHA ACCEPTANCE BLOCKED: external dependency/access unavailable; evidence: %s\n' \
      "$EVIDENCE_DIR" >&2
    exit 2
  fi
  printf '%s\n' '- automated_verdict: FAIL' >>"$REPORT"
  printf '\nALPHA ACCEPTANCE FAIL: automated release phase violated its contract; evidence: %s\n' \
    "$EVIDENCE_DIR" >&2
  exit 1
fi

[[ -t 0 ]] || die "--interactive требует терминал; для автоматики используйте --preflight-only"

cat >>"$REPORT" <<'EOF'

## Manual checkpoints

| Step | Result | Safe note |
| --- | --- | --- |
EOF

MANUAL_FAILURES=0
MANUAL_BLOCKED=0

record_manual() {
  local step_id="$1"
  local title="$2"
  local expectation="$3"
  local result note

  printf '\n%s — %s\n%s\n' "$step_id" "$title" "$expectation"
  while true; do
    read -r -p 'Результат [PASS/FAIL/BLOCKED]: ' result
    result="${result^^}"
    case "$result" in
      PASS|FAIL|BLOCKED) break ;;
      *) printf 'Введите PASS, FAIL или BLOCKED.\n' ;;
    esac
  done
  read -r -p 'Безопасная заметка (без секретов, Enter = пусто): ' note
  note="${note//|/\\|}"
  [[ -n "$note" ]] || note="—"
  printf '| %s — %s | %s | %s |\n' "$step_id" "$title" "$result" "$note" >>"$REPORT"
  [[ "$result" != "FAIL" ]] || MANUAL_FAILURES=$((MANUAL_FAILURES + 1))
  [[ "$result" != "BLOCKED" ]] || MANUAL_BLOCKED=$((MANUAL_BLOCKED + 1))
}

printf '\nОткройте %s и выполняйте шаг перед записью результата.\n' "$REPO_ROOT/$RUNBOOK_REL"
printf 'Скрипт не просит и не сохраняет credentials.\n'

record_manual "A01" "deploy SHA и вход" \
  "Workflow/verify-deployed подтверждает deployed SHA, равный проверенному candidate SHA; вход приводит на /."
record_manual "A02" "проект" \
  "Создан один проект с уникальным именем; project_uid переживает cold reload."
record_manual "A03" "положительный PDF" \
  "ar_baseline.pdf создаёт версию; version_uid доступен после reload; upload failure отсутствует."
record_manual "A04" "прогон" \
  "POST /runs -> 202 queued; <=150 s итог published/partial; четыре стадии; provider_mode=live."
record_manual "A05" "находки и evidence" \
  "Найдены >=2 из SI-01..SI-03, 0 из CTL-01..CTL-06; все цитаты есть на заявленных страницах."
record_manual "A06" "решения" \
  "Accept, reject и comment — отдельные события; reload и knowledge base сохраняют проекцию."
record_manual "A07" "CSV" \
  "UTF-8 BOM, 17 колонок, одна строка на evidence; повторная выгрузка побайтно стабильна."
record_manual "A08" "сравнение" \
  "Второй прогон той же версии сравнивается с первым; four-way verdict не смешивает absence и same."
record_manual "A09" "все экраны и 780px" \
  "Все маршруты из списка A09 в runbook открываются после cold reload; нет console error и горизонтального overflow."
record_manual "A10" "отрицательные PDF" \
  "Четыре PDF отклонены точными правилами; oversize не отправлен; новых документов/версий нет."
record_manual "A11" "dashboard и сохранность" \
  "Четыре панели без fault; тестовые данные достижимы из списка после cold reload."
record_manual "A12" "выход" \
  "После «Выйти» deep link закрыт; повторный вход возвращает доступ; секреты не записаны."
record_manual "A13" "заявка и ожидающий вход" \
  "Регистрация ведёт на подтверждение; до решения вход сообщает: «Заявка на регистрацию ещё не рассмотрена» без причины."
record_manual "A14" "очередь и одобрение" \
  "Ноль ролей: «Выберите хотя бы одну роль. Запрос не отправлен.»; одобрение с «Эксперт» обновляет очередь и счётчик."
record_manual "A15" "вход и профиль эксперта" \
  "Новый пользователь входит; имя, фамилия и отчество из заявки видны на /account после cold reload."
record_manual "A16" "вердикт и автор" \
  "Вердикт сохранён, история показывает автора «Фамилия И. О.» из профиля, без технического идентификатора."
record_manual "A17" "отзыв роли" \
  "После снятия «Эксперт» следующий BFF-запрос -> 401 authentication_required; строка сессии удалена; после входа новая запись -> 403 permission_denied."
record_manual "A18" "отклонённая заявка" \
  "Отклонённый и неизвестный адрес получают побайтно одинаковый общий отказ; причина видна только администратору."
record_manual "A19" "административные запреты" \
  "Самоархивирование -> permission_denied; доступ сохраняется. last_admin проверяется отдельно в QA-фикстуре (D-137)."
record_manual "A20" "архив и удаление автора" \
  "Архивный пользователь получает общий отказ входа; purge -> account_referenced, запись остаётся."

cat >>"$REPORT" <<EOF

## Verdict

- manual_failures: $MANUAL_FAILURES
- manual_blocked: $MANUAL_BLOCKED
EOF

if ((MANUAL_FAILURES > 0)); then
  printf '%s\n' '- verdict: FAIL' >>"$REPORT"
  printf '\nALPHA FAIL: %d шагов не прошло; отчёт: %s\n' "$MANUAL_FAILURES" "$REPORT" >&2
  exit 1
fi
if ((MANUAL_BLOCKED > 0)); then
  printf '%s\n' '- verdict: BLOCKED' >>"$REPORT"
  printf '\nALPHA BLOCKED: %d шагов заблокировано; отчёт: %s\n' "$MANUAL_BLOCKED" "$REPORT" >&2
  exit 2
fi

printf '%s\n' '- verdict: PASS' >>"$REPORT"
printf '\nALPHA PASS: все обязательные шаги пройдены; отчёт: %s\n' "$REPORT"
