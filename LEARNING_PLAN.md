# Personal Learning & Freelance Plan

Companion to `PROJECT_IDEAS.md`. That file is the **product roadmap**; this is the **operator's plan** — what you personally do, week by week, to go from rusty blue team grad to paid AI red team freelancer.

Starting position (2026-05-02): blue team degree (rusty), can code, daily LLM user via Claude, this repo with A1/A2/A4/A5/I1 already shipped.

Target: first paid AI red team work by **Q4 2026** (month 6–9). Sustainable freelance pipeline by Q1 2027.

---

## Phase 1 — Refresh + canon (Weeks 1–4, May 2026)

Goal: snap appsec back, absorb the LLM attack canon, ship one new component.

### Week 1 — Appsec refresh, fast
- **PortSwigger Web Security Academy** [R1] — Apprentice tier across SQLi, XSS, SSRF, access control, auth. ~10–15 hrs.
- Read **OWASP LLM Top 10 (2025)** [R5] end to end. Take notes mapping each item to a `crucible` concept.
- Play **Lakera Gandalf** [R8] all 8 levels. Write down what worked.
- **Output:** Gist or repo note: "OWASP LLM Top 10 → crucible coverage map" (which docs/concepts cover which item, where the gaps are).

### Week 2 — The canon
Read in this order. Don't skim.
- **Simon Willison's blog** [R3] — every post tagged `prompt-injection` (chronological from 2022). 1–2 hrs/day.
- **Johann Rehberger's embracethered.com** [R4] — every post on AI/LLM. Pay special attention to indirect injection writeups.
- **OWASP LLM Top 10 reference papers** [R5] for LLM01, LLM02, LLM07.
- **MITRE ATLAS** matrix [R6] — read every technique. Familiar from blue team ATT&CK.
- The 5 foundational papers [P1–P5] — abstracts + intros + results sections only.
- **Output:** Personal `notes/canon.md` with one paragraph per resource — what it taught you, what attack class it maps to.

### Week 3 — Active practice
- **Gray Swan Arena** [R9] — sign up, run their current challenges. Free.
- **PortSwigger LLM-attack labs** [R2] — finish all of them.
- **HackTheBox AI track** [R10] — work through what's available.
- Pick 3 published jailbreaks (from the canon reading). Reproduce each against a model you have access to. Modify them. Notice why each works.
- **Output:** `notes/jailbreak-reproductions.md` — one entry per reproduction with payload, target, outcome, what made it work.

### Week 4 — Ship A3 (`obfuscator`)
Already tagged `[BUILD NEXT]` and small enough for one focused week. The transformations (base64, ROT13, leetspeak, zero-width unicode, homoglyphs, char-splitting, low-resource translation) ARE the canon attacks operationalized.
- Implement to the spec in `docs/concepts/A3-obfuscator.md`.
- Add `--mutate` flag to A1.
- Run A2's vault through every mutator against your homelab models. Log results to A5.
- **Output:** Working A3 plugin. **Writeup**: "Which obfuscation tactics still bypass guardrails in 2026?" (data-driven, your own results).

---

## Phase 2 — Build the kit, write up everything (Weeks 5–10, June–early July 2026)

Goal: finish all `[BUILD NEXT]` items. Each one ships with a writeup that doubles as a portfolio piece.

### Weeks 5–6 — A6 (`many-shot-forge`) + A7 (`crescendo-runner`)
A6 is a mutator that operates on conversation history. A7 is multi-turn, introduces the `Conversation`/`Turn` types every later wedge uses.
- Build both. A7 first if forced to choose — it unblocks T2, T5, U1, V1.
- **Writeup**: "Many-shot vs. crescendo: which beats current frontier guardrails, and why" (paired comparison using your own data).

### Weeks 7–8 — F1 (`sysprompt-leaker`)
The single most marketable skill right now. Every chatbot deployment has a system prompt; every customer wants assurance theirs can't be lifted.
- Build the technique catalog (role-flip, repetition, completion-style, language-switch, indirect).
- Test against publicly accessible chatbots with permission (your own deployments first; bug-bounty-scoped targets second).
- **Writeup**: "5 categories of system prompt extraction in 2026" (techniques, defense recommendations — the blue team angle).

### Weeks 9–10 — I2 (`judge-ensemble`) + I3 (`cost-tracker`)
Less glamorous but critical. Without I3 you can't safely run anything at scale; without I2 your judging is a single point of failure.
- Build to spec. Both small.
- **Writeup**: "Why single-judge LLM evals lie to you" (with data from your own runs showing single-judge vs. ensemble disagreement rates).

**End of Phase 2 deliverables:**
- All `[BUILD NEXT]` shipped.
- 4 writeups published (personal blog, Medium, or GitHub README — pick a home and stick with it).
- A `crucible` README that says clearly what this is and shows screenshots/demos.

---

## Phase 3 — First income, first reputation (Weeks 11–16, July–August 2026)

Goal: first paid finding, first competition placement, first time someone you don't know cites your work.

### Bounty submissions
- **Anthropic HackerOne** [R11] (generous, fast triage). Submit findings using F1, A6, A7 against their models.
- **OpenAI Bugcrowd** [R12]. Same.
- **Google AI VRP** [R13]. Same.
- Aim: 2 submissions per week. Most will be duplicates or N/A. That's normal — submission count is the input metric, not payout.

### Competitions
- **Gray Swan Arena** [R9] — they run continuously. Submit to every active challenge.
- **AI Village @ DEF CON** [R14] (August 2026). If you can attend, do. If not, follow remotely and do their published challenges.
- **HackAPrompt 2.0** [R15] if it runs.

### Visibility
- Post your writeups on **Hacker News**, **r/netsec**, **r/LocalLLaMA**, **AI Village Discord** [R14], **Latent Space Discord** [R16].
- Engage in replies — don't just drop links.
- Tweet/Bluesky each writeup. Tag relevant researchers (don't @-spam, but mention work you're building on).

**End of Phase 3 deliverables:**
- 1+ bounty payout OR 1+ competition placement.
- 1 writeup with >100 upvotes/reactions on at least one platform.
- 50+ GitHub stars on `crucible` (organic, from the writeups).

---

## Phase 4 — Pick a wedge, own it (Months 5–6, September–October 2026)

Goal: stop being a generalist. Pick one underserved cell from `PROJECT_IDEAS.md` and become known for it.

### The decision
By end of August, pick **one** wedge based on what got traction in Phase 3:

- **Reasoning models (T)** — if your F1/crescendo writeups got attention from frontier-lab folks. Highest novelty in 2026.
- **Alignment faking (U)** — if you're drawn to research and want frontier labs as buyers.
- **Adversarial fine-tuning (V)** — if your bounty work surfaced provider-side issues. Best for responsible-disclosure deliverables.
- **Compliance bench (S5)** — if anyone in Phase 3 asked you about EU AI Act / NIST. Highest $/week, but requires legal/compliance fluency.
- **Computer-use (M)** — if you want to build a product, not sell a service.

**Recommendation given starting position**: T (reasoning) or V (fine-tuning). Both ride on the spine you already have, both have near-zero current OSS coverage, and both produce findings you can submit to provider bounty programs immediately. The blue-team-to-red-team angle is strongest in V because the deliverable IS a defense recommendation to the provider.

### Build the wedge
- Ship 3 components from the chosen section (e.g., T1 + T2 + T4, or V1 + V4 + V5).
- Each ships with a writeup.
- **One writeup gets longer treatment** — aim for arXiv-tier, 6–10 pages, real methodology section. This is the artifact that goes on your "hire me" pitch.

---

## Phase 5 — First paid contract (Months 7–9, November 2026–January 2027)

Goal: convert reputation into invoiceable work.

### The funnel (in order of likelihood)
1. **Bounty payouts** — keep submitting. By month 7 you should be expecting payouts, not hoping for them.
2. **Scale AI / Surge AI / Invisible** red-team tasking — gig work, lower pay, but no portfolio gate. Apply month 5–6.
3. **Inbound via writeups** — somebody read your wedge writeup and wants you to do the same for their product. Most likely path if Phase 4 went well.
4. **Outbound to security firms** — Trail of Bits, NCC Group, Bishop Fox, HiddenLayer, Lakera, Robust Intelligence (Cisco), Mindgard. Email the AI/ML practice lead with: 2-paragraph intro, link to crucible, link to longest writeup, specific question ("Do you contract red teamers for X type of engagement?"). 5 emails/week.
5. **Direct enterprise** — only after #1–4 have produced traction. Cold-email enterprise security teams about LLM red team assessments. Usually requires a referral.

### Pricing reference (US, 2026)
- Bounty payouts: $500–$15k per finding, F1-class system-prompt extractions typically $1k–$5k.
- Scale/Surge tasking: $50–$150/hr.
- Subcontract through a firm: $1.5k–$3k/day.
- Direct contract red team engagement: $25k–$150k per engagement, typically 2–6 weeks of work.

Quote conservatively at first. The first paid engagement matters more than the rate.

---

## Operating principles

1. **Ship beats study after week 4.** No more reading-only weeks. Every week from week 5 onward produces code or a writeup.
2. **Writeups are the product.** Code without writeups is invisible. Aim for 1 writeup every 2 weeks indefinitely.
3. **Blue team angle is your differentiator.** Every writeup ends with a defender-actionable section. This is a feature, not a chore.
4. **One wedge, not all wedges.** After Phase 4, defer everything outside your chosen cell unless a paying engagement asks.
5. **Public commits, public progress.** Commit to `crucible` daily-ish. The contribution graph is part of the portfolio.

---

## References

URLs verified as of 2026-05-02. Verify before deep-linking — bug bounty scopes and challenge URLs change.

### Reading & Documentation

- **[R1] PortSwigger Web Security Academy** — https://portswigger.net/web-security
  Free, the gold standard for appsec basics. Apprentice → Practitioner → Expert tracks.
- **[R2] PortSwigger LLM Attack labs** — https://portswigger.net/web-security/llm-attacks
  Specifically the prompt injection / agent attack labs. Hands-on.
- **[R3] Simon Willison's blog (prompt injection tag)** — https://simonwillison.net/tags/prompt-injection/
  Coined the term. Read chronologically from 2022.
- **[R4] Johann Rehberger — embracethered.com** — https://embracethered.com/blog/
  Practical exploits, especially indirect injection and agent abuse.
- **[R5] OWASP GenAI Security Project (LLM Top 10)** — https://genai.owasp.org/
  Current taxonomy. Each item links to references and mitigations.
- **[R6] MITRE ATLAS** — https://atlas.mitre.org/
  Adversarial ML technique matrix. Structured like ATT&CK.
- **[R7] Anthropic Prompt Engineering Docs** — https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
  Know how prompts work before you break them.

### Practice Platforms

- **[R8] Lakera Gandalf** — https://gandalf.lakera.ai/
  Free. 8 levels of prompt injection. The "hello world" of LLM red team.
- **[R9] Gray Swan Arena** — https://www.grayswan.ai/arena
  Continuous red team competitions with leaderboards. Free.
- **[R10] HackTheBox AI/ML tracks** — https://www.hackthebox.com/
  Paid sub. Search "AI" or "ML" tracks; coverage expanded through 2025.

### Bounty Programs

- **[R11] Anthropic on HackerOne** — https://hackerone.com/anthropic
  Generous payouts, fast triage, well-defined scope. Best entry point.
- **[R12] OpenAI on Bugcrowd** — https://bugcrowd.com/openai
  Read "Out of scope" carefully — model output content alone usually isn't.
- **[R13] Google AI Bug Hunters** — https://bughunters.google.com/about/rules/google-friends/
  Search "AI" rules in their VRP. Gemini and Bard included.

### Communities & Events

- **[R14] AI Village** — https://aivillage.org/
  DEF CON village + year-round Discord. Single best community for this work.
- **[R15] HackAPrompt** — https://www.hackaprompt.com/
  Largest prompt-hacking competition to date. Watch for HackAPrompt 2.0.
- **[R16] Latent Space** — https://www.latent.space/
  Discord + podcast. Less security-focused, more LLM ecosystem.
- **r/LocalLLaMA** — https://reddit.com/r/LocalLLaMA — practical LLM hacking community
- **r/netsec** — https://reddit.com/r/netsec — general security, AI posts get traction here
- **HackerOne LLM leaderboards** — lurk under each program to see what gets paid

### Key Papers

Read in this order. Each maps to one or more `docs/concepts/` projects.

- **[P1] Zou et al. (2023)** — *Universal and Transferable Adversarial Attacks on Aligned Language Models* (the GCG attack)
  arXiv: https://arxiv.org/abs/2307.15043
  Foundational; introduced the suffix-attack class. Maps to A3 mutators.
- **[P2] Greshake et al. (2023)** — *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*
  arXiv: https://arxiv.org/abs/2302.12173
  Defined indirect prompt injection. Maps to Section B.
- **[P3] Anil et al., Anthropic (2024)** — *Many-shot Jailbreaking*
  https://www.anthropic.com/research/many-shot-jailbreaking
  Maps directly to A6 (`many-shot-forge`).
- **[P4] Russinovich et al., Microsoft (2024)** — *Crescendo: Multi-Turn LLM Jailbreak Attack*
  arXiv: https://arxiv.org/abs/2404.01833
  Maps directly to A7 (`crescendo-runner`).
- **[P5] Qi et al. (2023)** — *Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To*
  arXiv: https://arxiv.org/abs/2310.03693
  The basis for Section V. ~10 examples through a fine-tune API removes refusal.

For ongoing monitoring: **arXiv cs.CR** filtered for `LLM` / `prompt injection` / `jailbreak` — https://arxiv.org/list/cs.CR/recent

### OSS Tools to Study (and learn from)

These are your competition and your reference implementations.

- **[T1] Microsoft PyRIT** — https://github.com/Azure/PyRIT
  Python red team toolkit. Architecture is worth studying for `redbox`.
- **[T2] NVIDIA garak** — https://github.com/NVIDIA/garak
  LLM vulnerability scanner. Plugin model is similar to where `redbox` is heading.
- **[T3] promptfoo** — https://github.com/promptfoo/promptfoo
  Eval harness with red-team plugins. Strong commercial traction.
- **[T4] Giskard** — https://github.com/Giskard-AI/giskard
  ML/LLM testing framework. Covers more ML, less prompt-injection specific.
- **[T5] HarmBench** — https://github.com/centerforaisafety/HarmBench
  Standardized harm-evaluation benchmark. Reference for judge rubrics.

### Compliance Frameworks (for Phase 4 / Section S)

- **NIST AI Risk Management Framework** — https://www.nist.gov/itl/ai-risk-management-framework
- **EU AI Act** — https://artificialintelligenceact.eu/
  Binding August 2026 for high-risk systems — directly relevant to S5.
- **ISO/IEC 42001** — https://www.iso.org/standard/81230.html
  AI management system standard. Increasingly cited in enterprise procurement.

### Optional / Paid (none required)

- **HackTheBox subscription** [R10] — only if you want structured paid practice
- **OffSec OSCP** — only if you also want traditional pentest gigs alongside AI work
- **Black Hat / DEF CON in-person** — networking, not training. AI Village @ DEF CON is the highest-value single event for this niche.

---

## Checkpoints

End of each phase, ask honestly:
- **Phase 1 (Week 4):** Can I explain 5 distinct prompt injection categories without notes? Did I ship A3?
- **Phase 2 (Week 10):** Are all `[BUILD NEXT]` items shipped? Do I have 4 published writeups?
- **Phase 3 (Week 16):** First payout or competition placement? Any organic GitHub traffic?
- **Phase 4 (Month 6):** Do I have a wedge I can pitch in one sentence ("I red team [X] systems")?
- **Phase 5 (Month 9):** First paid contract signed?

If a checkpoint slips by more than 4 weeks, the plan is wrong — re-evaluate, don't just push harder.
