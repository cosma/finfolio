---
name: "speckit-git-branch"
description: "Create and switch to a git branch matching the new spec's directory slug for /speckit-specify."
argument-hint: "Feature description (same text passed to /speckit-specify)"
compatibility: "Requires git repository. Optional hook for /speckit-specify before_specify phase."
metadata:
  author: "spec-kit-team"
  source: "git-branch-creation-hook"
  hook-type: "before_specify"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

## Branch Creation Hook for /speckit-specify

This skill is a `before_specify` hook (registered in `.specify/extensions.yml`). It creates and checks out a git branch whose name matches the feature slug that `/speckit-specify` will use for its `specs/<slug>/` directory.

### Execution

1. **Guard**: Check if we're in a git repository.
   ```bash
   git rev-parse --git-dir 2>/dev/null
   ```
   If this fails (not a git repo), output an informational message and exit with code 0 (graceful no-op). The caller will continue spec creation on the current branch.

2. **Compute the feature slug**:
   - If `GIT_BRANCH_NAME` environment variable is set (user explicitly specified a branch name to `/speckit-specify`), use it verbatim as the branch name — no numbering or slugification.
   - Otherwise, parse `$ARGUMENTS` (the feature description) and call:
     ```bash
     python3 .specify/scripts/python/create_new_feature.py --json --dry-run "$ARGUMENTS"
     ```
     This outputs JSON with `BRANCH_NAME`, `FEATURE_NUM`, `SPEC_FILE` keys.
     Extract `BRANCH_NAME` from that JSON.
   - If the Python script fails (e.g. invalid description, bad arguments), report the error and exit with code 1.

3. **Create and check out the branch**:
   ```bash
   git checkout -b "$BRANCH_NAME"
   ```
   If this fails because the branch already exists (exit code 1), fall back to:
   ```bash
   git checkout "$BRANCH_NAME"
   ```
   to switch onto the existing branch instead of erroring. This covers re-runs and pre-existing branches.
   
   If the second `git checkout` also fails, report the error and exit with code 1.

4. **Output the hook contract**:
   Emit JSON with the keys `/speckit-specify` step 2 expects:
   ```json
   {
     "BRANCH_NAME": "<computed-or-provided-branch-name>",
     "FEATURE_NUM": "<NNN-from-slug>"
   }
   ```
   If `GIT_BRANCH_NAME` was explicitly provided, `FEATURE_NUM` may be unavailable — output an empty string or omit the key in that case; `/speckit-specify` step 2 only uses `BRANCH_NAME` as the source of truth when an explicit `GIT_BRANCH_NAME` was provided.

5. **Success**:
   - Exit code 0.
   - User is now on the new/switched branch, ready for `/speckit-specify` to create `specs/<slug>/` on this branch.

### Error Handling

- **Not a git repo**: Exit 0 with an informational message (graceful no-op).
- **Invalid feature description**: Report the error and exit 1.
- **git checkout fails**: Report the error and exit 1.
- Any other failure: Report the error and exit 1.

### Example

```bash
# User calls /speckit-specify with feature description
/speckit-specify "Add user authentication with OAuth2"

# Pre-Execution Checks surfaces this optional hook
## Extension Hooks
**Optional Pre-Hook**: git-branch-creation
Command: `/speckit-git-branch`
Description: Create and switch to a git branch matching the new feature's directory slug

Prompt: Create and check out a new git branch for this feature...
To execute: `/speckit-git-branch`

# User (or automation) explicitly invokes the hook
/speckit-git-branch "Add user authentication with OAuth2"

# Hook computes: BRANCH_NAME="003-user-authentication" (via create_new_feature.py)
# Runs: git checkout -b 003-user-authentication
# Outputs: {"BRANCH_NAME": "003-user-authentication", "FEATURE_NUM": "003"}
# Then /speckit-specify step 2 reads this JSON
# Then /speckit-specify step 3 creates specs/003-user-authentication/spec.md on this branch
```

### Integration with /speckit-specify

- **Hook registration**: Defined in `.specify/extensions.yml` under `hooks.before_specify`.
- **Optional**: Set `optional: true` — every `/speckit-specify` run surfaces this as a choice, not an automatic requirement.
- **Contract**: Output JSON with `BRANCH_NAME` and `FEATURE_NUM` (if computable). `/speckit-specify` step 2 reads this and confirms the branch exists.
- **No state changes**: This hook computes the slug using the same logic as `/speckit-specify` (delegating to `create_new_feature.py --dry-run`) so there is no risk of off-by-one numbering or namespace collisions.
- **Graceful fallback**: If not a git repo, this hook silently succeeds and `/speckit-specify` continues on the current branch (no directory creation is blocked).
