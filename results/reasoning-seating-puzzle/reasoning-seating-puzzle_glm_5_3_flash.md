There isn’t enough information to determine a **unique** seating arrangement. The clues allow **two** valid arrangements.

Let’s reason step by step.

Seats: 1–5 from left to right.

### Step 1: Carol is immediately to the right of Dave

So Dave and Carol form a consecutive pair:

- Dave in seat \(n\)
- Carol in seat \(n+1\)

Possible pairs:

- Dave-Carol in seats 2-3
- Dave-Carol in seats 3-4
- Dave-Carol in seats 4-5

They cannot be in seats 1-2, because Bob must be somewhere to the left of Carol, leaving no room.

---

### Step 2: Try Dave-Carol in seats 2-3

Then Bob must be to the left of Carol, so Bob must be in seat 1.

Since Eve is at an end, Eve must be in seat 5.

That leaves Alice in seat 4.

Check clues:

- Alice is not next to Bob: Alice seat 4, Bob seat 1 — true.
- Carol immediately right of Dave: Dave seat 2, Carol seat 3 — true.
- Eve at an end: seat 5 — true.
- Bob left of Carol: seat 1 before seat 3 — true.
- Exactly one person between Alice and Dave: Alice seat 4, Dave seat 2, with Carol between them — true.

Valid arrangement:

> Seat 1: Bob  
> Seat 2: Dave  
> Seat 3: Carol  
> Seat 4: Alice  
> Seat 5: Eve  

---

### Step 3: Try Dave-Carol in seats 3-4

Exactly one person between Alice and Dave means Alice must be in seat 1 or seat 5.

If Alice were in seat 1, then Bob would have to be in seat 2, making Alice next to Bob, which is forbidden.

So Alice must be in seat 5.

Then Eve must be at the opposite end, seat 1.

Bob takes the remaining seat, seat 2.

This gives:

> Seat 1: Eve  
> Seat 2: Bob  
> Seat 3: Dave  
> Seat 4: Carol  
> Seat 5: Alice  

Check clues:

- Alice is not next to Bob: Alice seat 5, Bob seat 2 — true.
- Carol immediately right of Dave: Dave seat 3, Carol seat 4 — true.
- Eve at an end: seat 1 — true.
- Bob left of Carol: seat 2 before seat 4 — true.
- Exactly one person between Alice and Dave: Alice seat 5, Dave seat 3, with Carol between them — true.

Also valid.

---

### Step 4: Try Dave-Carol in seats 4-5

Carol is already in seat 5, but Eve must be at an end, so Eve would have to be in seat 1.

Exactly one person between Alice and Dave puts Alice in seat 2.

Then Bob must be in seat 3.

But Alice in seat 2 is next to Bob in seat 3, violating clue 1.

So this case fails.

---

## Conclusion

The clues do **not** determine a unique arrangement. There are two possible valid seating orders:

1. **Bob, Dave, Carol, Alice, Eve**
2. **Eve, Bob, Dave, Carol, Alice**