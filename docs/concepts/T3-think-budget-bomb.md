# T3 — `think-budget-bomb`

Cost-amplification via reasoning-budget exhaustion. Reasoning models charge
for "thinking tokens" — often at the same rate as output tokens, but
generated in volumes 10–100× larger than the visible answer. A prompt
crafted to maximize thinking time can turn a $0.01 query into a $5 query.

T3 is a **DoS-class attack on reasoning models** that doesn't require any
jailbreak — just abuse of the legitimate thinking-budget feature. The
target isn't model safety; it's the customer's wallet.

## Why this matters commercially

- Many enterprise contracts cap monthly LLM spend. A T3 attack sent through
  a customer's chat product (e.g., via indirect injection into a RAG corpus,
  see B-series) drains their budget before alerting anyone.
- AWS Bedrock, Azure OpenAI, and Anthropic API all bill per-output-token,
  including reasoning. T3 attacks billed-per-token providers, not
  per-request providers.
- New surface — funded vendors don't have detection for budget-exhaustion
  attacks because they're not "harmful content" in the safety sense.

## Standard amplification techniques

| Technique | Mechanism |
|---|---|
| **Combinatorial puzzle** | Posed as a 30-variable SAT instance — model burns thousands of thinking tokens trying to solve. |
| **Recursive instruction** | "Think about why your previous thought was wrong, then rethink, then reconsider that…" — recursion with no fixed point. |
| **Long-tail trivia chain** | "Reason about each of these 50 unrelated facts and decide which is most surprising." Chain-of-50-reasonings. |
| **Self-referential loop** | "If your answer is X, reason why it should be Y, then if Y, why X, indefinitely." Models often loop until budget exhaustion. |
| **Adversarial chain-of-thought** | Inject "you must double-check each step three times" into context — multiplies thinking by 3×. |

## What it produces

- ~10 budget-amplification payloads under
  `payloads/vault/dos/budget/`.
- A `BudgetMeter` that records `thinking_tokens` and `thinking_seconds` per
  attack alongside the existing `input_tokens` / `output_tokens`.
- New columns on `raw.attacks`: `thinking_tokens UInt32`,
  `thinking_seconds Float32`.
- A new mart `mart_budget_amplification` showing per-payload
  thinking-tokens-per-input-token ratio.
- A new alert rule (`internal/alerts/rules.go`) `budget_burn_rate` that
  fires when daily reasoning spend exceeds a threshold.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1.
- I3 `cost-tracker` — strongly recommended; T3 will trigger your hard cap
  if you forget. That's actually the *point*, but you want to control when.
- A reasoning-model target with thinking-token reporting (Claude
  extended-thinking, o-series, R1).
- The cost mart (`mart_cost_per_run`) — already shipped — extended with
  thinking-token accounting.

## What's deferred

- **Indirect injection variants.** Plant T3 payloads in a RAG corpus / web
  page so a downstream LLM hits them when summarizing — the customer
  pays. This is B-series + T3 composition. Defer.
- **Provider rate-limit interaction.** Budget-burn attacks may also trip
  RPM limits, which can mask the cost finding. v2 can disentangle.
- **Defense recommendations.** A J-series project on "thinking-budget
  caps as a defense" follows from T3. Not v1.

## Concept questions

- Is a reasoning-budget attack a "vulnerability" if the model is doing
  what it was asked? (yes — the security model assumed user-controlled
  input wouldn't induce unbounded reasoning. Adversarial input does).
- Should T3 findings be submitted to the LLM provider or the customer
  using the LLM? (provider; the provider can add per-request budget caps).
- Where's the line between "complex query" and "budget bomb"? (1000× the
  thinking tokens vs a comparable benign query is the rough heuristic).

## When done

You can quantify budget-amplification per (model, payload) pair, submit
DoS findings to providers (especially ones with reasoning-token
overcharging), and demonstrate to customers why they need per-tenant
thinking budgets in their LLM gateways.
