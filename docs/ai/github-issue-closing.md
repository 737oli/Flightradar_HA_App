# GitHub Issue Closing Comments

Use this reference when closing GitHub issues after completing a focused slice of work, whether the changes are local, committed, pushed, in a pull request, or merged.

## Purpose

Leave a concise completion comment that makes the issue history useful later. The comment should show what changed, how it was validated, what delivery state the work is in, and what risk remains.

## Before Commenting

- Re-read the issue scope and acceptance criteria.
- Review the diff for only the files related to that issue.
- Confirm which changes are local, committed, pushed, in a pull request, or merged.
- Run the smallest relevant checks first, then broader checks when feasible.
- Do not claim unrelated local work as part of the issue.
- Do not include secrets, private roster data, API keys, or raw calendar URLs.

## State Disclosure

Always state the current delivery state explicitly:

- `Local only` - changes exist locally but are not committed.
- `Committed` - changes are committed locally.
- `Pushed` - changes are pushed to the remote branch.
- `Pull request opened` - a PR exists but is not merged.
- `Merged` - the change is merged into the target branch.

Do not imply a stronger state than actually exists.

## Comment Structure

Use the same structure as `docs/ai/code-review.md`:

```markdown
## Summary

<What was completed and why it satisfies the issue. Mention important files or behavior boundaries.>

## Delivery state

<Local only / Committed / Pushed / Pull request opened / Merged. Include branch or PR when useful.>

## Blocking issues

None.

## Non-blocking suggestions

<Optional follow-ups, or "None for this slice.">

## Tests/checks run

- `<command>` -> `<result>`

## Remaining risks

<What this did not verify, or "No known functional risk from this docs-only slice.">
```

## Closing The Issue

1. Post the completion comment first.
2. Close the issue with a short closure note.
3. Re-query the issue state when practical.
4. Tell the user whether the code is committed, pushed, released, or still local.

## Good Closure Note

```text
Closed after completing the documented slice and recording validation results above.
```

## Avoid

- Closing without a validation summary.
- Mixing several unrelated issues into one completion comment.
- Overstating what tests prove.
- Claiming a release, push, or commit happened when it did not.
- Pasting large diffs into the issue when a concise file summary is clearer.
