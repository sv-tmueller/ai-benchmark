# Finding the Second Derivative

**Given:** 
$$f(x) = 3x^4 - 5x^3 + 2x^2 - 7x + 11$$

---

## Step 1: Find the First Derivative, f′(x)

Apply the **power rule**: $\frac{d}{dx}\left(ax^n\right) = anx^{n-1}$, differentiating one term at a time.

| Term | Differentiation |
|------|----------------|
| $3x^4$ | $4 \cdot 3x^{4-1} = 12x^3$ |
| $-5x^3$ | $3 \cdot (-5)x^{3-1} = -15x^2$ |
| $2x^2$ | $2 \cdot 2x^{2-1} = 4x$ |
| $-7x$ | $-7$ |
| $11$ | constant → $0$ |

Combining these results:

$$f'(x) = 12x^3 - 15x^2 + 4x - 7$$

---

## Step 2: Differentiate Again to Get f″(x)

Now apply the same rules to $f'(x)$:

| Term | Differentiation |
|------|----------------|
| $12x^3$ | $3 \cdot 12x^{3-1} = 36x^2$ |
| $-15x^2$ | $2 \cdot (-15)x^{2-1} = -30x$ |
| $4x$ | $4$ |
| $-7$ | constant → $0$ |

### Final Simplified Expression:

$$\boxed{f''(x) = 36x^2 - 30x + 4}$$

---

## Step 3: Evaluate f″(2)

Substitute $x = 2$ into the second derivative:

$$f''(2) = 36(2)^2 - 30(2) + 4$$

Compute each piece carefully:

$$= 36(4) - 60 + 4$$
$$= 144 - 60 + 4$$
$$= 84 + 4$$

$$\boxed{f''(2) = 88}$$

Since $f''(2) > 0$, the graph of $f$ is concave up at $x = 2$. ✓