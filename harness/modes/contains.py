"""``contains`` grading mode: check that the expected answer appears verbatim.

The rule comes from the prompt TOML's ``[grading]`` table:

    [grading]
    mode     = "contains"
    expected = "42"

``expected`` is compared as text, so numeric answers work without quoting.
"""

from ._common import derive_model


def grade(result_path, grading, prompt):
    """Return the verdict dict for a substring match of ``grading["expected"]``."""
    expected = str(grading["expected"])
    try:
        text = result_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "prompt_id": prompt["id"],
            "model": derive_model(result_path, prompt),
            "mode": "contains",
            "pass": False,
            "detail": "result file not found ({})".format(exc.strerror),
        }

    if expected in text:
        detail = 'expected "{}" found'.format(expected)
    else:
        detail = 'expected "{}" not found'.format(expected)

    return {
        "prompt_id": prompt["id"],
        "model": derive_model(result_path, prompt),
        "mode": "contains",
        "pass": expected in text,
        "detail": detail,
    }
