# Repository Instructions for Codex

## Project Overview

This repository contains a Home Assistant custom integration for tracking KLM flights from an iCal roster and enriching those roster entries with Air France-KLM Open Data flight status.

The integration should feel calm and useful at home: the dashboard card shows the current or next flight, the timeline card explains the travel day, and Home Assistant entities expose concise status for automations and notifications. The iCal roster remains the source of truth; live API data only enriches roster facts with timing, gates, aircraft, status, position, and irregularity information.

## Operating Principles

- Keep changes as small, reviewable vertical slices.
- Preserve observable behavior unless the task explicitly asks to change it.
- Prefer deterministic code for parsing, timing, cache, status, and timeline decisions.
- Keep domain logic independent from Home Assistant, vendor API payloads, storage, and frontend rendering.
- Prefer cache-first behavior before external API calls.
- Treat 404s, blocked live data, missing fields, exhausted daily budget, and stale cache as expected boundary states.
- Never commit secrets, tokens, calendar URLs, API keys, personal roster data, or private screenshots.
- Do not silently change user-facing product rules. Add or update tests for behavior changes.

## Product Rules

- Track only KLM flights with `KL` flight numbers.
- The Air France-KLM API key is required for live flight status.
- Respect API limits: stay below the daily request budget and never exceed one request per second.
- Use the iCal roster as the source of truth for which flights and travel-day events exist.
- Use AF-KLM API data to enrich roster entries with live departure/arrival timing, gates, aircraft registration, aircraft type, status, route position, and irregularities.
- Live updates should focus on the active flight window and avoid wasting requests on flights that are far outside the useful range.
- Dashboard and timeline language should be home-friendly: concise, stable, and useful for someone following the travel day.

## Important Directories

- `custom_components/flight_tracker/` - Home Assistant custom integration package.
- `custom_components/flight_tracker/clients/` - External IO and vendor transport, such as iCal HTTP and AF-KLM API clients.
- `custom_components/flight_tracker/parsers/` - Translation from iCal text or AF-KLM payloads into project-owned data.
- `custom_components/flight_tracker/models/` - Dataclasses and snapshots with minimal behavior.
- `custom_components/flight_tracker/services/` - Domain summaries, timeline composition, and travel status logic.
- `custom_components/flight_tracker/storage/` - Home Assistant persistent storage helpers for API usage, cache, and budget state.
- `custom_components/flight_tracker/frontend/` - No-build Lovelace custom card JavaScript.
- `tests/` - Fast, deterministic Python tests for parsing, services, cache, API mapping, and release metadata.
- `docs/ai/` - Local AI-agent standards, workflows, and skill guidelines. This folder may be ignored by git but should be read when present.

Root compatibility modules such as `api.py`, `api_usage.py`, `calendar.py`, `summary.py`, and `timeline.py` should stay thin and delegate to the owned modules above.

## Required References

Before making non-trivial code changes, read:

- `docs/ai/coding-standards.md`
- `docs/ai/testing-strategy.md`
- `docs/ai/architecture-guidelines.md`
- `docs/ai/agent-skills.md`

Before reviewing code, read:

- `docs/ai/code-review.md`

Before planning larger work, read:

- `docs/ai/planning-workflow.md`

If `docs/ai/` is unavailable in a checkout, follow this file and the existing code/tests as the baseline.

## Architecture Guidance

- Keep external API details inside `clients/` and `parsers/`.
- Normalize external payloads into project-owned models before they reach services or entities.
- Keep Home Assistant setup, entities, coordinators, and config flow thin around the domain layer.
- Put user-facing status text and timeline composition in `services/`.
- Keep frontend rendering separate from parsing and domain decisions.
- Avoid shallow wrapper modules unless they protect an existing compatibility import path.
- Use intention-revealing names and domain language.
- Add comments only for intent, constraints, tradeoffs, warnings, or non-obvious roster/API rules.
- Do not introduce broad architecture changes without characterization tests and a small migration plan.

## Cache And API Boundary Rules

Before calling the AF-KLM API, prefer:

1. Fresh cached status or cached flight identifiers.
2. Deterministic computation from roster data.
3. A narrow API refresh for the specific active or near-active flight.
4. Stale cached data with a clear fallback state when safe.

When changing API or storage behavior, define or preserve:

- Cache key.
- Freshness window.
- Refresh trigger.
- Daily budget behavior.
- One-request-per-second pacing.
- Failure behavior for 404, 429, missing fields, and blocked flight details.
- Whether stale data may be used and how that state is exposed.

## Frontend Rules

- This is a no-build Lovelace card. Keep browser-compatible JavaScript modules in `frontend/`.
- Keep the dashboard card and timeline card visually polished but information-dense.
- Avoid adding marketing-style pages or explanatory UI copy.
- Use concise labels and stable layout so text does not overlap in narrow Home Assistant dashboards.
- When changing frontend behavior, run the Node tests and add focused coverage for helpers, formatters, or entrypoint wiring where practical.

## Version And Release Rules

- Keep `custom_components/flight_tracker/manifest.json`, frontend `CARD_VERSION`, README cache-buster examples, tags, and GitHub releases aligned.
- Do not change versions or tags unless the user asks for a version or release update.
- Prefer a new patch version over force-moving a public release tag.
- Before a HACS-facing release, verify that the tag points at the intended commit.

## Build, Test, And Verification

Use the smallest relevant check first, then broaden before finishing when feasible.

- Python tests: `python3 -m pytest -q`
- Frontend tests: `node --test custom_components/flight_tracker/frontend/*.test.mjs`
- Python compile check: `python3 -m compileall custom_components tests`
- Whitespace check: `git diff --check`

For docs-only changes, `git diff --check` is usually enough. For parser, service, API, storage, entity, or frontend behavior changes, run the relevant focused tests and then the broader suite when feasible.

## Definition Of Done

A task is done only when:

- The change is a small, coherent slice.
- Behavior changes are covered by meaningful tests or explicitly documented as untested with a reason.
- Relevant checks have been run, or the reason they were not run is stated.
- The diff has been reviewed for readability, duplication, naming, coupling, and unnecessary complexity.
- Cache invalidation, stale data behavior, and fallback behavior are considered when relevant.
- Release/version impact is considered when HACS-facing files change.
- Remaining risks, assumptions, or follow-up work are stated.
