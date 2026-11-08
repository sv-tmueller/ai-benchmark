Here is an iterative implementation:

```python
def flatten(data):
    """Flatten an arbitrarily nested list of integers."""
    out = []
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, list):
            stack.extend(reversed(cur))
        else:
            out.append(cur)
    return out
```
