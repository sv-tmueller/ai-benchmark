Here's an iterative implementation using an explicit stack, followed by tests:

```python
"""Flattening utilities for arbitrarily nested integer lists."""

from __future__ import annotations

from typing import Union, cast

# Recursive type alias: an int, or a list whose elements are themselves
# NestedIntLists -- e.g. int, [int], [[int, [int]]], ...
NestedIntList = Union[int, list["NestedIntList"]]


def flatten(data: NestedIntList) -> list[int]:
    """Flatten an arbitrarily nested list of integers into a flat list.

    Values are collected in depth-first, left-to-right order. Recursion is
    avoided entirely: an explicit LIFO stack drives the traversal, so inputs
    nested deeper than Python's recursion limit are handled safely.

    Args:
        data: An arbitrarily nested list of integers. Any non-list item is
            treated as a leaf value and copied to the output unchanged;
            per the stated contract these will always be ints.

    Returns:
        A new ``list[int]`` containing every leaf value in encounter order.

    Complexity:
        O(n) time and O(n) auxiliary space in the worst case, where n is the
        total number of items (ints plus container lists).

    Notes:
        Assumes the input has no cyclic references (i.e., no list contains
        itself, directly or indirectly).

    Example:
        >>> flatten([1, [2, [3, 4]], 5])
        [1, 2, 3, 4, 5]
    """
    result: list[int] = []

    # Seed the stack with the root (wrapped so bare scalars also work).
    stack: list[NestedIntList] = [data]

    while stack:
        current = stack.pop()
        if isinstance(current, list):
            # Extend in REVERSED order so the leftmost child ends up on top
            # of the stack and is therefore processed next (LIFO discipline),
            # preserving original left-to-right sequence.
            stack.extend(reversed(current))
        else:
            # Input contract guarantees ints; cast documents that guarantee
            # for static type checkers.
            result.append(cast(int, current))

    return result


if __name__ == "__main__":
    # 1. Mixed-depth example from the specification.
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]

    # 2. Empty lists at various depths collapse to an empty result.
    assert flatten([]) == []
    assert flatten([[], [[]], [[[[]]]]]) == []

    # 3. Depth-first order preserved across sibling branches and duplicates.
    assert flatten([[[1], [2, 3]], [4], 1]) == [1, 2, 3, 4, 1]

    # 4. Nesting far deeper than the default recursion limit (~1000 frames);
    #    this would crash a naive recursive solution.
    deep: NestedIntList = 42
    for _ in range(50_000):
        deep = [deep]
    assert flatten(deep) == [42]

    # 5. Graceful handling of a bare scalar input.
    assert flatten(7) == [7]

    print("All tests passed.")
```

Key points worth noting:

- **Order maintenance:** When a sublist is popped, its children are pushed in *reverse*, so the leftmost child sits atop the stack and is visited next — this reproduces exactly what natural recursion would produce.
- **No recursion-limit issues:** Test 4 nests 50,001 levels deep; a recursive version would hit `RecursionError` well past ~1000 levels.
- **Typing:** The self-referential alias `NestedIntList` models the recursive shape statically; `cast` bridges the gap between the dynamic check (`isinstance`) and the promised `int` payload.
- **Caveat:** As documented, cyclic inputs (e.g., `lst.append(lst)`) would loop indefinitely — detecting cycles would add per-node bookkeeping that most real-world callers don't want, so it's excluded by contract instead.