# Chapter 16: Database Bootstrap, Reset, and Workload State

Chapter 15 explained runtime resources. This chapter covers the data lifecycle: table creation, population, reset, and workload state. DayTrader is benchmarkable only if its database can be reset into a known shape.

For modernization learners, bootstrap code is not peripheral. It defines the initial conditions under which every workload and user journey is meaningful.

By the end, you should understand why the database setup is web-triggered, destructive, and direct-JDBC-oriented.

## Table Creation

The web module contains DDL scripts for Derby, DB2, and Oracle. The configuration servlet detects the database product, chooses a DDL resource, parses semicolon-delimited statements, and recreates tables.

```mermaid
flowchart TD
    Config[/config buildDBTables] --> Detect[Detect DB Product]
    Detect --> Pick[Pick DDL Script]
    Pick --> Parse[Parse Statements]
    Parse --> DropCreate[Drop and Create Tables]
    DropCreate --> Restart[Prompt Restart]
```

This is operationally convenient for a sample and dangerous for production. The endpoint can destroy data from the web UI.

## Configuration Servlet Actions

The configuration servlet is the operations console. Its `action` parameter chooses between display, update, reset, table creation, and data population.

```mermaid
flowchart TD
    Config[/config] --> Action{action}
    Action -->|none| Display[Show config.jsp]
    Action -->|updateConfig| Update[Mutate TradeConfig statics]
    Action -->|resetTrade| Reset[TradeAction.resetTrade(false)]
    Action -->|buildDBTables| Tables[Detect DB and recreate tables]
    Action -->|buildDB| Populate[TradeBuildDB / resetTrade(true)]
    Reset --> Stats[runStats.jsp]
    Tables --> Direct[TradeDirect schema operations]
    Populate --> Seed[Generated quotes users holdings]
```

This flow is why `/config` is an operations endpoint, not a normal user page. It changes the benchmark environment.

## Population

Population is generated through Java logic:

- Create quotes.
- Register users.
- Buy random holdings for users.
- Track errors and abort after repeated failures.

The data is not a static SQL seed. It is produced through the app’s own operations, which means seed data also exercises business logic.

```java
for each symbolNumber:
    trading.createQuote(symbol, company, price)

for each userNumber:
    trading.register(user, password, profile, openingBalance)
    repeat randomHoldingCount:
        trading.buy(user, randomSymbol(), quantity, synchronous)
```

This is slower than bulk SQL but better for testing whether the trading path can build a plausible world.

## Why Reset Uses Direct JDBC

In EJB mode, reset still drops into direct JDBC with normal trading transactions disabled or bypassed. That choice looks inconsistent until you separate operations from product behavior.

Reset has a different job:

- Delete or summarize large volumes of existing state.
- Recreate a predictable data population.
- Avoid entangling destructive setup with normal user transactions.
- Work even when the JPA business model is not the thing being tested.
- Produce run statistics for benchmark discipline.

The reset path is therefore a control surface for the benchmark. It should not be used as the model for user-facing data mutation.

## What Reset Does Not Mean

Reset is not a migration system. It is not safe production administration. It is not a reversible operation. It also does not mean all runtime state is clean: server logs, messaging stores, transaction logs, JVM caches, and warmed code paths live outside the trading tables.

Modernization should separate:

| Concern | Legacy DayTrader Mechanism | Modernization Direction |
| --- | --- | --- |
| Schema creation | Web-triggered DDL parsing | Versioned migrations |
| Seed data | Java-generated through services | Repeatable seed tool or fixture pipeline |
| Run stats | `RunStatsDataBean` after reset | Baseline validation report |
| Destructive access | Unauthenticated `/config` action | Admin-only external operation |

## Reset Stats

Reset returns run statistics: counts of users, quotes, holdings, orders, and related state. These stats are part of benchmark discipline. They confirm that a run starts from the expected scale.

Without reset discipline, performance comparisons are meaningless. A database full of completed orders and altered quote prices is not the same workload as a freshly populated one.

## DDL Drift

There are multiple DDL sources, and they are not perfectly identical. Some contain columns not used by active entity versioning. Some include OpenJPA sequence tables. This is normal legacy drift.

Modernization should pick one authoritative schema description and reconcile the rest. Do not begin by deleting “duplicates” until you understand which path each one serves.

## Checked-In Runtime State

The Liberty configuration tree contains runtime artifacts such as deployed EARs, logs, messaging stores, and transaction logs. That makes local startup easier to inspect, but it is not a clean source repository practice.

For training, it demonstrates what an app server creates. For modernization, it should become generated output.

## Apply This

1. **Known-State Bootstrap** -> Makes workloads comparable -> Provide repeatable schema and seed steps -> Pitfall: benchmarking against unknown leftover data.
2. **Behavioral Seeding** -> Exercises app rules while creating data -> Seed through services when business invariants matter -> Pitfall: using bulk SQL that bypasses required side effects.
3. **Destructive Operation Guard** -> Prevents accidental data loss -> Move reset/build actions behind explicit admin controls -> Pitfall: preserving sample convenience in production.
4. **Schema Authority Choice** -> Reduces DDL drift -> Select one source of schema truth before migration -> Pitfall: reconciling by guesswork.
5. **Runtime Output Boundary** -> Cleans repository structure -> Separate deployable config from generated logs/stores/apps -> Pitfall: committing stateful server artifacts into source control.
