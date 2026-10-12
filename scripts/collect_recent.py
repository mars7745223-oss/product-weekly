#!/usr/bin/env python3
"""Adapt last30days raw Report JSON into traceable, unverified weekly leads.

Uses only the standard library. Without --run it makes no network requests.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SKILL_ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")
ALIASES = {"web": "grounding", "hn": "hackernews", "xhs": "xiaohongshu"}
# Matches env.KEYCHAIN_KEYS in the pinned engine; empty values prevent pass probes.
CREDENTIAL_KEYS = (
    "OPENAI_API_KEY", "XAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY",
    "GOOGLE_GENAI_API_KEY", "SCRAPECREATORS_API_KEY", "APIFY_API_TOKEN",
    "AUTH_TOKEN", "CT0", "BSKY_HANDLE", "BSKY_APP_PASSWORD", "TRUTHSOCIAL_TOKEN",
    "BRAVE_API_KEY", "EXA_API_KEY", "SERPER_API_KEY", "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY", "PARALLEL_API_KEY", "XQUIK_API_KEY",
    "XIAOHONGSHU_API_BASE", "GITHUB_TOKEN", "BRIGHTDATA_API_KEY", "X_BEARER_TOKEN",
)
OS_KEYS = {
    "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
    "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH",
    "SYSTEMDRIVE", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
    "LANG", "LC_ALL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
}
REQUIRED_FLAGS = (
    "--days", "--as-of", "--search", "--emit", "--json-profile",
    "--no-browser-cookies", "--save-dir", "--no-verify-freshness", "--web-backend",
)


def csv(value: str) -> list[str]:
    return list(dict.fromkeys(ALIASES.get(x.strip().lower(), x.strip().lower())
                              for x in value.split(",") if x.strip()))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("topic", nargs="?", help="One specific product/model or research mechanism")
    p.add_argument("--days", type=int, default=7, help="Editorial calendar days, default 7")
    p.add_argument("--as-of", type=date.fromisoformat,
                   default=datetime.now(SHANGHAI).date(), help="Explicit client cutoff YYYY-MM-DD")
    p.add_argument("--search", default="reddit,web", help="Engine channels; default reddit,web")
    p.add_argument("--engine-root", type=Path,
                   help="Engine checkout, extracted skill, scripts directory, or entrypoint")
    p.add_argument("--python", default=sys.executable, help="Engine Python executable (3.12+)")
    p.add_argument("--subreddits", help="Verified broad/category subreddit names")
    p.add_argument("--dedicated-subreddits", help="Verified product-home subreddit names")
    p.add_argument("--x-handle", help="Verified X account, requires an available authorized backend")
    p.add_argument("--github-repo", help="Verified owner/repo, comma-separated")
    p.add_argument("--include-term", action="append", default=[], help="Keep if any term matches text")
    p.add_argument("--exclude-term", action="append", default=[], help="Exclude if any term matches text")
    p.add_argument("--deep", action="store_true", help="Higher recall; default uses --quick")
    p.add_argument("--use-env", action="store_true",
                   help="Use existing authorized process credentials; never load global config")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="Execute retrieval; otherwise show plan only")
    mode.add_argument("--input-json", type=Path, help="Normalize existing --json-profile raw output offline")
    mode.add_argument("--check", action="store_true", help="Check entrypoint/CLI text without execution")
    mode.add_argument("--self-test", action="store_true", help="Run deterministic offline contract checks")
    p.add_argument("--mock", action="store_true", help="With --run, use engine fixtures, no real retrieval")
    p.add_argument("--timeout", type=int, default=240, help="Engine subprocess timeout in seconds")
    p.add_argument("--output", type=Path, help="Save normalized JSON; default stdout")
    return p


def find_engine(args: argparse.Namespace) -> Path | None:
    root = args.engine_root or Path(os.environ.get(
        "LAST30DAYS_ENGINE_ROOT", str(SKILL_ROOT / "vendor" / "last30days")))
    root = root.expanduser().resolve()
    choices = [root] if root.is_file() else [
        root / "scripts" / "last30days.py",
        root / "skills" / "last30days" / "scripts" / "last30days.py",
        root / "last30days.py",
    ]
    return next((x for x in choices if x.is_file()), None)


def engine_check(entry: Path | None) -> dict:
    if entry is None:
        return {"state": "not-deployed", "runtime_checked": False}
    content = entry.read_text(encoding="utf-8")
    missing = [flag for flag in REQUIRED_FLAGS if flag not in content]
    complete = (entry.parent / "lib" / "schema.py").is_file()
    return {"state": "entrypoint-found" if complete and not missing else "incompatible-or-incomplete",
            "entrypoint": str(entry), "missing_flags": missing,
            "script_tree_present": complete, "runtime_checked": False}


def child_env(config_dir: Path, use_env: bool) -> dict[str, str]:
    inherited = {k: v for k, v in os.environ.items() if k.upper() in OS_KEYS}
    for key in CREDENTIAL_KEYS:
        inherited[key] = os.environ.get(key, "") if use_env else ""
    if use_env:
        # Retain deliberate provider/backend endpoints, never general engine config.
        for key in ("LAST30DAYS_REASONING_PROVIDER", "LAST30DAYS_X_BACKEND",
                    "OPENAI_BASE_URL", "XAI_BASE_URL", "OPENROUTER_BASE_URL"):
            if key in os.environ:
                inherited[key] = os.environ[key]
    else:
        # The engine exposes local as a runtime outcome, not a valid provider pin.
        # With auto and all credentials empty it resolves to deterministic local.
        inherited["LAST30DAYS_REASONING_PROVIDER"] = "auto"
        inherited["EXCLUDE_SOURCES"] = (
            "x,tiktok,instagram,linkedin,perplexity,trustpilot,amazon,meta_ads,"
            "xiaohongshu,threads,pinterest,truthsocial,bluesky,telegram"
        )
    inherited.update({
        "LAST30DAYS_CONFIG_DIR": str(config_dir), "LAST30DAYS_MEMORY_DIR": "",
        "LAST30DAYS_SKIP_KEYCHAIN": "1", "LAST30DAYS_TRUST_PROJECT_CONFIG": "0",
        "LAST30DAYS_STORE": "0", "LAST30DAYS_LIBRARY_CONTEXT": "off",
        "LAST30DAYS_TRUSTPILOT_NO_BROWSER": "1", "AGENTCOOKIE": "off",
        "LAST30DAYS_X_HOST_LANE": "off", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
    })
    return inherited


def command(args: argparse.Namespace, entry: Path, save_dir: Path) -> list[str]:
    result = [args.python, str(entry), args.topic, "--days", str(args.days),
              "--as-of", args.as_of.isoformat(), "--search", ",".join(csv(args.search)),
              "--emit", "json", "--json-profile", "raw", "--no-browser-cookies",
              "--no-verify-freshness", "--save-dir", str(save_dir),
              "--deep" if args.deep else "--quick"]
    if not args.use_env:
        result += ["--web-backend", "keyless"]
    for name in ("subreddits", "dedicated_subreddits", "x_handle", "github_repo"):
        if getattr(args, name):
            result += ["--" + name.replace("_", "-"), getattr(args, name)]
    if args.mock:
        result.append("--mock")
    return result


def base_result(args: argparse.Namespace, state: str) -> dict:
    start = args.as_of - timedelta(days=args.days - 1)
    return {"schema_version": "product-weekly-leads/1", "collection_state": state,
            "query": {"topic": args.topic, "days": args.days,
                      "range_from": start.isoformat(), "range_to": args.as_of.isoformat(),
                      "timezone": "Asia/Shanghai", "requested_sources": csv(args.search),
                      "include_terms": args.include_term, "exclude_terms": args.exclude_term},
            "source_status": {}, "leads": [], "excluded": [], "warnings": [],
            "fallback": {"method": "native-web-search-and-original-pages",
                         "needed": state in {"unavailable", "failed"},
                         "note": "Use the existing competitor pool, source seeds and actual comment pages."}}


def published_date(value: object) -> date | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or str(value).replace(".", "", 1).isdigit():
            return datetime.fromtimestamp(float(value), timezone.utc).astimezone(SHANGHAI).date()
        text = str(value)
        if len(text) == 10:
            return date.fromisoformat(text)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        # Do not invent a timezone for a naive timestamp.
        return parsed.astimezone(SHANGHAI).date() if parsed.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def normalize(report: dict, args: argparse.Namespace, state: str) -> dict:
    if not isinstance(report, dict) or not isinstance(report.get("items_by_source"), dict):
        raise ValueError("Expected a single raw Report with items_by_source; use --emit json --json-profile raw")
    result = base_result(args, state)
    result["engine_report"] = {k: report.get(k) for k in
                               ("topic", "range_from", "range_to", "generated_at")}
    result["warnings"] = list(report.get("warnings") or [])
    if report.get("topic") != args.topic:
        result["warnings"].append("Imported engine topic differs from requested topic; confirm entity scope.")
    result["source_status"] = dict(report.get("source_status") or {})
    result["errors_by_source"] = dict(report.get("errors_by_source") or {})
    for source in csv(args.search):
        if source not in result["source_status"]:
            result["source_status"][source] = {
                "state": "not-reported", "attempted": None,
                "detail": result["errors_by_source"].get(source),
            }
    start = date.fromisoformat(result["query"]["range_from"])
    seen: set[tuple[str, str]] = set()
    for source, items in report["items_by_source"].items():
        if not isinstance(items, list):
            raise ValueError(f"items_by_source.{source} must be a list")
        for position, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"items_by_source.{source}[{position}] must be an object")
            native_id = str(item.get("item_id") or "")
            url = item.get("url")
            fingerprint = hashlib.sha256(json.dumps(item, sort_keys=True,
                                                     ensure_ascii=False).encode()).hexdigest()
            key = (source, native_id or fingerprint)
            if key in seen:
                continue
            seen.add(key)
            pub = published_date(item.get("published_at"))
            window = "unknown" if pub is None else "in-window" if start <= pub <= args.as_of else "outside-window"
            text = " ".join(str(item.get(k) or "") for k in ("title", "body", "snippet")).casefold()
            why = []
            if args.include_term and not any(t.casefold() in text for t in args.include_term):
                why.append("no-include-term")
            if any(t.casefold() in text for t in args.exclude_term):
                why.append("exclude-term")
            if window == "outside-window":
                why.append("outside-editorial-window")
            lead = {
                "lead_id": "L30-" + hashlib.sha256("|".join(key).encode()).hexdigest()[:12],
                "source": source, "source_item_id": native_id or None,
                "title": item.get("title"), "url": url,
                "author": item.get("author"), "container": item.get("container"),
                "published_at": item.get("published_at"), "date_confidence": item.get("date_confidence"),
                "window_status": window, "retrieved_at": report.get("generated_at"),
                "engine_locator": f"items_by_source.{source}[{position}]",
                "verification_status": "mock-fixture" if state == "mock" else "lead-only",
                "citation_ready": False, "raw_item": item,
            }
            if why:
                lead["exclusion_reasons"] = why
                result["excluded"].append(lead)
            else:
                result["leads"].append(lead)
    bad = [s for s, outcome in result["source_status"].items()
           if not isinstance(outcome, dict) or outcome.get("state") != "ok"]
    result["fallback"]["needed"] = bool(bad) or not result["leads"]
    result["fallback"]["sources"] = bad
    if state == "succeeded" and bad:
        result["collection_state"] = "partial"
    return result


def self_test() -> dict:
    args = parser().parse_args(["Device A", "--as-of", "2026-10-08", "--include-term", "device a"])
    item = {"item_id": "r1", "title": "Device A owner report", "url": "https://example.invalid/1",
            "body": "Source text, not a verified quote", "published_at": "2026-10-02"}
    raw = {"topic": "Device A", "items_by_source": {"reddit": [item, item,
           {**item, "item_id": "r2", "published_at": "2026-10-01"},
           {**item, "item_id": "r3", "published_at": None}]},
           "source_status": {"reddit": {"state": "ok", "items_returned": 4, "attempted": True},
                             "grounding": {"state": "auth-failed", "attempted": True}}}
    result = normalize(raw, args, "succeeded")
    assert len(result["leads"]) == 2 and len(result["excluded"]) == 1
    assert result["collection_state"] == "partial" and result["fallback"]["needed"]
    assert result["leads"][1]["window_status"] == "unknown"
    assert all(not x["citation_ready"] for x in result["leads"])
    assert published_date("2026-10-01T17:00:00Z") == date(2026, 10, 2)
    assert published_date("2026-10-01T17:00:00") is None
    try:
        normalize({"candidates": []}, args, "imported")
    except ValueError:
        pass
    else:
        raise AssertionError("Agent profile must not be silently accepted as raw")
    isolated = child_env(Path("unwritten-check-directory"), False)
    assert all(isolated[k] == "" for k in CREDENTIAL_KEYS)
    assert isolated["LAST30DAYS_TRUST_PROJECT_CONFIG"] == "0"
    return {"state": "passed", "checks": ["raw-schema", "date-boundary", "unknown-dates",
            "timezone", "deduplication", "source-failure", "quote-not-ready", "credential-isolation"]}


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        result, code = self_test(), 0
    else:
        if args.days < 1 or args.timeout < 1 or not csv(args.search):
            parser().error("days/timeout must be positive and search must contain a channel")
        if not args.topic and not args.check:
            parser().error("topic is required except with --check or --self-test")
        topic_key = " ".join((args.topic or "").split()).casefold()
        if topic_key in {"setup", "doctor", "library feed", "library search", "queue list", "queue cover"} or topic_key.startswith(("library search ", "queue cover ")):
            parser().error("Use a research topic, not an engine setup/library/queue command")
        if args.mock and not args.run:
            parser().error("--mock requires --run")
        entry = find_engine(args)
        checked = engine_check(entry)
        code = 0
        try:
            if args.input_json:
                result = normalize(json.loads(args.input_json.read_text(encoding="utf-8-sig")), args, "imported")
            elif args.check:
                result = checked
            elif checked["state"] != "entrypoint-found":
                result = base_result(args, "unavailable")
                result["engine"] = checked
                code = 2 if args.run else 0
            elif not args.run:
                result = base_result(args, "planned")
                result["engine"] = checked
                result["command"] = command(args, entry, Path("<temporary-run-directory>"))
                result["credential_mode"] = "existing-process-env" if args.use_env else "keyless-local"
            else:
                with tempfile.TemporaryDirectory(prefix="product-weekly-last30days-") as tmp:
                    run_dir = Path(tmp)
                    environment = child_env(run_dir, args.use_env)
                    help_run = subprocess.run([args.python, str(entry), "--help"],
                        cwd=run_dir, env=environment, text=True, encoding="utf-8", errors="replace",
                        capture_output=True, timeout=min(args.timeout, 30))
                    if help_run.returncode or any(x not in help_run.stdout for x in REQUIRED_FLAGS):
                        raise ValueError("Engine --help failed: check Python 3.12+, dependency tree and CLI version")
                    run = subprocess.run(command(args, entry, run_dir), cwd=run_dir,
                        env=environment, text=True, encoding="utf-8", errors="replace",
                        capture_output=True, timeout=args.timeout)
                    if run.returncode and not run.stdout.strip():
                        raise ValueError(f"Engine exited {run.returncode} without a JSON report")
                    result = normalize(json.loads(run.stdout), args, "mock" if args.mock else "succeeded")
                    result["engine_exit_code"] = run.returncode
                    result["engine"] = {**checked, "runtime_checked": True}
                    result["credential_mode"] = "existing-process-env" if args.use_env else "keyless-local"
                    if run.returncode:
                        result["collection_state"] = "partial"
                        result["fallback"]["needed"] = True
                        code = 2
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result = base_result(args, "failed")
            # Do not echo provider stderr or credentials into a weekly artifact.
            result["error"] = "engine-timeout" if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
            code = 2
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
