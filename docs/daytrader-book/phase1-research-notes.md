# Phase 1 Research Notes

These are raw subsystem notes for the DayTrader EE6 technical book. They are research material, not final manuscript prose.

## EJB, Domain, Persistence, and Trading Services

### Architecture and Boundaries

- `daytrader3-ee6-ejb` owns the business service contract, JPA domain model, EJB/JPA implementation, direct JDBC implementation, JMS message-driven beans, utility code, persistence descriptors, and EJB bindings.
- Main packages:
  - `com.ibm.websphere.samples.daytrader`: service interfaces, facade, configuration, entities/DTOs.
  - `com.ibm.websphere.samples.daytrader.ejb3`: stateless session beans and MDBs.
  - `com.ibm.websphere.samples.daytrader.direct`: direct JDBC/JMS implementation.
  - `com.ibm.websphere.samples.daytrader.util`: logging, financial math, timing, key-block helpers.
- `TradeServices` is the central contract. `TradeSLSBLocal` and `DirectSLSBLocal` extend it for local EJB access.
- `TradeAction` is the client-side facade used by the web layer and SOAP wrapper. It selects a runtime implementation from static `TradeConfig`.

### Key Abstractions

- `TradeServices`: operations for market summary, buy/sell, quote operations, holdings, account/profile, login/logout, registration, order queue/completion/cancel, reset.
- `TradeAction`: runtime-mode switch, shared service delegate cache, market summary cache.
- `TradeSLSBBean`: full EJB3/JPA implementation with container-managed transactions, JPA `EntityManager`, JMS queue/topic resources, and a `SessionContext`.
- `DirectSLSBBean`: stateless EJB wrapper that delegates every call to `new TradeDirect(true)`.
- `TradeDirect`: direct JDBC/JMS implementation of the same service API, with manual connection handling and optional global transaction participation.
- Domain/JPA entities:
  - `AccountProfileDataBean`: profile keyed by user ID.
  - `AccountDataBean`: account state, balance, login/logout counters, profile, orders, holdings.
  - `QuoteDataBean`: stock quote, price, volume, high/low/open/change.
  - `HoldingDataBean`: user-owned position.
  - `OrderDataBean`: buy/sell order and status.
- DTOs: `MarketSummaryDataBean`, `MarketSummaryDataBeanWS`, `RunStatsDataBean`.

### Data Flow

- Login: servlet reads credentials -> `TradeServletAction` -> `TradeAction.login` -> selected `TradeServices.login` -> account/profile lookup -> password check -> account counters update -> web session receives `uidBean`.
- Home/portfolio: web action calls account and holdings services; portfolio additionally fetches quote data per holding. Market summary is intentionally fetched from JSP fragments, not the controller.
- Quote: controller dispatches to JSP; `displayQuote.jsp` creates `TradeAction` and calls `getQuote`. Invalid symbols return an "Invalid symbol" quote object rather than throwing.
- Buy: web action -> `TradeAction.buy` -> implementation creates open buy order, debits account immediately, completes synchronously or queues asynchronously, then `TradeAction` updates quote price/volume.
- Sell: implementation creates sell order, marks holding in-flight by setting purchase date to epoch, credits account immediately, completes synchronously or queues asynchronously, then quote update runs unless order was cancelled.
- Async order completion: `queueOrder` sends JMS message to `TradeBrokerQueue`; `DTBroker3MDB` receives `neworder`, chooses EJB or direct implementation from message property, calls `completeOrder`, and records timing.
- Quote streaming: quote update publishes to `TradeStreamerTopic` in a new transaction; `DTStreamer3MDB` consumes and records/logs timing only.
- Market summary: `TradeAction` uses a time-window cache; EJB implementation computes summary from a named query over a subset of quote symbols.

### Patterns

- Service interface shared across implementations to compare EJB/JPA, direct JDBC, and EJB-wrapped JDBC.
- Runtime strategy selected by mutable static config.
- EJB session facade centralizes transaction and resource integration.
- Direct implementation mirrors service API to isolate container overhead.
- Message-driven worker decouples order submission and completion in async mode.
- Time-window cache prevents all callers from recomputing an expensive market summary.
- Pessimistic quote update uses `for update` native query / SQL.
- Table-based key generation uses shared `keygenejb` block allocation.
- SOAP compatibility layer converts collections into arrays.

### Surprising Decisions

- `TradeAction.trade` is static and mutable across all facade instances.
- Buy/sell adjust account balance at order creation, even though comments imply completion should do it.
- Sell uses epoch purchase date as an in-flight marker instead of an explicit holding status.
- `completeOrder` dereferences `order` before checking for null.
- `OrderDataBean.isCompleted()` treats cancelled orders as completed.
- `TradeSLSBBean.orderCompleted` is unsupported, while completion calls a new `TradeAction().orderCompleted(...)` no-op hook.
- Closed-order retrieval mutates status from `closed` to `completed`.
- Entity `@Version` fields are commented out while some DDL contains `optLock`.
- Direct SQL and JPA paths are intentionally parallel but behavior can drift.
- REST is packaged with the EAR but does not expose trading services.

## Web UI, Controllers, JSP, JSF, and Configuration

### Architecture and Boundaries

- `daytrader3-ee6-web` owns the main user interface, servlet controllers, JSP/JSF views, benchmark primitive web endpoints, configuration/reset UI, DB DDL scripts, and web descriptors.
- `TradeAppServlet` at `/app` is a parameter-dispatch front controller.
- `TradeServletAction` adapts HTTP/session/request attributes to `TradeAction`.
- `TradeScenarioServlet` at `/scenario` generates server-side benchmark traffic by including `/app?action=...`.
- `TradeConfigServlet` at `/config` mutates runtime static configuration and runs reset/table-build/populate operations.
- `OrdersAlertFilter` checks for closed orders on `/app` requests and exposes `closedOrders`.
- `TradeWebContextListener` initializes `TradeDirect`.

### Key Abstractions

- Session key `uidBean` is the app-level authentication flag.
- Request attributes include `accountData`, `accountProfileData`, `holdingDataBeans`, `quoteDataBeans`, `orderData`, `closedOrders`, `tradeConfig`, `runStatsData`, `results`, and `status`.
- JSP sets:
  - Plain trading views: `welcome.jsp`, `tradehome.jsp`, `account.jsp`, `portfolio.jsp`, `quote.jsp`, `displayQuote.jsp`, `order.jsp`, `register.jsp`, `config.jsp`, `runStats.jsp`.
  - Image-heavy variants selected by `TradeConfig.webInterface`.
- JSF/Facelets exist as benchmark primitives, not primary UI: `PingFaceletSmall.xhtml`, `PingFaceletLarge.xhtml`, `QuoteBean`, `AccountBean`.

### Data Flow

- `/app?action=login`: credentials -> `TradeAction.login` -> session state -> home page data.
- `/app?action=home`: account and holdings -> `tradehome.jsp`; market summary fetched inside JSP fragment.
- `/app?action=portfolio`: holdings -> quote lookup per holding -> `portfolio.jsp`.
- `/app?action=quotes`: dispatches without controller quote lookup; JSP fragments call service.
- `/app?action=buy` / `sell`: parse inputs -> service call -> `order.jsp`.
- `/app?action=account`: account/profile/orders unless long-run mode skips orders.
- `/scenario`: picks action from workload mix, internally includes `/app` actions, sometimes depends on request attributes from earlier includes in the same response.
- `/config`: renders or updates runtime configuration; can reset, recreate tables, and populate database.

### Patterns

- Front controller plus procedural action helper.
- Server-side include is the primary composition mechanism, not forward/redirect.
- JSP fragments deliberately call services to support edge-cache and benchmark scenarios.
- Mutable static runtime config makes the benchmark adjustable without redeploying.
- App-level auth avoids container security to keep benchmark dimensions explicit.
- Vendor descriptor set preserves WebSphere/Geronimo/JBoss portability history.

### Surprising Decisions

- MVC boundaries are intentionally weak: quote and market-summary lookups are in JSP fragments.
- `/config`, `/scenario`, primitive endpoints, reset, and DB build are unauthenticated.
- Runtime config is process-local static memory and resets on restart.
- JSF is present only as a primitive workload.
- Forms use old parameter names with spaces and mixed case.
- Some catch paths include one page and then continue to include another.
- `TradeDirect.destroy()` is commented out on context shutdown.
- Several JSP sections duplicate alert/navigation markup.

## Benchmark Primitives and Workload Harness

### Architecture and Boundaries

- Primitive endpoints are a layered measurement matrix, not application features.
- They isolate static serving, servlet dispatch, response writers, include/forward, JSP/EL, sessions, JNDI, JDBC, EJB, JPA, JMS, JSF, REST, and two-phase resource coordination.
- `web_prmtv.html` catalogs primitives for interactive access.
- `jmeter_files/daytrader3.jmx` drives both realistic trading flows and selected primitive-like endpoints.

### Taxonomy

- Static/raw: `PingHtml.html`, `PingServlet`, `PingServletWriter`, `PingServletSetContentLength`, `PingServlet2PDF`, `ExplicitGC`.
- Dispatch/JSP: `PingServlet2Include`, `PingServlet2Servlet`, `PingJsp.jsp`, `PingJspEL.jsp`, `PingServlet2Jsp`, `quoteDataPrimitive.jsp`.
- Session: `PingSession1`, `PingSession2`, `PingSession3`.
- JDBC/JNDI: `PingServlet2DB`, `PingJDBCRead`, `PingJDBCRead2JSP`, `PingJDBCWrite`, `PingServlet2JNDI`.
- JSF: `PingFaceletSmall.jsf`, `PingFaceletLarge.jsf`.
- EJB/JPA/JMS: session EJB pings, entity pings, collection/relationship pings, direct-JDBC-through-EJB pings, queue/topic MDB pings, two-phase ping.
- REST: `/rest/addresses` is included as a lightweight JAX-RS sample endpoint.

### Data Flow

- Servlet/JSP primitives exercise request mapping, attributes, include/forward, and rendering.
- JDBC primitives instantiate `TradeDirect`, acquire datasource connections, read/update quotes, and optionally include JSP rendering.
- EJB/JPA primitives inject local EJBs or `EntityManager` and isolate container invocation, persistence context, and relationship traversal.
- JMS primitives send messages to queue/topic resources and rely on MDB consumption for timing side effects.
- JSF primitives route through `FacesServlet`, request-scoped beans, runtime-mode service selection, and Facelets rendering.
- JMeter drives `/daytrader/app` with cookies, assertions, think time, regex extraction for holdings, plus JSF and JAX-RS calls.

### Patterns

- Differential baselines: compare adjacent layers to estimate marginal overhead.
- Primitive iteration reduces web-container overhead per measured lower-layer operation.
- Warm-up and reset discipline make benchmark data less noisy.
- Scenario servlet is convenient but less realistic than JMeter because actions are server-side includes.
- Primitive endpoints bypass global runtime modes when they need to isolate a specific stack.

### Surprising Decisions

- Static unsynchronized counters are approximate under concurrency.
- Some labels are stale from earlier Java EE terminology.
- `PingServlet2DB` appears to acquire a connection without visibly closing it in that servlet path.
- JNDI primitive measures context construction plus lookup.
- JMeter README property names do not perfectly match the JMX property lookups.
- JMS primitives are explicitly not meant as performance tests, even though they collect timing stats.

## REST Sample

### Architecture and Boundaries

- `daytrader3-ee6-rest` is a standalone WAR packaged into the EAR at context root `/rest`.
- It is not a trading API. It exposes a small in-memory address-book sample used as a JAX-RS workload primitive.
- `AddressApplication` registers `AddressBook`, while `web.xml` maps a JAX-RS application servlet to `/*`.

### Key Abstractions

- `AddressBook`: root resource at `/addresses`.
- `Address`: JAXB DTO and subresource with its own `@GET`.
- `AddressList`: mutable list wrapper for collection responses.
- `AddressBookDatabase`: static `HashMap` mock database.
- `ObjectFactory`: JAXB-style factory.

### Data Flow

- `GET /rest/addresses`: creates `AddressList`, copies all static map values, produces JSON.
- `GET /rest/addresses/search/{searchstring}`: prefix filter by entry name, produces JSON.
- `GET /rest/addresses/{entryName}`: root resource locator returns an `Address`; the `Address` subresource returns XML only if `Accept` contains `text/xml`.

### Patterns

- Mock repository for lightweight endpoint behavior.
- JAXB DTOs with container-provided JSON/XML serialization.
- Subresource locator pattern where model object also acts as resource.
- Benchmark primitive packaged beside, not integrated into, the domain system.

### Surprising Decisions

- No endpoint calls `TradeAction`, `TradeServices`, JPA entities, or JMS.
- Collection endpoints are JSON-only; item endpoint is XML-only.
- Missing entries have no explicit 404 path.
- `Accept: */*` may not satisfy the exact XML media check.
- Static `HashMap` is unsynchronized and unordered.

## Build, Packaging, Deployment, and Runtime Configuration

### Architecture and Boundaries

- Maven and Gradle describe the same five modules: EJB, web, REST, EAR, Liberty configuration.
- Maven appears more complete; Gradle mirrors packaging but uses older APIs and no wrapper.
- EAR descriptor packages `web.war` at `/daytrader`, `dt-ejb.jar`, and `Rest.war` at `/rest`.
- Liberty config module contains deployable server configuration and checked-in runtime artifacts.

### Key Build and Runtime Artifacts

- Root Maven aggregator: `pom.xml`.
- Gradle topology: `settings.gradle`, root `build.gradle`, module builds.
- EAR assembly: `daytrader3-ee6/src/main/application/META-INF/application.xml`.
- Liberty server: `daytrader3-ee6-wlpcfg/servers/daytrader3_Sample/server.xml`.
- EJB persistence/bindings: `persistence.xml`, `ibm-ejb-jar-bnd.xml`.
- Web refs/bindings: `web.xml`, `ibm-web-bnd.xml`, `ibm-web-ext.xml`.
- DB DDL: web `dbscripts/{derby,db2,oracle}/Table.ddl`; EJB `META-INF/daytrader.sql`.

### Integration Points

- Liberty features: EJB Lite, JSF, JAX-RS, JPA, JMS MDB, WAS JMS server/client.
- Derby embedded datasource has both JTA and non-JTA variants.
- JMS queue/topic resources wire to EJB resource refs and MDB activation specs.
- Web descriptor declares datasource/JMS/EJB refs; IBM bindings map them to Liberty resources.
- Maven EAR module copies Derby and EAR into the Liberty user directory.
- JMeter workload assumes app at `localhost:9083/daytrader` by default.

### Operational Flow

- Build EAR.
- Set `WLP_USER_DIR` to the repo Liberty config directory.
- Install required Liberty feature/package.
- Start server.
- Browse `/daytrader`.
- Use configuration UI to recreate tables, populate data, restart.
- Run JMeter or scenario/primitive endpoints.

### Surprising Decisions

- Checked-in Liberty config includes runtime outputs such as deployed EAR, Derby log, messaging store, and transaction logs.
- `.gitignore` appears to miss the actual runtime directory name.
- Maven WAR plugin is old and may fail on modern Java runtimes.
- Maven and Gradle dependency scopes differ for REST JAX-RS API.
- Server uses large fixed JDBC pool minimums.
- DB initialization is destructive and web-triggered rather than deployment-automated.
- DDL sources are not identical.
- Docs conflict in places with actual EE6 feature set.

