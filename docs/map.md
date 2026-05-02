# UI Entry Points

The DayTrader browser UI lives in `daytrader3-ee6-web/src/main/webapp`.
The application welcome file is `/index.html`, configured in
`WEB-INF/web.xml`. It is a frameset that loads:

- `/header.html`
- `/contentHome.html`
- `/footer.html`

The header links to the main application areas:

- `/app` - main trading UI
- `/configure.html` - configuration landing page
- `/web_prmtv.html` - web primitive samples
- `/docs/tradeFAQ.html` - documentation/FAQ

## Controller-Backed UI

`/app` is handled by `TradeAppServlet` and renders JSP pages selected through
`TradeConfig.webUI`:

- `/welcome.jsp`, `/welcomeImg.jsp`
- `/register.jsp`, `/registerImg.jsp`
- `/portfolio.jsp`, `/portfolioImg.jsp`
- `/quote.jsp`, `/quoteImg.jsp`
- `/tradehome.jsp`, `/tradehomeImg.jsp`
- `/account.jsp`, `/accountImg.jsp`
- `/order.jsp`, `/orderImg.jsp`
- `/config.jsp`
- `/runStats.jsp`

Other servlet-backed UI routes:

- `/config` - renders `/config.jsp` or `/runStats.jsp`
- `/scenario` - runs a generated trading scenario and includes `/app?...` actions
- `/TestServlet` - includes `/tradehome.jsp`
- `*.jsf` - mapped to `FacesServlet`; with `.xhtml` as the default JSF suffix,
  the reachable Facelets are `/PingFaceletSmall.jsf` and `/PingFaceletLarge.jsf`

## JSP Files

- `account.jsp`
- `accountImg.jsp`
- `config.jsp`
- `displayQuote.jsp`
- `error.jsp`
- `marketSummary.jsp`
- `order.jsp`
- `orderImg.jsp`
- `PingJsp.jsp`
- `PingJspEL.jsp`
- `PingServlet2Jsp.jsp`
- `portfolio.jsp`
- `portfolioImg.jsp`
- `quote.jsp`
- `quoteDataPrimitive.jsp`
- `quoteImg.jsp`
- `register.jsp`
- `registerImg.jsp`
- `runStats.jsp`
- `sample.jsp`
- `tradehome.jsp`
- `tradehomeImg.jsp`
- `welcome.jsp`
- `welcomeImg.jsp`

Some JSPs are primarily fragments or internal targets rather than normal
top-level pages:

- `displayQuote.jsp`
- `marketSummary.jsp`
- `quoteDataPrimitive.jsp`
- `error.jsp`
- `PingServlet2Jsp.jsp`

## Other Page Templates And Static Pages

- `index.html`
- `header.html`
- `contentHome.html`
- `footer.html`
- `leftMenu.html`
- `configure.html`
- `web_prmtv.html`
- `PingHtml.html`
- `PingFaceletSmall.xhtml`
- `PingFaceletLarge.xhtml`
- `docs/benchmarking.html`
- `docs/documentation.html`
- `docs/glossary.html`
- `docs/rtCharacterisitics.html`
- `docs/tradeFAQ.html`
- `docs/tradeversion.html`
