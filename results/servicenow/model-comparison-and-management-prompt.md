# Model Evaluation — ServiceNow Consulting & Local LLM Feasibility

*Prepared for the management PowerPoint. This page merges the comparison table
with the explanation of what was tested and why, in non-technical language.*

---

## 1. The comparison table

Two questions: which model is best for **ServiceNow story writing & development**,
and which is best for **game development** (used as a stress test).

### 1a. Game / app development (the stress test — 10 hard prompts)

| Model | Played a game? | What it produced | Output effort | Verdict |
|-------|:---:|---|---|---|
| **GLM-5.3 Flash** | **1 / 10** | 10/10 built; 1 genuinely playable | Highest (~38k) | Only one that produced a playable result |
| GLM-5.2 | 0 / 10 | 10 design blueprints, no playable game | High (~33k) | Design only, no runnable output |
| gpt-oss-120b | 0 / 10 | 10 design blueprints, no playable game | Low (~10k) | Design only, no runnable output |
| DeepSeek V4.1 flash | not recorded | ran the full task set incl. a deep reasoning test | — | No playability result captured |
| Qwen 3.8 27B | — | **not run in this test** | — | No data |

**Bottom line (game dev):** of the models actually tested, only **GLM-5.3 Flash**
produced anything playable — and that was 1 of 10. In plain terms: none of the
local models cleared the bar on the hardest task; Flash came closest.

### 1b. ServiceNow story writing & development (your real use case)

| Model | ServiceNow test? | Result |
|-------|:---:|---|
| **GLM-5.3 Flash** | **Yes** | Produced a **complete, professional** catalog story — a record producer, a validated variable set, and acceptance criteria. **Not yet checked against a real ServiceNow schema.** |
| GLM-5.2 | not run | no data |
| gpt-oss-120b | not run | no data |
| DeepSeek V4.1 flash | not run | no data |
| Qwen 3.8 27B | not run | no data |

**Bottom line (ServiceNow):** the data is **mostly silent** — only Flash was
tried, and it produced a good-looking story (but unverified against a real
schema). **We cannot honestly rank the others for ServiceNow from this test.**
The right next step is to run your *actual* ServiceNow task on the models
you're considering and check the output against a real ServiceNow schema.

---

## 2. Why I was testing this (for the PowerPoint — non-technical)

> Merge this with the other model results, then build the PowerPoint from it.

**What this was, in one line:** a **cost-and-feasibility study** — I was finding
out whether we can run **local AI models** instead of paid API models (like
Claude) for our ServiceNow consulting work, and how they compare.

**The reason behind the testings:**

- We currently use **Claude** to build our ServiceNow **plugin and skills**
  (the reusable guidance that helps produce stories and development artifacts).
  Paid API models are the quality bar — but they cost more per use.
- **Local models cost far less to run**, so the question for management is:
  *can a cheaper local model do our ServiceNow work well enough to switch to
  it, and save money?*
- To answer that, I put the candidate models through a set of tasks and
  measured how their **results differ** from the paid models. This is a
  **capability comparison**, not a production build.

**Why games were part of it (the part that may look odd):**

- Game/app development was used as a **stress test** — the hardest kind of task,
  to push the models and see where they break.
- **It is not the ServiceNow work itself.** A game is the worst-case test;
  ServiceNow work is more structured and pattern-based, so the games are a
  proxy for "how capable is the model," not a ServiceNow result.
- **Important note on scope:** some of the tasks were not the ServiceNow work
  and were not the kind of "private development" that our API keys normally
  allow. That is by design — the goal was to **measure how local models behave
  and how their results differ from the paid models**, so we can decide
  whether and where to use them for **cost savings**.

**What the results tell management:**

- The cheaper models **do not yet match the paid models** on the hardest tasks.
  The one model that got closest (Flash) still only succeeded in 1 of 10 hard
  tasks.
- On a **real ServiceNow task**, Flash produced a **complete-looking story** —
  but it has **not been verified against a real ServiceNow schema** yet, so it
  is a **promising sign, not a proven result**.
- **The honest conclusion:** the local models are **not yet a drop-in
  replacement** for the paid models on ServiceNow work — but the gap is
  narrowing, and the only way to know for sure is to **run our real ServiceNow
  task and check the output against a real ServiceNow schema.**

**Recommended next step:** run one real ServiceNow task (a story + a small
update set) on the models we're considering, and verify the output against a
real ServiceNow schema. That single test answers the question the game stress
test cannot.

---

*Data basis: batch #97 (flash) and #112 (gpt-oss-120b / GLM-5.2), plus the
reasoning probes. DeepSeek V4.1 flash ran the task set but has no playability
record; Qwen 3.8 27B was not run. ServiceNow has one unverified Flash sample.
No Claude or ChatGPT verdict exists in this dataset — that comparison comes
from separate external testing.*
