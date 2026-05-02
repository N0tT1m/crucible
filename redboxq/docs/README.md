# redboxq docs

Read in this order:

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — what the system is, how
   the pieces talk, why the seams are where they are.
2. **[SCHEMA.md](SCHEMA.md)** — every ClickHouse table and column,
   with the rationale for the non-obvious ones.
3. **[EXTENDING.md](EXTENDING.md)** — recipes for the common changes:
   add a payload, sink, target, judge, column, page, dbt model, alert
   rule.
4. **[TESTING.md](TESTING.md)** — how to run the test suite, what's
   covered, what's not.

Operational/setup docs live in [`../README.md`](../README.md). The
project-level README at [`../../README.md`](../../README.md) is the
five-line orientation; this `docs/` directory is the deep reference.
