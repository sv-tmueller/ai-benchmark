"""``playability`` grading mode: read the CDP-harness verdict from the meta.

This mode needs no ``[grading]`` block. The verdict lives in the result's
paired ``<stem>.meta.json``, in one of two shapes found across ``results/``:

- newer: ``meta["playability_verification"]["playability_verdict"]``
- older: ``meta["playability"]["label"]``

``PLAYABLE_VERIFIED`` is the only passing label; every other label
(``BOOTS_ONLY``, ``BROKEN_AT_BOOT``, ``BLUEPRINT_ONLY``,
``BLUEPRINT_INCOMPLETE``, ``SCRIPT_TRUNCATED``) fails. Existing labels are
taken as ground truth — no re-verification happens here.
"""

import json

from ._common import derive_model, pair_meta

MODE = "playability"
PASSING_LABEL = "PLAYABLE_VERIFIED"


def resolve_verdict(meta):
    """Return the playability label carried by ``meta``, or ``None``."""
    verification = meta.get("playability_verification")
    if isinstance(verification, dict):
        verdict = verification.get("playability_verdict")
        if verdict:
            return verdict

    playability = meta.get("playability")
    if isinstance(playability, dict):
        label = playability.get("label")
        if label:
            return label

    return None


def _result(prompt_id, result_path, passed, detail):
    return {
        "prompt_id": prompt_id,
        "model": derive_model(result_path),
        "mode": MODE,
        "pass": passed,
        "detail": detail,
    }


def grade(result_path, grading, prompt):
    """Return the verdict dict derived from the paired meta sidecar."""
    prompt_id = prompt["id"]
    meta_path = pair_meta(result_path)
    if meta_path is None:
        return _result(prompt_id, result_path, False, "playability meta not found")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _result(
            prompt_id, result_path, False, "playability meta unreadable ({})".format(exc)
        )

    if not isinstance(meta, dict):
        return _result(prompt_id, result_path, False, "playability verdict missing")

    verdict = resolve_verdict(meta)
    if verdict is None:
        return _result(prompt_id, result_path, False, "playability verdict missing")

    return _result(
        prompt_id,
        result_path,
        verdict == PASSING_LABEL,
        "playability verdict: {}".format(verdict),
    )
