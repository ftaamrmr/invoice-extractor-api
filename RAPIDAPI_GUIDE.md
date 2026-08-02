# RapidAPI Guide (v1.1.0)

## Backend auth model
RapidAPI traffic is accepted only when:
1. `REQUIRE_RAPIDAPI_SECRET=true`
2. `X-RapidAPI-Proxy-Secret` is present
3. Header equals `RAPIDAPI_PROXY_SECRET`

`X-RapidAPI-Key` is not used for backend trust decisions.

## Suggested plans
- Free: 50 req/month
- Starter: 1,000 req/month
- Pro: 10,000 req/month
- Business: 50,000 req/month

## Secret hygiene
- Rotate `RAPIDAPI_PROXY_SECRET` regularly.
- Keep direct access disabled unless needed.
- Never publish internal secrets in examples or docs.

## Honest product description
Service uses OCR + rule-based parsing (not a generative AI model).
Accuracy varies by document quality/layout.
