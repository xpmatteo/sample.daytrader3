# Phase 2: Audience and Positioning

## Primary Audience

This book serves three readers at once:

- Technical leaders who want to understand why DayTrader is shaped this way: its module boundaries, benchmark intent, runtime-mode strategy, transaction posture, deployment model, and where the design trades purity for measurement.
- Senior engineers who want implementation-level understanding: how servlet includes, JSP fragments, EJBs, JPA entities, direct JDBC, JMS MDBs, Liberty bindings, and benchmark primitives cooperate under load.
- AI-assisted modernization learners who will use the repository as a training ground. They need the trading application explained as a complete legacy system: user journeys, business invariants, persistence state, UI coupling, runtime configuration, and modernization hazards.

The reader should already understand Java web applications, HTTP sessions, relational persistence, and basic enterprise Java terminology. The book should not teach Java EE from first principles. It should teach how a concrete Java EE application works as a trading system and how that system is also shaped to expose architectural cost.

## Core Thesis

DayTrader is a full legacy trading application that doubles as a controlled measurement instrument. Its central architectural bet is that one stable business contract can carry real user workflows while being driven through multiple runtime paths: EJB/JPA, direct JDBC, EJB-wrapped direct JDBC, synchronous order completion, asynchronous JMS completion, JSP fragments, JSF primitives, REST primitives, and workload generators. Every major subsystem serves either the trading loop, the comparability of implementations, or the isolation of one Java EE layer for measurement.

## What Makes It Worth a Book

- The source shows mechanisms but not narrative. It does not explain that apparent impurities are often benchmark affordances.
- The cross-cutting pattern is scattered: the same operation is intentionally implemented through several stacks so engineers can compare overhead and behavior.
- The rationale is mostly implicit: mutable static config, JSP-side service calls, direct JDBC beside JPA, server-side scenario includes, and unauthenticated reset endpoints look wrong unless viewed through the benchmark thesis.
- The transferable lessons are valuable beyond Java EE: build a stable service contract, create alternate implementations for measurement, isolate marginal costs, make runtime modes explicit, and keep deployment resources visible enough to reason about the whole system.

# Phase 3: Proposed Book Structure

## Working Title

**DayTrader EE6: Modernizing a Trading System Built for Measurement**

## Part I: The Benchmark Contract

*A system built for comparison must first make its behaviors comparable.*

### Chapter 1: Reading DayTrader as an Instrument

- Establishes the book thesis: DayTrader is both a real trading workflow and a benchmark harness.
- Explains the five modules, EAR shape, Liberty runtime, and why modernization learners must separate domain behavior from benchmark scaffolding.
- Introduces the recurring tension between clean architecture, legacy compatibility, and measurable architecture.

### Chapter 2: The Stable Surface: `TradeServices`, `TradeAction`, and Runtime Modes

- Covers the service contract that keeps EJB/JPA, direct JDBC, and EJB-wrapped JDBC comparable.
- Explains `TradeAction` as facade, runtime strategy selector, JNDI lookup point, and cache owner.
- Analyzes the cost and risk of mutable static configuration and shared service delegates.

### Chapter 3: Data as the Common Currency

- Explains the entity/DTO model: accounts, profiles, quotes, holdings, orders, market summaries, and run stats.
- Shows why entities are both persistence records and display-friendly data beans.
- Covers key generation, named queries, relationship fetch choices, transient compatibility fields, and commented optimistic locking.

## Part II: The Trading Core

*The core loop turns a user action into state change, market movement, and measurable work.*

### Chapter 4: Login, Home, Portfolio, and Quote Lookup

- Traces the user-facing trading shell: login, authenticated session state, home page, account summary, portfolio display, and quote lookup.
- Explains how the same workflows move through servlet actions, service contract, JPA/direct JDBC, and JSP rendering.
- Covers modernization-relevant coupling: session keys, request attributes, lazy relationship inflation, JSP-side service calls, and invalid-symbol behavior.

### Chapter 5: Buy and Sell as Order State Machines

- Builds the core trading write path as a domain state machine: create order, debit/credit account, mark holdings, complete or queue, update quote, and alert the user.
- Explains account, order, holding, and quote invariants that modernization work must preserve.
- Surfaces subtle design choices: balance changes before completion, epoch timestamps for in-flight sells, cancelled-as-completed, and closed-order alerts mutating state.

### Chapter 6: Market Movement and Summary Caching

- Explains the market side of the trading app: quote price/volume update, pessimistic locking, penny-stock recovery, max-price safeguards, and quote publication.
- Shows market summary computation and the time-window cache that prevents every request from recomputing it.
- Compares EJB/JPA and direct JDBC implementations where behavior is parallel but not identical, highlighting modernization regression risks.

## Part III: Enterprise Boundaries

*Enterprise code is mostly about who owns transactions, resources, and side effects.*

### Chapter 7: The EJB/JPA Implementation

- Covers `TradeSLSBBean` as the transactional boundary around `EntityManager`, JMS resources, and business operations.
- Explains container-managed transactions, self-invocation avoidance via business proxy, `REQUIRES_NEW` publication, and `NOT_SUPPORTED` reset.
- Discusses entity-manager usage patterns, named/native queries, and where the EJB path optimizes for container-managed comparability.

### Chapter 8: The Direct JDBC Shadow System

- Explains `TradeDirect` as a parallel implementation, not a shortcut.
- Covers datasource lookup, connection lifecycle, SQL mirroring, manual commit/rollback, `UserTransaction`, and shared key generation.
- Shows how `DirectSLSBBean` wraps direct JDBC inside EJB transactions to isolate EJB invocation overhead from JPA overhead.

### Chapter 9: Asynchronous Work with JMS and MDBs

- Traces `queueOrder`, `DTBroker3MDB`, direct-vs-EJB dispatch, rollback behavior, and MDB timing stats.
- Explains quote streaming through `TradeStreamerTopic` as instrumentation rather than user-facing market data.
- Covers nonpersistent JMS resources, activation specs, two-phase intent, and redelivery decisions.

## Part IV: Web Surfaces and Workload Generation

*A benchmark needs users, but not every user has to be human.*

### Chapter 10: The Servlet/JSP Application Shell

- Explains `/app`, `TradeServletAction`, request/session attributes, page selection, includes, and error handling.
- Shows how the UI deliberately mixes controller-managed data with JSP-side service calls.
- Covers image-heavy JSP variants, closed-order alert filter, app-level authentication, and exposed configuration/reset endpoints.

### Chapter 11: Scenario Traffic and Primitive Endpoints

- Explains `TradeScenarioServlet` as a server-side workload generator and how it chains includes.
- Classifies primitive endpoints by layer: static, servlet, JSP, session, JNDI, JDBC, EJB, JPA, JMS, JSF, REST, two-phase.
- Shows the differential-baseline method: compare adjacent primitives to infer marginal container overhead.

### Chapter 12: JSF at the Edge of the Benchmark

- Covers JSF Facelets as workload primitives rather than primary UI.
- Explains request-scoped managed beans, runtime-mode service selection, Facelets rendering, and JSF performance tuning.
- Uses JSF as an example of adding UI-stack coverage without rewriting the trading application shell.

### Chapter 13: The REST WAR That Is Not a Trading API

- Explains the address-book REST module, its in-memory model, JAX-RS wiring, media-type quirks, and context-root packaging.
- Makes the non-integration explicit: no REST endpoint calls `TradeAction`, `TradeServices`, JPA entities, or JMS trading flows.
- Shows how modernization learners should avoid mistaking co-packaged samples for domain APIs.

## Part V: Deployment as Architecture

*The runtime is part of the design; bindings and pools are not incidental details.*

### Chapter 14: Building the EAR and Its Liberty World

- Explains Maven/Gradle module topology, final artifact names, EAR module mapping, and Liberty plugin/copy tasks.
- Covers provided APIs, REST dependency-scope mismatch, old build-tool risks, and checked-in deployable artifacts.
- Shows the lifecycle from build to feature install to server start to database setup.

### Chapter 15: Resources, Descriptors, and the Server Contract

- Explains `server.xml`, JDBC pools, Derby embedded database, JTA/non-JTA datasources, JMS queue/topic resources, and activation specs.
- Connects web/EJB descriptors and IBM bindings to runtime JNDI names.
- Discusses legacy Geronimo/JBoss descriptors as portability history and reasoning cost.

### Chapter 16: Database Bootstrap, Reset, and Workload State

- Covers destructive table creation, DDL variants, Java-generated seed data, users/quotes/holdings, and reset stats.
- Explains why reset uses direct JDBC outside JPA/EJB transactions and why benchmark runs need state discipline.
- Discusses DDL drift, checked-in runtime state, and operational risks in sample code.

## Part VI: Lessons, Trade-offs, and Transfer

*The patterns worth stealing are rarely the cleanest-looking parts of the code.*

### Chapter 17: Performance Thinking Without Premature Optimization

- Extracts the benchmark design method: stable contract, alternate implementations, primitive probes, warm-up, reset, and controlled workload mix.
- Explains what DayTrader measures well and what it distorts, including scenario servlet vs JMeter realism.
- Covers static counters, primitive iteration, long-run mode, caching knobs, and how to avoid fooling yourself.

### Chapter 18: Modernization Patterns You Can Reuse

- Synthesizes transferable patterns for AI-assisted modernization: domain invariant maps, comparable service surfaces, runtime strategy switches, transaction-boundary experiments, instrumentation endpoints, and explicit deployment contracts.
- Calls out anti-patterns to remove or contain in production: unauthenticated reset, mutable static config, descriptor drift, checked-in runtime output, weak MVC boundaries where no benchmark rationale exists.
- Reconnects each subsystem to the core thesis and gives a forward-looking view of how to modernize the trading app without destroying its measurement value.

## Proposed Chapter Dependencies

- Chapters 1-3 define the system, service surface, and data model.
- Chapters 4-6 explain the main business loop.
- Chapters 7-9 explain implementation variants and enterprise side effects.
- Chapters 10-13 explain user and workload surfaces built on the core.
- Chapters 14-16 explain runtime infrastructure once the reader understands what it supports.
- Chapters 17-18 synthesize performance method and transferable modernization architecture.

## Approved Output Format

- The trading application will be explained in full because the codebase will be used as a training ground for AI-assisted modernization learners.
- REST is split into its own chapter.
- The manuscript will be written one file per chapter under `docs/daytrader-book/chapters/`.
