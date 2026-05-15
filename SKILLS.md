# Project Skills

Use these recurring skills when working in this repository.

## Plan A Small Slice

1. Clarify the requested behavior.
2. Identify assumptions and unresolved questions.
3. Inspect the existing code and tests.
4. Define what should be true when done.
5. Implement the smallest useful vertical slice.
6. Run feedback loops and review the diff.

Good slices are small enough to review in one sitting, covered by focused tests, reversible if wrong, and visibly closer to the product goal.

## Parse External Data Safely

- Keep raw iCal and AF-KLM response handling inside `parsers/`.
- Prefer structured parsing over ad hoc string manipulation when possible.
- Preserve roster semantics such as flights, deadheads, hotel stays, taxi rows, ground time, and base returns.
- Add characterization tests before changing unclear roster parsing behavior.

## Build Domain Summaries

- Put travel-day and notification-friendly composition in `services/`.
- Keep user-facing text concise and stable.
- Prefer clear phase/state names over leaking implementation details.
- Use live AF-KLM times to show early/late changes against scheduled roster times when available.

## Protect External Boundaries

- Keep HTTP/API behavior inside `clients/`.
- Keep Home Assistant persistence in `storage/`.
- Cache AF-KLM flight ids where possible.
- Treat 404s, blocked requests, budget exhaustion, and missing live data as expected boundary states, not crashes.

## Review Like A Senior Engineer

Use this structure for substantial reviews:

1. Summary
2. Blocking issues
3. Non-blocking suggestions
4. Tests/checks run
5. Remaining risks

Check correctness, edge cases, error handling, module ownership, naming, useful comments, and meaningful tests.

## Test Behavior

- Prefer behavior tests over implementation-copying tests.
- Cover boundary conditions and near-bug cases.
- Keep tests fast, deterministic, independent, and self-validating.
- For behavior changes, update or add tests before broad refactors.
