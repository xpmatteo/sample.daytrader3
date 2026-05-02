# Repository Guidelines

## Project Structure & Module Organization

This is a multi-module Java EE 6 DayTrader sample. Root `pom.xml` and `settings.gradle` define the same main modules: `daytrader3-ee6-ejb` for business services, data beans, EJBs, JPA resources, and SQL seed data; `daytrader3-ee6-web` for servlets, JSPs, JSF beans, static assets, web descriptors, and database DDL scripts; `daytrader3-ee6-rest` for the REST sample; `daytrader3-ee6` for EAR assembly; and `daytrader3-ee6-wlpcfg` for WebSphere Liberty server configuration. Project documentation lives in `docs/`, and JMeter workload files live in `jmeter_files/`.

## Build, Test, and Development Commands

- `gradle build`: builds all Gradle modules and assembles the application.
- `mvn install`: Maven equivalent for compiling modules and installing artifacts locally.
- `export WLP_USER_DIR=$PWD/daytrader3-ee6-wlpcfg`: points Liberty commands at this repository's server configuration.
- `/path/to/wlp/bin/installUtility install daytrader3_Sample`: installs Liberty features required by `server.xml`.
- `/path/to/wlp/bin/server start daytrader3_Sample`: starts the local sample at `http://localhost:9083/daytrader`.
- `/path/to/wlp/bin/server stop daytrader3_Sample`: stops the local server.

After first startup, use the Configuration page to recreate and repopulate the DayTrader database, then restart the server.

## Coding Style & Naming Conventions

Use Java 7-compatible code and follow the existing IBM package namespace, `com.ibm.websphere.samples.daytrader`. Keep Java indentation consistent with nearby files; existing code uses spaces in most classes and tabs in some legacy Gradle/POM sections. Class names are PascalCase, methods and fields are camelCase, constants are uppercase with underscores, and servlet/JSP names should match the existing DayTrader or `Ping*` patterns. Do not reformat unrelated legacy files.

## Testing Guidelines

There is no committed `src/test` tree. Validate changes with `gradle build` or `mvn install`, then run a Liberty smoke test when web, EJB, REST, persistence, or server configuration behavior changes. For workload validation, use the JMeter plan in `jmeter_files/daytrader3.jmx`. Add focused tests under the relevant module's `src/test/java` when introducing testable new logic.

## Commit & Pull Request Guidelines

Recent history uses short, imperative or descriptive subjects such as `Update TradeDirect.java` and `Updated Maven plugin to 2.6.3`. Keep commits focused and avoid generated build output unless it is intentionally versioned configuration. Pull requests should describe the changed module, build command results, Liberty smoke-test status, and any database or server setup impact. Include screenshots only for visible JSP/JSF UI changes.

## Security & Configuration Tips

Do not commit local Liberty logs, work areas, credentials, or machine-specific WLP paths. Treat files under `daytrader3-ee6-wlpcfg/servers/daytrader3_Sample` as deployable configuration; review changes there carefully because they affect runtime resources, messaging, transactions, and application deployment.
