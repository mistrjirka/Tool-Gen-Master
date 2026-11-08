"""CLI for the standalone tool_gen current-generation pipeline."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from tool_gen.client import DEFAULT_MODEL, BudgetedClient, ClientError
from tool_gen.store import (
    AbortError,
    InputFile,
    StageContext,
    StageError,
    collect_reader_files,
    collect_stage_files,
    ensure_unique_ids,
    hash_file,
    read_jsonl_strict,
    strict_dumps,
    validate_shard_args,
)


def _input_files(paths: list[Path]) -> list[InputFile]:
    return [InputFile(path=str(p), sha256=hash_file(p)) for p in paths]


def _cap(value: str) -> str | None:
    return None if value == "none" else value


def _shard_dir(root: Path, shard: int) -> Path:
    return root / f"shard-{shard}"


def _add_stage_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--model", default=None)
    p.add_argument(
        "--max-usd",
        default="1.00",
        help="budget cap; pass 'none' for the authorized uncapped full build",
    )


def _client_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {"max_usd": _cap(args.max_usd), "model": args.model or DEFAULT_MODEL}


def cmd_goals(args: argparse.Namespace) -> int:
    from tool_gen.goals import gen_goals
    from tool_gen.models import GoalRecord

    goals = gen_goals(args.num, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for goal in goals:
            GoalRecord.model_validate(goal)
            fh.write(strict_dumps(goal) + "\n")
    print(f"wrote {len(goals)} goals (seed {args.seed}) -> {out}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from tool_gen.validate import audit_goals

    goals = read_jsonl_strict(Path(args.input))
    report = audit_goals(goals)
    problems = report["problems"]
    if not isinstance(problems, list):
        raise StageError("internal: audit report must carry a problem list")
    families = report["families"]
    tools = report["tools"]
    if not isinstance(families, list) or not isinstance(tools, list):
        raise StageError("internal: audit report must carry family/tool lists")
    print(
        f"goals={report['goals']} families={len(families)} tools={len(tools)} bad_goals={report['bad_goals']}"
    )
    for problem in problems[:50]:
        print(f"  - {problem}")
    if len(problems) > 50:
        print(f"  ... and {len(problems) - 50} more")
    if args.output:
        Path(args.output).write_text(strict_dumps(report) + "\n", encoding="utf-8")
    return 1 if report["bad_goals"] else 0


def cmd_writer(args: argparse.Namespace) -> int:
    from tool_gen.writer import run_writer

    validate_shard_args(args.shard, args.shards)
    goals_path = Path(args.goals)
    raw_goals = read_jsonl_strict(goals_path)
    if args.limit:
        raw_goals = raw_goals[: args.limit]
    ids: list[str] = []
    for raw in raw_goals:
        goal_id = raw.get("id")
        if not isinstance(goal_id, str):
            raise StageError("writer input rows need a string goal 'id'")
        ids.append(goal_id)
    ensure_unique_ids(ids, "writer goals input")
    shard_dir = _shard_dir(Path(args.out), args.shard)
    kwargs = _client_kwargs(args)
    max_usd = kwargs["max_usd"]
    model = kwargs["model"]
    if not isinstance(model, str):
        raise StageError("internal: model must resolve to a string")
    if max_usd is not None and not isinstance(max_usd, str):
        raise StageError("internal: max_usd must resolve to a string or None")
    from tool_gen.prompts import load_prompt, writer_prompt

    system = writer_prompt()
    prompt_provenance = system + "\n\n" + load_prompt("writer", "brief_template")
    ctx = StageContext(
        stage="writer",
        shard_dir=shard_dir,
        shard=args.shard,
        shards=args.shards,
        prompt_text=prompt_provenance,
        config={
            "temperature": str(args.temperature),
            "model": model,
            "max_usd": max_usd if max_usd is not None else "none",
            "limit": str(args.limit),
            "input_format": "readable-v1",
        },
        inputs=_input_files([goals_path]),
    )
    with BudgetedClient(str(shard_dir), max_usd=max_usd, model=model) as client:
        try:
            stats = run_writer(
                raw_goals, ctx, client.complete, temperature=args.temperature
            )
        except AbortError as exc:
            print(f"writer aborted after {exc.processed} goals: {exc}", file=sys.stderr)
            print(strict_dumps({"accounting": client.accounting()}))
            return 2
        summary: dict[str, object] = dict(client.accounting())
        summary.update(stats)
        print(strict_dumps(summary))
    return 0


def _collect_writer_entries(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for found in collect_stage_files(path, "results.jsonl"):
        for row in read_jsonl_strict(found):
            if row.get("decision", "accept") != "accept":
                continue
            if not isinstance(row.get("goal"), dict) or not row.get("request"):
                continue
            entries.append({"goal": row["goal"], "request": row["request"]})
    if not entries:
        raise StageError(f"{path} yielded no accepted writer rows with requests")
    ids: list[str] = []
    for entry in entries:
        goal = entry["goal"]
        if not isinstance(goal, dict) or not isinstance(goal.get("id"), str):
            raise StageError("writer rows need a goal object with a string 'id'")
        ids.append(goal["id"])
    ensure_unique_ids(ids, "combined writer input")
    return entries


def cmd_reader(args: argparse.Namespace) -> int:
    from tool_gen.reader import run_reader

    validate_shard_args(args.shard, args.shards)
    input_path = Path(args.input)
    files = collect_stage_files(input_path, "results.jsonl")
    entries = _collect_writer_entries(input_path)
    if args.max_attempts < 1:
        raise StageError("--max-attempts must be at least 1")
    replay_files: list[Path] = []
    if args.replay_from:
        from tool_gen.triage import replay_ids

        replay_path = Path(args.replay_from)
        source_root = replay_path if replay_path.is_dir() else replay_path.parent
        source_root = source_root.resolve()
        output_root = Path(args.out).resolve()
        if output_root.is_relative_to(source_root) or source_root.is_relative_to(
            output_root
        ):
            raise StageError(
                "reader replay needs a fresh output root outside its source results"
            )
        replay_files = collect_reader_files(replay_path)
        previous = [row for path in replay_files for row in read_jsonl_strict(path)]
        selected_ids = replay_ids(previous)
        entries = [
            entry
            for entry in entries
            if isinstance(entry["goal"], dict)
            and entry["goal"].get("id") in selected_ids
        ]
        if not entries:
            raise StageError("no unresolved source IDs matched --replay-from results")
    shard_dir = _shard_dir(Path(args.out), args.shard)
    kwargs = _client_kwargs(args)
    max_usd = kwargs["max_usd"]
    model = kwargs["model"]
    if not isinstance(model, str):
        raise StageError("internal: model must resolve to a string")
    if max_usd is not None and not isinstance(max_usd, str):
        raise StageError("internal: max_usd must resolve to a string or None")
    from tool_gen.prompts import reader_prompt

    system = reader_prompt()
    ctx = StageContext(
        stage="reader",
        shard_dir=shard_dir,
        shard=args.shard,
        shards=args.shards,
        prompt_text=system,
        config={
            "temperature": str(args.temperature),
            "model": model,
            "max_usd": max_usd if max_usd is not None else "none",
            "max_attempts": str(args.max_attempts),
            "comparison": "schema-instants-v1",
            "reader_contract": "argument-slots-v1",
        },
        inputs=_input_files(files + replay_files),
    )
    with BudgetedClient(str(shard_dir), max_usd=max_usd, model=model) as client:
        try:
            stats = run_reader(
                entries,
                ctx,
                client.complete,
                temperature=args.temperature,
                max_attempts=args.max_attempts,
            )
        except AbortError as exc:
            print(
                f"reader aborted after {exc.processed} entries: {exc}", file=sys.stderr
            )
            print(strict_dumps({"accounting": client.accounting()}))
            return 2
        summary = dict(client.accounting())
        summary.update(stats)
        print(strict_dumps(summary))
    return 0


def cmd_paraphrase(args: argparse.Namespace) -> int:
    from tool_gen.paraphrase import run_paraphrase

    validate_shard_args(args.shard, args.shards)
    input_path = Path(args.writer)
    files = collect_stage_files(input_path, "results.jsonl")
    accepted: list[dict[str, object]] = []
    for found in files:
        accepted += [
            e for e in read_jsonl_strict(found) if e.get("decision") == "accept"
        ]
    if not accepted:
        raise StageError(f"{input_path} yielded no accepted writer rows")
    ids: list[str] = []
    for entry in accepted:
        goal = entry.get("goal")
        if not isinstance(goal, dict) or not isinstance(goal.get("id"), str):
            raise StageError("writer rows need a goal object with a string 'id'")
        ids.append(goal["id"])
    ensure_unique_ids(ids, "combined writer input")
    shard_dir = _shard_dir(Path(args.out), args.shard)
    kwargs = _client_kwargs(args)
    max_usd = kwargs["max_usd"]
    model = kwargs["model"]
    if not isinstance(model, str):
        raise StageError("internal: model must resolve to a string")
    if max_usd is not None and not isinstance(max_usd, str):
        raise StageError("internal: max_usd must resolve to a string or None")
    from tool_gen.prompts import load_prompt

    system = load_prompt("paraphraser", "base")
    ctx = StageContext(
        stage="paraphrase",
        shard_dir=shard_dir,
        shard=args.shard,
        shards=args.shards,
        prompt_text=system,
        config={
            "model": model,
            "max_usd": max_usd if max_usd is not None else "none",
            "input_format": "readable-v1",
        },
        inputs=_input_files(files),
    )
    with BudgetedClient(str(shard_dir), max_usd=max_usd, model=model) as client:
        try:
            stats = run_paraphrase(accepted, ctx, client.complete)
        except AbortError as exc:
            print(
                f"paraphrase aborted after {exc.processed} entries: {exc}",
                file=sys.stderr,
            )
            print(strict_dumps({"accounting": client.accounting()}))
            return 2
        summary = dict(client.accounting())
        summary.update(stats)
        print(strict_dumps(summary))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from tool_gen.export import (
        export_paraphrases,
        export_writer_results,
        load_verified_proofs,
    )

    verification: dict[str, str] | None = None
    if args.verification:
        proofs, _accepted_rows, without_proof = load_verified_proofs(
            Path(args.verification)
        )
        if not proofs:
            if without_proof:
                raise StageError(
                    f"{args.verification} holds {without_proof} accepted verdicts "
                    "without content fingerprints (old provenance); refusing to "
                    "certify stale ids as verified"
                )
            raise StageError(f"{args.verification} yielded no accepted reader verdicts")
        verification = proofs
    if args.paraphrases:
        stats = export_paraphrases(
            Path(args.paraphrases), Path(args.output), verification
        )
    else:
        if not args.input:
            raise StageError("export needs --input or --paraphrases")
        stats = export_writer_results(Path(args.input), Path(args.output), verification)
    print(strict_dumps(stats))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from tool_gen.analysis import analyze_paths

    report = analyze_paths([Path(p) for p in args.input])
    text = strict_dumps(report) + "\n"
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    from tool_gen.triage import triage_entries, triage_summary

    entries = _collect_writer_entries(Path(args.input))
    results = [
        row
        for path in collect_reader_files(Path(args.results))
        for row in read_jsonl_strict(path)
    ]
    reports = triage_entries(entries, results)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "".join(strict_dumps(row) + "\n" for row in reports), encoding="utf-8"
        )
    else:
        for row in reports:
            print(strict_dumps(row))
    categories = Counter(str(row.get("category", "unknown")) for row in reports)
    print(
        strict_dumps(
            {
                "mode": "offline-triage",
                "source_rows": len(entries),
                "reader_rows": len(results),
                "coverage": triage_summary(reports),
                "categories": dict(categories),
                "fresh_model_requests": 0,
            }
        ),
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tool-gen", description="Standalone current-generation pipeline"
    )
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("goals", help="generate seeded goals")
    g.add_argument("-n", "--num", type=int, default=30)
    g.add_argument("--seed", type=int, default=21)
    g.add_argument("-o", "--output", default="goals.jsonl")
    g.set_defaults(func=cmd_goals)

    a = sub.add_parser(
        "audit", help="mechanical goal audit (unknown tools, bad args, forward refs)"
    )
    a.add_argument("--input", required=True)
    a.add_argument("--output", default=None)
    a.set_defaults(func=cmd_audit)

    w = sub.add_parser("writer", help="write natural requests for goals")
    w.add_argument("--goals", required=True, help="goals JSONL file")
    w.add_argument(
        "--out", required=True, help="stage root; this shard uses <root>/shard-N"
    )
    w.add_argument("--limit", type=int, default=0)
    w.add_argument("--temperature", type=float, default=0.9)
    _add_stage_args(w)
    w.set_defaults(func=cmd_writer)

    r = sub.add_parser("reader", help="blind-verify writer requests")
    r.add_argument(
        "--input",
        required=True,
        help="writer results.jsonl file or stage root holding shard results",
    )
    r.add_argument(
        "--out", required=True, help="stage root; this shard uses <root>/shard-N"
    )
    r.add_argument("--temperature", type=float, default=0.0)
    r.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="bounded blind reader attempts per valid goal (default: 2)",
    )
    r.add_argument(
        "--replay-from",
        default=None,
        help="prior reader result file/root; retry only unresolved IDs in a fresh output root",
    )
    _add_stage_args(r)
    r.set_defaults(func=cmd_reader)

    pp = sub.add_parser("paraphrase", help="paraphrase accepted requests x3 registers")
    pp.add_argument(
        "--writer",
        required=True,
        help="writer results.jsonl file or stage root holding shard results",
    )
    pp.add_argument(
        "--out", required=True, help="stage root; this shard uses <root>/shard-N"
    )
    _add_stage_args(pp)
    pp.set_defaults(func=cmd_paraphrase)

    e = sub.add_parser("export", help="export accepted rows to SFT JSONL")
    e.add_argument(
        "--input", default=None, help="writer results.jsonl file or stage root"
    )
    e.add_argument(
        "--paraphrases", default=None, help="paraphrases.jsonl file or stage root"
    )
    e.add_argument(
        "--verification",
        default=None,
        help="reader results file or stage root; only reader-accepted goals are kept",
    )
    e.add_argument("--output", required=True)
    e.set_defaults(func=cmd_export)

    an = sub.add_parser("analyze", help="pattern/bias report over JSONL files")
    an.add_argument("--input", nargs="+", required=True)
    an.add_argument("--output", default=None)
    an.set_defaults(func=cmd_analyze)

    tr = sub.add_parser(
        "triage",
        help="offline analysis of reader matches, differences and unresolved errors",
    )
    tr.add_argument("--input", required=True, help="writer result file/root")
    tr.add_argument("--results", required=True, help="reader result file/root")
    tr.add_argument(
        "--output",
        default=None,
        help="JSONL assessment, not a fresh verification proof",
    )
    tr.set_defaults(func=cmd_triage)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (StageError, ClientError) as exc:
        print(f"tool-gen: {exc}", file=sys.stderr)
        return 2
    except (ValueError, TypeError, OSError) as exc:
        # Bad inputs (malformed JSONL, wrong shapes, unreadable paths,
        # rejected directories) are user-facing errors, not tracebacks.
        print(f"tool-gen: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
