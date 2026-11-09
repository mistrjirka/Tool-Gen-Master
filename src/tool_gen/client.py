"""Budget-guarded OpenRouter JSON-schema client for standalone `tool_gen`.

One narrow job: send a request, get a locally validated JSON object back, and keep
spending inside the approved budget. The default cap is $1; the separately
authorized full-generation build selects `max_usd=None` and is bounded only by the
credit available on the existing OpenRouter account. Money is reserved from the
ledger BEFORE every HTTP call and only settled afterwards, so an unknown charge is
always retained at its worst-case estimate in both modes. Single process, sequential
requests; the run folder is flock-locked so a second driver cannot share the same
ledger. A ledger never changes mode on resume: capped and uncapped records refuse
each other, and an uncapped ledger is only written into an empty run folder.

The API key comes from the `OPENROUTER_API_KEY` environment variable only, read
lazily on each fresh (non-cached) request; this module never stores, echoes, logs,
or writes the key, and never reads shell startup files.
"""

import fcntl
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

import jsonschema
from typing_extensions import Self

API_URL = "https://openrouter.ai/api/v1/chat/completions"
SCHEMA_NAME = "tool_composition"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
MAX_TOKENS_CAP = 4096
# Explicit low-reasoning probes need room for reasoning plus visible JSON.
# Normal/default requests keep the original ceiling; spend is still reserved.
REASONING_MAX_TOKENS_CAP = 8192
# provider.max_price values are USD per MILLION tokens. These are the enforced
# ceilings, deliberately above the current live rates (prompt $0.045, completion
# $0.50): a returned `request` fee of 0 bounds any per-request surcharge.
PROMPT_USD_PER_MILLION = Decimal("0.30")
COMPLETION_USD_PER_MILLION = Decimal("1.20")
REQUEST_FEE_CEILING = Decimal(0)
PILOT_CAP_USD = Decimal("1.00")
# One token is never cheaper than one UTF-8 byte, so byte length bounds prompt
# tokens. The extra allowance covers chat framing plus server-side tool schema.
PROMPT_TOKEN_SLACK = 4096
MICRO_USD = Decimal("0.000001")
TIMEOUT_SECONDS = 180  # a timeout halts rather than retries
LEDGER_NAME = "budget.json"
LOCK_NAME = "budget.lock"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")
_ERROR_CODES = {
    401: "key rejected",
    402: "insufficient OpenRouter credits",
    403: "access denied",
    404: "model or route not found",
    408: "provider timeout",
    429: "rate limited",
    500: "provider internal error",
    502: "bad gateway",
    503: "no capacity",
    504: "gateway timeout",
}


class ClientError(RuntimeError):
    """A request was refused, failed, or produced unusable output."""


class BudgetError(ClientError):
    """The approved cap or the provider's remaining credit prevents spending."""


class OutputError(ClientError):
    """A completed, accounted model response cannot supply a usable label.

    Callers may quarantine this item without treating transport/auth failures as
    content mistakes. The failed request itself is never silently re-sent.
    """


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ClientError("model output repeats a JSON key")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise ClientError(f"model output used non-standard JSON literal {name}")


def _load_json(text: str) -> object:
    try:
        return json.loads(
            text, object_pairs_hook=_strict_object, parse_constant=_reject_constant
        )
    except ClientError:
        raise
    except json.JSONDecodeError as exc:
        raise ClientError(f"malformed JSON: {exc.msg} at offset {exc.pos}") from None


def _dump_json(value: object, *, sort_keys: bool = True) -> str:
    try:
        # Canonicalize persisted data and payloads by default. HTTP request
        # schemas keep declaration order so decisions/name precede call arguments.
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=sort_keys,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (ValueError, TypeError) as exc:
        raise ClientError(f"value is not strict JSON: {exc}") from None


def _redact(text: object, limit: int = 200) -> str:
    """Keep a bounded single-line hint; headers, bodies and keys are never logged."""
    hint = " ".join(str(text).split())[:limit]
    return hint if len(str(text)) <= limit else hint + "…"


def _money(value: object, label: str) -> Decimal:
    if type(value) is not str:
        raise ClientError(f"{label} must be stored as a decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ClientError(f"{label} is not a decimal amount") from None
    if not amount.is_finite() or amount < 0:
        raise ClientError(f"{label} must be a finite nonnegative amount")
    return amount


def _optional_money(value: object, label: str) -> Decimal | None:
    """A cap, or None for the authorized uncapped mode. Only a JSON `null` that is
    actually present in the ledger means uncapped; a missing or corrupt field is an
    error and is never read as permission to spend without a limit."""
    if value is None:
        return None
    return _money(value, label)


def _quantize(amount: Decimal, rounding: str = ROUND_UP) -> Decimal:
    return amount.quantize(MICRO_USD, rounding=rounding)


PINNED_PRICES = {
    "prompt": str(PROMPT_USD_PER_MILLION),
    "completion": str(COMPLETION_USD_PER_MILLION),
    "request": str(REQUEST_FEE_CEILING),
}


def worst_case_usd(prompt_bytes: int, max_tokens: int = MAX_TOKENS_CAP) -> Decimal:
    """Conservative ceiling for one call: worst-case prompt and completion prices.
    Exposed so a driver can size its own plan offline before spending anything."""
    prompt_tokens = prompt_bytes + PROMPT_TOKEN_SLACK + max_tokens
    prompt = Decimal(prompt_tokens) * PROMPT_USD_PER_MILLION / Decimal(1_000_000)
    completion = Decimal(max_tokens) * COMPLETION_USD_PER_MILLION / Decimal(1_000_000)
    return _quantize(prompt + completion + REQUEST_FEE_CEILING)


def _schema_problem(schema: object) -> str:
    """Cheap pre-send refusals only. Free-form sub-objects are left to the provider:
    if strict mode rejects them we get a bounded HTTP error, never a silent drop to
    json_object mode, and locally we still validate the returned object anyway."""
    if not isinstance(schema, dict):
        return "schema must be a JSON object"
    if schema.get("type") != "object":
        return "the tool_gen output contract requires a top-level object schema"
    return ""


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Publish complete evidence atomically, fsyncing both the file and directory."""
    text = _dump_json(payload) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ClientError(f"cannot persist {path.name}: {_redact(detail)}") from None
    finally:
        if temporary is not None:
            # Best-effort temporary-file cleanup must not mask a persistence error.
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def _read_strict_json(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    parsed = _load_json(text)
    if not isinstance(parsed, dict):
        raise ClientError(f"{path.name} must contain a JSON object")
    return parsed


def _described_cap(cap: Decimal | None) -> str:
    return "uncapped (account credit)" if cap is None else f"{cap} USD"


@dataclass
class _Ledger:
    """The only spend record: loaded from disk, pinned to the config it was made with.

    `max_usd` is None only in the explicitly authorized uncapped mode.
    """

    model: str
    max_usd: Decimal | None
    reported: Decimal
    retained: Decimal
    fresh_requests: int
    cache_hits: int
    stopped: bool
    stop_reason: str
    reservations: dict[str, dict[str, str]]

    def spent(self) -> Decimal:
        return self.reported + self.retained

    def pending(self) -> Decimal:
        return sum(
            (_entry_charge(entry) for entry in self.reservations.values()), Decimal(0)
        )

    def to_json(self) -> dict[str, object]:
        return {
            "version": 1,
            "model": self.model,
            "max_usd": None if self.max_usd is None else str(self.max_usd),
            "reported_usd": str(_quantize(self.reported)),
            "retained_usd": str(_quantize(self.retained)),
            "fresh_requests": self.fresh_requests,
            "cache_hits": self.cache_hits,
            "stopped": self.stopped,
            "stop_reason": self.stop_reason,
            "reservations": self.reservations,
            "pinned_prices_usd_per_million": dict(PINNED_PRICES),
        }

    @staticmethod
    def from_json(raw: dict[str, object]) -> "_Ledger":
        reservations: dict[str, dict[str, str]] = {}
        stored = raw.get("reservations")
        if isinstance(stored, dict):
            for request_id, entry in stored.items():
                if isinstance(entry, dict):
                    reservations[request_id] = {
                        str(key): str(value) for key, value in entry.items()
                    }
        stopped = raw.get("stopped")
        reason = raw.get("stop_reason")
        fresh, hits = raw.get("fresh_requests"), raw.get("cache_hits")
        if type(fresh) is not int or type(hits) is not int or fresh < 0 or hits < 0:
            raise ClientError("budget ledger has invalid request counts")
        if "max_usd" not in raw:
            raise ClientError(
                "budget ledger has no max_usd field; a missing cap is "
                "never interpreted as uncapped spending"
            )
        return _Ledger(
            model=str(raw.get("model", "")),
            max_usd=_optional_money(raw["max_usd"], "ledger max_usd"),
            reported=_money(raw.get("reported_usd"), "ledger reported_usd"),
            retained=_money(raw.get("retained_usd"), "ledger retained_usd"),
            fresh_requests=fresh,
            cache_hits=hits,
            stopped=stopped is True,
            stop_reason="" if not isinstance(reason, str) else reason,
            reservations=reservations,
        )


def _entry_charge(entry: dict[str, str]) -> Decimal:
    return _money(entry.get("reserved_usd"), "reservation amount")


class BudgetedClient:
    """Sequential budgeted calls; every charge is reserved before it is attempted."""

    def __init__(
        self,
        folder: str | Path,
        max_usd: str | None = "1.00",
        model: str = DEFAULT_MODEL,
    ) -> None:
        """Capped mode by default. `max_usd=None` is the separately authorized
        uncapped mode for a NEW full-generation ledger: the only remaining bound is
        the credit already on the OpenRouter account, enforced by the service itself.
        Passing no argument never means uncapped, and an existing capped ledger is
        never refilled, reset or reinterpreted as uncapped.
        """
        if not MODEL_PATTERN.fullmatch(model):
            raise ClientError("model identifier is malformed")
        if max_usd is None:
            cap: Decimal | None = None
        else:
            cap = _money(max_usd, "max_usd")
            if cap <= 0 or cap > PILOT_CAP_USD:
                raise ClientError(
                    "this client requires max_usd greater than 0 and at most 1.00; "
                    "pass max_usd=None explicitly for the authorized full build"
                )
        self.folder = Path(folder)
        self.model = model
        self._cap = cap
        self._ledger_path = self.folder / LEDGER_NAME
        self._requests_dir = self.folder / "requests"
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            self._requests_dir.mkdir(exist_ok=True)
        except OSError as exc:
            raise ClientError(
                f"cannot prepare run folder: {_redact(exc.strerror or exc)}"
            ) from None
        self._resources = ExitStack()
        self._closed = False
        try:
            self._lock_handle = self._resources.enter_context(
                (self.folder / LOCK_NAME).open("a+")
            )
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._resources.callback(
                fcntl.flock, self._lock_handle.fileno(), fcntl.LOCK_UN
            )
            self._ledger = self._load_ledger()
        except OSError as exc:
            self._resources.close()
            raise ClientError(
                "run folder cannot be locked (it may be held by another process)"
            ) from exc
        except ClientError:
            self._resources.close()
            raise

    def close(self) -> None:
        self._resources.close()
        self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _load_ledger(self) -> _Ledger:
        if not self._ledger_path.exists():
            if self._prior_attempts():
                raise ClientError(
                    "run folder already holds recorded attempts but no budget "
                    "ledger; the budget is never restarted or refilled around them"
                )
            return _Ledger(
                self.model, self._cap, Decimal(0), Decimal(0), 0, 0, False, "", {}
            )
        raw = _read_strict_json(self._ledger_path)
        ledger = _Ledger.from_json(raw)
        if ledger.model != self.model:
            raise ClientError(
                f"ledger is pinned to model {ledger.model}, not {self.model}"
            )
        if ledger.max_usd != self._cap:
            raise ClientError(
                "ledger is pinned to "
                f"{_described_cap(ledger.max_usd)} but this run asks for "
                f"{_described_cap(self._cap)}; a resume never refills or "
                "changes the approved budget mode"
            )
        if ledger.max_usd is not None and ledger.spent() > ledger.max_usd:
            raise ClientError(
                "ledger already records more than its cap; investigate before resuming"
            )
        if raw.get("pinned_prices_usd_per_million") != PINNED_PRICES:
            raise ClientError(
                "ledger was written under different provider price ceilings; "
                "refusing to mix budgets"
            )
        return ledger

    def _prior_attempts(self) -> bool:
        """Any recorded request evidence in this folder, however small."""
        try:
            return any(self._requests_dir.glob("*.json"))
        except OSError:
            return True

    # ---------------------------------------------------------------- accounting

    def accounting(self) -> dict[str, object]:
        """Safe totals: what OpenRouter reported plus pessimistically retained cost.
        Uncapped mode reports its status honestly instead of inventing an infinity."""
        ledger = self._ledger
        pending = ledger.pending()
        spent = ledger.spent()
        total = _quantize(spent + pending)
        cap = ledger.max_usd
        if cap is None:
            available: Decimal | None = None
            over_cap = False
        else:
            available = _quantize(max(Decimal(0), cap - spent - pending), ROUND_DOWN)
            over_cap = spent + pending > cap
        return {
            "model": ledger.model,
            "uncapped": cap is None,
            "budget_mode": "authorized_full_generation_uncapped"
            if cap is None
            else "capped_pilot",
            "max_usd": None if cap is None else str(cap),
            "reported_usd": str(_quantize(ledger.reported)),
            "retained_unresolved_usd": str(_quantize(ledger.retained)),
            "unresolved_pending_usd": str(_quantize(pending)),
            "accounted_usd": str(total),
            "available_usd": None if available is None else str(available),
            "fresh_requests": ledger.fresh_requests,
            "cache_hits": ledger.cache_hits,
            "pending_request_ids": sorted(ledger.reservations),
            "stopped": ledger.stopped,
            "stop_reason": ledger.stop_reason,
            "over_cap": over_cap,
        }

    def _save_ledger(self) -> None:
        _write_json(self._ledger_path, self._ledger.to_json())

    def _reserve(self, request_id: str, charge: Decimal, digest: str) -> None:
        if self._ledger.stopped:
            raise BudgetError(
                f"client is stopped ({self._ledger.stop_reason}); "
                "no further requests are allowed"
            )
        if request_id in self._ledger.reservations:
            raise ClientError(
                f"{request_id} already has an unresolved attempt; "
                "it is never retried or charged again"
            )
        committed = self._ledger.spent() + self._ledger.pending() + charge
        if self._ledger.max_usd is not None and committed > self._ledger.max_usd:
            raise BudgetError(
                f"worst-case reservation would spend {committed} USD "
                f"of the {self._ledger.max_usd} cap; request refused before sending"
            )
        self._ledger.reservations[request_id] = {
            "reserved_usd": str(charge),
            "sha256": digest,
            "state": "pending",
        }
        self._ledger.fresh_requests += 1
        # Durable reservation, and durable note of what we are about to attempt.
        self._save_ledger()

    def _settle(
        self, request_id: str, actual_usd: Decimal | None, stop_reason: str = ""
    ) -> Decimal:
        """Replace the reservation with the known charge, or keep the worst case."""
        entry = self._ledger.reservations.pop(request_id, None)
        if entry is None:
            raise ClientError(f"{request_id} has no reservation to settle")
        reserved = _entry_charge(entry)
        if actual_usd is None:
            self._ledger.retained = _quantize(self._ledger.retained + reserved)
        else:
            self._ledger.reported = _quantize(self._ledger.reported + actual_usd)
            if actual_usd > reserved:
                stop_reason = (
                    f"billed {actual_usd} USD exceeds the {reserved} USD "
                    "reservation bound; the price ceiling is wrong"
                )
        if stop_reason:
            self._ledger.stopped = True
            self._ledger.stop_reason = stop_reason
        self._save_ledger()
        return reserved

    # ------------------------------------------------------------------- calling

    def complete(
        self,
        request_id: str,
        system: str,
        payload: str | dict[str, object],
        schema: dict[str, object],
        temperature: float = 0.7,
        max_tokens: int = MAX_TOKENS_CAP,
        *,
        reasoning_effort: Literal["low"] | None = None,
    ) -> dict[str, object]:
        """One budgeted call. Raises ClientError/BudgetError instead of half-succeeding.

        A string payload is sent as the literal human-readable user message;
        a dict payload keeps the legacy compact-JSON user message.
        Explicit low reasoning is opt-in per invocation; defaults remain off.
        Reasoning text is excluded, and all completion tokens share the same cap.
        """
        if self._closed:
            raise ClientError("client is closed")
        if not isinstance(request_id, str) or not ID_PATTERN.fullmatch(request_id):
            raise ClientError("request_id must be a short file-safe identifier")
        if type(system) is not str or not system.strip():
            raise ClientError("system prompt must be a nonempty string")
        if isinstance(payload, str):
            if not payload.strip():
                raise ClientError("string payload must be a nonempty message")
            user_content = payload
        elif isinstance(payload, dict):
            user_content = _dump_json(payload)
        else:
            raise ClientError("payload must be a readable string or a JSON object")
        if not isinstance(schema, dict):
            raise ClientError("schema must be a JSON object")
        if type(temperature) is not float or not 0.0 <= temperature <= 2.0:
            raise ClientError("temperature must be a float between 0 and 2")
        if reasoning_effort is not None and reasoning_effort != "low":
            raise ClientError("reasoning_effort must be low or None (disabled)")
        if type(max_tokens) is not int or max_tokens < 1:
            raise ClientError("max_tokens must be a positive integer")
        token_cap = (
            MAX_TOKENS_CAP if reasoning_effort is None else REASONING_MAX_TOKENS_CAP
        )
        if max_tokens > token_cap:
            raise ClientError(
                f"max_tokens must stay within the client cap of {token_cap}"
            )
        if self._ledger.stopped:
            raise BudgetError(
                f"client is stopped ({self._ledger.stop_reason}); "
                "no further requests are allowed"
            )

        problem = _schema_problem(schema)
        if problem:
            raise ClientError(f"schema is not usable for tool_gen: {problem}")
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            raise ClientError(f"invalid JSON Schema: {_redact(exc.message)}") from None

        body: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": SCHEMA_NAME, "strict": True, "schema": schema},
            },
            "reasoning": (
                {"enabled": False}
                if reasoning_effort is None
                else {"effort": reasoning_effort, "exclude": True}
            ),
            "provider": {
                "require_parameters": True,
                "max_price": {
                    "prompt": float(PROMPT_USD_PER_MILLION),
                    "completion": float(COMPLETION_USD_PER_MILLION),
                    "request": float(REQUEST_FEE_CEILING),
                },
            },
        }
        request_bytes = _dump_json(body, sort_keys=False).encode("utf-8")
        digest = hashlib.sha256(request_bytes).hexdigest()
        evidence_path = self._requests_dir / f"{request_id}.json"
        finish_reason = ""

        cached = self._cached(evidence_path, digest, request_id)
        if cached is not None:
            return cached

        # Missing local credentials are a pre-send setup error, not an
        # unresolved billable attempt. Cache hits above need no credentials.
        key = self._api_key()
        charge = worst_case_usd(len(request_bytes), max_tokens)
        self._reserve(request_id, charge, digest)
        self._write_evidence(
            evidence_path,
            {
                "request_id": request_id,
                "state": "pending",
                "request_sha256": digest,
                "request_body": body,
                "request_body_json": request_bytes.decode("utf-8"),
                "system": system,
                "payload": payload,
                "schema": schema,
                "reserved_usd": str(charge),
                "cache_hit": False,
            },
            api_key=None,
        )

        record: dict[str, object] = {
            "request_id": request_id,
            "state": "failed",
            "request_sha256": digest,
            "request_body": body,
            "request_body_json": request_bytes.decode("utf-8"),
            "system": system,
            "payload": payload,
            "schema": schema,
            "reserved_usd": str(charge),
            "cache_hit": False,
        }
        try:
            response_text = self._post(key, request_bytes)
        except ClientError as exc:
            # Anything we could not answer definitively stays charged at worst case.
            self._settle(request_id, None, stop_reason=str(exc))
            record["error"] = _redact(str(exc), 300)
            self._write_evidence(evidence_path, record, api_key=key)
            raise

        record["raw_http_json"] = _safe_http_json(response_text)
        usage = _usage_of(record["raw_http_json"])
        actual = _known_cost(usage)
        reserved = self._settle(request_id, actual, stop_reason="")
        record["usage"] = usage
        record["billed_usd"] = str(actual) if actual is not None else None
        record["retained_worst_case_usd"] = (
            None if actual is not None else str(reserved)
        )
        record["provider"] = _provider_of(record["raw_http_json"], body["provider"])
        reported_model = (
            record["raw_http_json"].get("model")
            if isinstance(record["raw_http_json"], dict)
            else None
        )
        # Only a real returned identifier counts; the request is never re-routed.
        record["model"] = (
            reported_model
            if isinstance(reported_model, str) and reported_model
            else self.model
        )

        try:
            output, content, finish_reason = _parse_output(response_text, schema)
        except ClientError as exc:
            record["error"] = _redact(str(exc), 300)
            record["finish_reason"] = finish_reason
            record["raw_content"] = _content_of(record["raw_http_json"])
            record["failure_kind"] = (
                "model_output" if isinstance(exc, OutputError) else "protocol"
            )
            self._write_evidence(evidence_path, record, api_key=key)
            message = (
                f"{request_id}: {_redact(str(exc), 200)} "
                "(the attempt stays accounted in accounting())"
            )
            if isinstance(exc, OutputError):
                raise OutputError(message) from None
            raise ClientError(message) from None

        record["state"] = "completed"
        record["raw_content"] = content
        record["finish_reason"] = finish_reason
        self._write_evidence(evidence_path, record, api_key=key)
        metadata: dict[str, object] = {
            "request_id": request_id,
            "model": record["model"],
            "requested_model": self.model,
            "provider": record["provider"],
            "usage": usage,
            "billed_usd": record["billed_usd"],
            "retained_worst_case_usd": record["retained_worst_case_usd"],
            "reserved_usd": str(charge),
            "cache_hit": False,
            "request_sha256": digest,
            "finish_reason": finish_reason,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return {"output": output, "metadata": metadata, "raw_content": content}

    def _cached(
        self, evidence_path: Path, digest: str, request_id: str
    ) -> dict[str, object] | None:
        """A completed identical request is explicit, free and never re-sent."""
        if not evidence_path.exists():
            return None
        record = _read_strict_json(evidence_path)
        stored_digest = record.get("request_sha256")
        state = record.get("state")
        if stored_digest != digest:
            raise ClientError(
                f"{request_id} already exists with a different request hash; "
                "refusing to overwrite the recorded attempt"
            )
        if state == "pending":
            raise ClientError(
                f"{request_id} has an attempt with no recorded result; "
                "it is not retried or charged again"
            )
        if state == "failed":
            reason = (
                record.get("error")
                if isinstance(record.get("error"), str)
                else "unknown"
            )
            message = (
                f"{request_id} already failed ({_redact(reason, 160)}); "
                "a billed attempt is never silently retried"
            )
            if record.get("failure_kind") == "model_output":
                raise OutputError(message)
            # Older completed/billed failures predate failure_kind. Reclassify
            # using their retained envelope, never by repeating the request.
            envelope, schema = record.get("raw_http_json"), record.get("schema")
            if isinstance(envelope, dict) and isinstance(schema, dict):
                try:
                    _parse_output(_dump_json(envelope), schema)
                except OutputError:
                    raise OutputError(message) from None
                except ClientError:
                    pass
            raise ClientError(message)
        if state != "completed":
            raise ClientError(f"{request_id} evidence has an unreadable state")
        output, content, _ = _output_of_record(record)
        self._ledger.cache_hits += 1
        self._save_ledger()
        cached_model = record.get("model")
        metadata: dict[str, object] = {
            "request_id": request_id,
            "model": cached_model if isinstance(cached_model, str) else self.model,
            "requested_model": self.model,
            "provider": record.get("provider", {}),
            "usage": record.get("usage", {}),
            "billed_usd": record.get("billed_usd"),
            "reserved_usd": record.get("reserved_usd"),
            "cache_hit": True,
            "request_sha256": digest,
            "cache_state": "completed",
            "finish_reason": record.get("finish_reason"),
        }
        return {"output": output, "metadata": metadata, "raw_content": content}

    def _write_evidence(
        self, path: Path, record: dict[str, object], api_key: str | None
    ) -> None:
        payload = dict(record)
        payload["ledger_snapshot"] = self._ledger.to_json()
        text = _dump_json(payload)
        if api_key and api_key in text:
            raise ClientError("refusing to persist evidence containing the API key")
        _write_json(path, payload)

    def _api_key(self) -> str:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key.strip():
            raise ClientError(
                "OPENROUTER_API_KEY is not set; export it in the "
                "environment before making fresh requests "
                "(cached requests need no credentials)"
            )
        return key.strip()

    def _post(self, key: str, request_bytes: bytes) -> str:
        request = urllib.request.Request(
            API_URL,
            data=request_bytes,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Tool composition pilot",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw: object = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 402:
                # The account's own credit limit is the real budget in uncapped mode:
                # stop cleanly, keep the worst-case charge, never retry or top up.
                raise BudgetError(
                    "OpenRouter HTTP 402 (insufficient OpenRouter credits): "
                    "generation stops here without retry or automatic top-up; "
                    "reservation retained"
                ) from None
            hint = _ERROR_CODES.get(exc.code, "failed")
            raise ClientError(
                f"OpenRouter HTTP {exc.code} ({hint}); reservation retained"
            ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            raise ClientError(
                f"transport failed with no definitive answer "
                f"({_redact(str(reason))}); reservation retained"
            ) from None
        if not isinstance(raw, bytes):
            raise ClientError(
                "provider response body is not bytes; reservation retained"
            )
        return raw.decode("utf-8", errors="replace")


def _safe_http_json(response_text: str) -> object:
    """Best-effort envelope for evidence/accounting; never trusted for output."""
    try:
        return _load_json(response_text)
    except ClientError:
        return {
            "unparseable_http_response": True,
            "sha256": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
        }


def _http_json(response_text: str) -> dict[str, object]:
    parsed = _safe_http_json(response_text)
    if not isinstance(parsed, dict):
        raise ClientError("OpenRouter response was not a JSON object")
    if parsed.get("unparseable_http_response") is True:
        raise ClientError("OpenRouter response body was not valid JSON")
    return parsed


def _usage_of(envelope: object) -> dict[str, object]:
    usage = envelope.get("usage") if isinstance(envelope, dict) else None
    return usage if isinstance(usage, dict) else {}


def _provider_of(envelope: object, requested: object) -> dict[str, object]:
    """Reported routing/provider data, plus proof of the provider parameters we sent."""
    provider: dict[str, object] = {}
    if isinstance(envelope, dict):
        routed = envelope.get("provider")
        if isinstance(routed, str):
            provider["provider"] = routed
        for field in ("routing", "provider_name", "provider_slug"):
            value = envelope.get(field)
            if isinstance(value, str):
                provider[field] = value
    provider["requested_parameters"] = requested if isinstance(requested, dict) else {}
    return provider


def _known_cost(usage: dict[str, object]) -> Decimal | None:
    """Returned USD charge, or None. A missing cost is never assumed to be free."""
    cost = usage.get("cost")
    if type(cost) in (int, float):
        value = Decimal(str(cost))
    elif isinstance(cost, str):
        try:
            value = Decimal(cost)
        except InvalidOperation:
            return None
    else:
        return None
    if not value.is_finite() or value < 0:
        return None
    return _quantize(value)


def _content_of(envelope: object) -> str:
    """Keep the raw model text for review even when parsing later failed."""
    if not isinstance(envelope, dict):
        return ""
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else ""


def _parse_output(
    response_text: str, schema: dict[str, object]
) -> tuple[dict[str, object], str, str]:
    envelope = _http_json(response_text)
    if envelope.get("error") is not None:
        raise ClientError("OpenRouter reported an error payload")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ClientError("OpenRouter response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ClientError("OpenRouter choice was not an object")
    finish_reason = str(first.get("finish_reason") or "")
    if finish_reason in ("length", "content_filter", "tool_calls"):
        raise OutputError(f"completion stopped early: {finish_reason}")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ClientError("OpenRouter message was not an object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OutputError("empty model completion (cause unknown)")
    try:
        output = _load_json(content)
    except ClientError as exc:
        raise OutputError(str(exc)) from None
    if not isinstance(output, dict):
        raise OutputError("model output is not a JSON object")
    try:
        jsonschema.Draft202012Validator(schema).validate(output)
    except jsonschema.ValidationError as exc:
        trail = "/".join(str(part) for part in list(exc.absolute_path)[:4])
        raise OutputError(
            f"output violates the schema at {trail or 'root'}: {_redact(exc.message)}"
        ) from None
    return output, content, finish_reason


def _output_of_record(record: dict[str, object]) -> tuple[dict[str, object], str, str]:
    """Re-derive and re-validate a cached answer; a corrupt cache never passes."""
    content = record.get("raw_content")
    if not isinstance(content, str):
        raise ClientError("cached evidence has no raw content")
    schema = record.get("schema")
    if not isinstance(schema, dict):
        raise ClientError("cached evidence has no recorded schema")
    output = _load_json(content)
    if not isinstance(output, dict):
        raise ClientError("cached raw content is not a JSON object")
    jsonschema.Draft202012Validator(schema).validate(output)
    finish_reason = record.get("finish_reason")
    return output, content, finish_reason if isinstance(finish_reason, str) else ""
