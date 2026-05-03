# Editorial Review Action Plan

## Priority 1: Make the Trading App Concrete

- Add a user-facing trading walkthrough early so learners see pages, state changes, orders, holdings, quote updates, and alerts as one story.
- Add an app navigation diagram.
- Add a behavioral invariants table covering login, buy, sell, quote update, closed-order alerts, invalid symbols, and reset.
- Fix the buy-flow diagram so `TradeAction` is visible as the owner of the quote update side effect.

## Priority 2: Strengthen Shared Maps

- Clarify in Chapter 2 that `TradeAction` is not just routing; it owns market-summary caching and post-trade quote updates.
- Add a runtime-mode matrix for EJB3, DIRECT, SESSION3, sync, and async two-phase behavior.
- Add a cross-implementation topology diagram showing web, scenario, primitives, JSF, REST, `TradeAction`, `TradeServices`, EJB/JPA, direct JDBC, JMS, and MDBs.
- Normalize terminology around service contract, runtime mode, product behavior, benchmark primitive, operations endpoint, and historical descriptor.

## Priority 3: Fix Accuracy and Missing Implementation Detail

- Add the quote-publication caveat: `REQUIRES_NEW` can publish a quote-change message even if the surrounding quote update later rolls back.
- Expand the direct JDBC transaction explanation into standalone direct, EJB-wrapped direct, and direct async two-phase cases.
- Make the alert filter’s hidden mutation explicit: `getClosedOrders` moves orders from `closed` to `completed`.
- Split Chapter 11’s primitive matrix by surface/module rather than treating JSF and REST as one layer.
- Expand Chapter 12 with actual Facelets, bean classes, URL mapping, and runtime-mode lookup behavior.
- Repeat the REST non-domain boundary immediately after the endpoint table.

## Priority 4: Expand Deployment and Operations Chapters

- Expand Chapter 14 with concrete Maven/Gradle evidence, artifact names, copy behavior, Liberty lifecycle, `WLP_USER_DIR`, and database setup sequence.
- Expand Chapter 15 with exact Liberty feature names and a resource-resolution ladder from Java/descriptors to `server.xml`.
- Expand Chapter 16 with `config` actions, `resetTrade`, `buildDB`, `buildDBTables`, DDL selection, seed behavior, and why reset delegates to direct JDBC.
- Expand Chapter 17 with DayTrader-specific measurement examples and a controlled modernization run.
- Replace Chapter 18’s Gantt with a modernization decision table and add missing patterns for runtime strategy switches, transaction-boundary experiments, and instrumentation endpoints.

## Priority 5: Editorial Tightening

- Reduce repeated generic “benchmark vs bad code” warnings where later chapters can use shorter local references.
- Vary openings and `Apply This` sections enough to avoid mechanical repetition.
- Keep REST’s distinction consistent: packaged in the EAR, not a trading API.

