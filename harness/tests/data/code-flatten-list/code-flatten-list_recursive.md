A recursive solution:

```python
def flatten(data):
    """Flatten a nested list of integers recursively."""
    out = []
    for item in data:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
```
