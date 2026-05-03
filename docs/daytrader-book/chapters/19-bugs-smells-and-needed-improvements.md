# Chapter 19: Bugs, Smells, and Needed Improvements

Chapter 18 ended with modernization patterns worth reusing. This chapter does the opposite: it names what should not be normalized. DayTrader is valuable because it is realistic legacy code, and realistic legacy code contains defects, ambiguous behavior, risky shortcuts, stale descriptors, and architectural compromises that only make sense inside a benchmark sample.

For AI-assisted modernization training, this chapter is a defect map. It is not a blame list. The goal is to teach learners how to separate three categories that are often confused: bugs that can produce wrong behavior, smells that increase change risk, and improvements that should be planned deliberately rather than applied as drive-by cleanup.

## Bugs and Likely Behavioral Defects

These are issues that can produce incorrect behavior, brittle runtime behavior, or misleading benchmark results.

| Area | Issue | Why It Matters | Improvement Direction |
| --- | --- | --- | --- |
| Order completion | Completion dereferences an order before the missing-order check | A missing order can fail with a null-pointer path instead of intended handling | Move null check before relationship access and add a regression test |
| Quote publication | Quote-change event can publish in a separate transaction even if the quote update later rolls back | Consumers can observe a market event for state that did not commit | Decide whether publication should be after commit, same transaction, or explicitly best-effort |
| Closed-order alerts | `getClosedOrders` mutates orders from `closed` to `completed` during a read-like operation | Caching, retry, or UI refactoring can accidentally change order state | Rename/reshape as an explicit acknowledge operation |
| Direct/JPA parity | EJB/JPA and direct JDBC implementations are similar but not identical | Benchmark comparisons can mix framework cost with behavior drift | Add contract tests across runtime modes |
| REST item endpoint | Single-address GET can return null based on exact `Accept` handling | Normal clients may get surprising responses | Return explicit 404/406 or consistent representation handling |
| JMeter properties | README property names and JMX property lookup names can drift | Runs may silently use defaults | Align docs and JMX property conventions |
| Build tooling | Old Maven/Gradle plugins can fail on modern JDKs | Learners may diagnose environment failures as code failures | Pin toolchain or update plugins in a controlled build-modernization task |

The highest-priority defects are the ones that hide state transitions or corrupt comparison across runtime modes. Fixing a typo is less important than proving buy, sell, quote update, and order alert behavior are equivalent across implementations.

## Code Smells

Smells are not automatically bugs. They are structures that make future changes harder, especially for AI tools that tend to overgeneralize from local context.

### Mutable Static Control State

`TradeConfig` is the global control plane. It holds runtime mode, workload mix, page mapping, scale settings, cache intervals, primitive iteration counts, and tracing flags.

This is convenient for a benchmark UI, but risky for modernization:

- Behavior changes process-wide.
- Tests can leak state into each other.
- Thread-safety is unclear.
- Runtime mode changes can interact with the static `TradeAction` delegate.

Needed improvement: introduce an explicit configuration service or immutable runtime snapshot while preserving benchmark-adjustable settings during training.

### Business Logic in Multiple Places

The same user-visible behavior can be split across:

- `TradeAppServlet`.
- `TradeServletAction`.
- `TradeAction`.
- `TradeSLSBBean`.
- `TradeDirect`.
- JSP fragments.
- Filters.
- MDBs.

This is why broad modernization prompts are unsafe. A buy operation is not only in `buy`; quote update lives in the facade, alert mutation lives behind a filter-triggered read, and holding display depends on JSP attribute contracts.

Needed improvement: build behavior-level tests and introduce explicit application services before moving UI or persistence logic.

### JSPs as Service Clients

Quote and market-summary JSP fragments instantiate `TradeAction` directly. This weakens MVC boundaries, but it also supports cacheable and measurable fragments.

Needed improvement: preserve the fragment contract first, then move service calls behind view models or controller endpoints if the benchmark no longer needs JSP-level service access.

### Sentinel Values Instead of Explicit State

Sell-in-flight is represented by setting a holding purchase date to epoch. That is compact but obscure.

Needed improvement: introduce explicit holding status in a schema-aware migration. Until then, tests should treat the epoch value as meaningful domain behavior.

### Descriptor Drift

The repository carries Liberty, IBM, Geronimo, and JBoss-era descriptors and fallback JNDI names. Some are runtime-critical; others are historical residue.

Needed improvement: create a descriptor authority map. Mark each descriptor as active, legacy reference, or removable only after deployment tests prove it.

## Security and Operations Smells

DayTrader is a sample, but modernization learners should still name production risks clearly.

| Smell | Risk | Improvement |
| --- | --- | --- |
| Unauthenticated `/config` | Anyone with access can reset or recreate data | Restrict to admin-only local/dev profile or externalize operations |
| Plain sample passwords | Encourages unsafe credential handling | Treat credentials as seed data only; modernize auth separately |
| Placeholder credentials in server config | Bad production pattern | Move secrets to environment or secret store |
| Checked-in runtime state | Logs, transaction stores, deployed EARs pollute source | Separate generated server output from deployable config |
| Destructive DB setup in web app | Operational mistakes can destroy data | Replace with migrations and guarded seed tooling |
| App-level session auth only | No container or modern security integration | Add a security boundary as a dedicated modernization phase |

These should not all be fixed first. Security and operations improvements should be sequenced after the core behavior is characterized, unless the modernization goal is specifically to harden deployment.

## Performance and Benchmark Smells

Some smells affect measurement quality rather than user correctness.

- Static unsynchronized hit counters are approximate under concurrency.
- Primitive endpoints may measure more than their labels imply, such as context creation plus JNDI lookup.
- Scenario servlet throughput is not browser throughput because it uses server-side includes.
- REST and JSF primitives add stack coverage but not trading-domain coverage.
- Large fixed pool minimums stabilize benchmark behavior but distort small-machine resource use.
- Market summary considers a subset of generated symbols, so it is a benchmark market summary, not a complete exchange summary.

Needed improvement: document each benchmark’s measurement boundary and keep benchmark assertions separate from product assertions.

## Modernization Improvement Backlog

The improvements below are ordered for training value and risk control.

| Priority | Improvement | Why First or Later |
| --- | --- | --- |
| 1 | Add characterization tests for login, quote, buy, sell, alert, reset, and market summary | Locks down behavior before changing mechanisms |
| 2 | Add cross-runtime contract tests for EJB/JPA, direct JDBC, and session-to-direct paths | Protects the benchmark thesis |
| 3 | Revive and pin the build toolchain | Prevents environment noise during modernization |
| 4 | Create a resource and descriptor authority map | Makes runtime wiring explicit |
| 5 | Secure or isolate `/config` operations | Removes the highest operational risk |
| 6 | Introduce explicit order and holding state models | Replaces string/sentinel state safely |
| 7 | Separate view models from entities and JSP scriptlets | Enables UI modernization |
| 8 | Replace static runtime config with explicit configuration snapshots | Improves testability and concurrency reasoning |
| 9 | Rationalize DDL and migrations | Creates one schema source of truth |
| 10 | Define a real trading REST API only if needed | Avoids confusing the address-book sample with domain API design |

## How to Prompt AI Against This Chapter

A weak prompt asks for cleanup:

```text
Fix the code smells in DayTrader.
```

A strong prompt scopes one smell to one behavior:

```text
Analyze the sell workflow and propose a migration from epoch purchase-date
sentinel to explicit holding status. Include affected JSPs, TradeServices
methods, EJB/JPA implementation, direct JDBC implementation, schema changes,
and workload tests. Do not edit code yet.
```

The second prompt asks for evidence. It forces the model to respect both product behavior and benchmark comparability.

## Apply This

1. **Bug-Smell-Improvement Split** -> Prevents random cleanup from changing behavior -> Classify findings before fixing them -> Pitfall: treating every legacy pattern as an immediate defect.
2. **Behavior-First Bug Fixing** -> Focuses effort where state can be wrong -> Fix defects around order, holding, account, quote, and alert transitions first -> Pitfall: polishing low-risk style issues before correctness.
3. **Smell With Rationale** -> Preserves benchmark affordances until replaced -> Explain why a smell exists before removing it -> Pitfall: deleting measurement scaffolding because it looks impure.
4. **Improvement Backlog** -> Turns modernization into sequenced work -> Order changes by testability, risk, and training value -> Pitfall: combining build, UI, persistence, and security changes in one pass.
5. **Evidence Prompting** -> Makes AI output auditable -> Ask for affected files, behaviors, runtime modes, and tests -> Pitfall: accepting broad recommendations with no trace through the system.

