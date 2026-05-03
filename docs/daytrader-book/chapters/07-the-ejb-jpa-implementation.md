# Chapter 7: The EJB/JPA Implementation

Chapter 6 covered market behavior. This chapter drops one layer lower and studies the main implementation behind that behavior: the stateless EJB backed by JPA and JMS resources. If `TradeServices` is the contract, `TradeSLSBBean` is the canonical Java EE realization of that contract.

For modernization learners, this chapter is about boundaries. The bean owns transactions, persistence context access, resource injection, and several business operations. Replacing it with a modern service class is possible, but only after understanding which responsibilities come from the domain and which come from the container.

By the end, you should know how DayTrader uses EJB as an architectural boundary, not just as a framework annotation.

## The Bean as Transaction Boundary

The main trading bean is stateless, container-managed, and transaction-required by default. That gives every normal service method a transaction unless it opts out.

```mermaid
graph TD
    App[/app Servlet] --> Action[TradeAction]
    Scenario[/scenario] --> App
    Prims[Primitive Servlets] --> Action
    JSF[JSF Facelets] --> Services
    REST[REST WAR Address Sample] --> AddressOnly[In-Memory Address Store]
    Action --> Services[TradeServices]
    Caller[Web or MDB Caller] --> Bean[Stateless Trading Bean]
    Services --> Bean
    Services --> Direct[TradeDirect]
    Services --> Wrapper[DirectSLSBBean]
    Wrapper --> Direct
    Bean --> Tx[Container Transaction]
    Tx --> EM[Persistence Context]
    Tx --> JMS[JMS Resources]
    EM --> DB[(Database)]
    JMS --> Queue[Queue]
    JMS --> Topic[Topic]
    Queue --> BrokerMDB[Broker MDB]
    Topic --> StreamerMDB[Streamer MDB]
```

This is the classic enterprise shape: business methods are where persistence and messaging become one unit of work. The code relies on the container for transaction demarcation, exception handling, resource injection, and persistence-context lifecycle.

## Injected Resources

The bean consumes four kinds of runtime resources:

| Resource | Purpose |
| --- | --- |
| `EntityManager` | JPA persistence for accounts, profiles, quotes, holdings, orders |
| Queue connection factory and queue | Async order completion |
| Topic connection factory and topic | Quote update publication |
| Session context | EJB metadata, rollback, and business proxy access |

The session context is especially important because the bean uses it to call itself through a business proxy for quote publication. That is not stylistic. It is how the code ensures transaction metadata applies.

## Method Categories

The bean has several categories of methods:

- User workflow methods: login, logout, account/profile, holdings, quotes.
- Trading mutation methods: buy, sell, complete order, cancel order.
- Market methods: quote update, market summary, quote publication.
- Benchmark methods: investment return and two-phase ping.
- Operational method: reset trade.

Those categories should not be flattened during modernization. Product behavior, probes, and operations have different security and transaction expectations.

## Transaction Attribute Choices

Most methods run under the default required transaction. Two choices stand out:

- Reset is not supported by the current transaction and delegates to direct JDBC.
- Quote publication requires a new transaction.

```java
transaction(required):
    updateQuote()
    proxy.publishQuoteEventInNewTransaction()

transaction(notSupported):
    directJdbcReset(deleteData)
```

The reset choice keeps destructive setup outside the normal JPA business model. The publication choice isolates the event send from the surrounding quote update, but with a caveat: because publication runs in a separate transaction, a quote-change message can be published even if the surrounding quote update later rolls back. The code comments acknowledge this awkwardness. Whether the choice is ideal is less important than recognizing it as an intentional runtime boundary with observable consequences.

## Persistence Usage

The EJB path mostly uses `EntityManager.find` for direct lookup and named queries for collections:

- Find profile by user ID.
- Navigate from profile to account.
- Find quote by symbol.
- Query holdings by user ID.
- Query closed orders by status and user ID.
- Query quotes ordered by change for market summary.

The code sometimes touches relationships before returning data to the web layer. That is a pragmatic response to JSP rendering outside the bean method.

## Native Query as Escape Hatch

Quote update uses a native `for update` query. This is the moment where pure JPA abstraction yields to database behavior. Under load, the quote row is a shared mutable object. The code wants pessimistic serialization.

A modernization should preserve the locking behavior even if the persistence mechanism changes.

## Deep Dive: Self-Invocation and Business Proxies

EJB transaction annotations do not apply to ordinary self-invocation. If a bean method calls another method on `this`, the container does not intercept the call.

DayTrader avoids that for quote publication:

```java
proxy = context.businessObject(ServiceInterface)
proxy.publishEvent(change)
```

This pattern is easy for AI tools to erase because a direct method call looks simpler. In modernization, replace the mechanism only if you replace the transaction boundary too.

## Apply This

1. **Container Responsibility Map** -> Shows what framework services the bean relies on -> List transactions, resources, proxies, and lifecycle before migration -> Pitfall: converting annotations to plain methods without replacements.
2. **Method Category Split** -> Separates product, probe, and operations code -> Classify service methods by intent -> Pitfall: applying one security or transaction policy to all.
3. **Persistence Inflation Rule** -> Preserves JSP compatibility -> Identify relationship touches before returning entities -> Pitfall: returning lazy objects to views after transaction closure.
4. **Native Escape Audit** -> Finds places abstraction was insufficient -> Preserve database-specific semantics intentionally -> Pitfall: replacing `for update` with a normal ORM read.
5. **Proxy Boundary Preservation** -> Keeps interceptor behavior intact -> Replace self-proxy patterns with explicit service boundaries -> Pitfall: simplifying calls and losing transaction attributes.
