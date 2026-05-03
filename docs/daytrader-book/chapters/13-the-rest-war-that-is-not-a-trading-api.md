# Chapter 13: The REST WAR That Is Not a Trading API

Chapter 12 explained JSF as an edge primitive. REST is another edge, but with an even sharper warning: the REST module is not a trading API. It is a small address-book sample packaged into the same EAR to exercise JAX-RS.

For modernization learners, this is a test of architectural reading. Co-packaging does not imply domain integration. A model that sees `/rest` and assumes it should replace `/app` will misunderstand the system.

By the end, you should know exactly what the REST WAR does and does not do.

## Shape of the Module

The REST WAR contains:

- A JAX-RS application class.
- One address-book resource.
- Address and address-list JAXB objects.
- A static in-memory map acting as a mock database.
- A web descriptor mapping JAX-RS to the WAR.

```mermaid
graph TD
    RestWar[Rest.war at /rest] --> JAXRS[JAX-RS Runtime]
    JAXRS --> AddressBook[/addresses Resource]
    AddressBook --> StaticMap[Static AddressBookDatabase]
    StaticMap --> Address[Address DTOs]
```

No class in this module calls the trading service, entities, JMS resources, or database.

## Endpoints

| Endpoint | Behavior |
| --- | --- |
| `GET /rest/addresses` | Return all static addresses as JSON |
| `GET /rest/addresses/search/{term}` | Return addresses whose entry name starts with the term as JSON |
| `GET /rest/addresses/{entry}` | Return one address through a subresource path, XML-oriented |

The endpoint set is intentionally tiny. It exists to put JAX-RS into the deployed application and workload plan.

The endpoint table is also the boundary: none of these URLs logs in a trader, reads an account, returns holdings, places orders, updates quotes, or touches JMS. A trading REST API would have to be designed from `TradeServices`, not inferred from this address-book sample.

## Model and Binding

The address model uses JAXB annotations. JSON serialization is left to the container/provider. The list wrapper exposes a mutable backing list. The static map is unordered and unsynchronized.

```java
list = new addressList()

for each address in addressDatabase.values():
    list.add(address)

return list
```

That is adequate for a primitive. It is not a persistence or API design pattern for the trading system.

## Media-Type Quirks

The collection endpoints produce JSON. The single-address subresource expects XML-oriented negotiation and may return null if the acceptable media list does not literally contain the expected XML media type.

This is useful modernization material because it demonstrates a legacy API edge case. But it should not be treated as evidence about trading-domain API requirements.

## Apply This

1. **Co-Packaging Skepticism** -> Prevents false domain assumptions -> Trace imports and calls before assigning architectural meaning -> Pitfall: treating every WAR in an EAR as part of the same API surface.
2. **Primitive API Label** -> Separates stack coverage from product capability -> Mark sample endpoints as benchmark-adjacent -> Pitfall: modernizing them into unsupported product APIs.
3. **Static Store Warning** -> Identifies non-persistent sample behavior -> Treat static maps as mock repositories -> Pitfall: adding business features on top of them.
4. **Media Negotiation Test** -> Captures brittle REST behavior -> Test actual `Accept` headers before changing providers -> Pitfall: assuming normal REST conventions match legacy code.
5. **Domain API Gap** -> Makes modernization scope explicit -> If a trading REST API is desired, design it from `TradeServices`, not from address-book code -> Pitfall: using sample JAX-RS structure as the trading API blueprint.
