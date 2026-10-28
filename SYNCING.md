# Syncing with Frappe LMS

This app ships its own build of the Frappe LMS frontend, plus a few page files copied from
`frappe/lms`, with Asante's changes on top. When upstream LMS updates, those copies must be
refreshed and the Asante changes reapplied.

## Current upstream base

| | |
|---|---|
| Upstream repo | `frappe/lms`, checked out next to this app at `../lms` |
| Branch | `main` |
| Commit | `c51661b164acd7df87e54a6d8d47a4e67985ff68` (`v2.67.1`) |
| Minimum Frappe | `version-16` at 16.54.0 or newer (the frontend links `@framework/ui` to `../../frappe/ui`) |

Update this table on every sync.

## What comes from upstream

Files copied verbatim from `frappe/lms` (the "upstream snapshot"):

| This repo | Upstream (`../lms`) |
|---|---|
| `frontend/` (everything except `node_modules`) | `frontend/` |
| `lms_extension/www/_lms.py`, `certificate.py`, `certificate.html`, `new-sign-up.html` | `lms/www/` (same names) |
| `lms_extension/templates/signup-form.html` | `lms/templates/signup-form.html` |

Also mirrors upstream, but kept by hand:

- `lms_extension/plugins.py` `show_custom_signup` mirrors `lms/plugins.py` `show_custom_signup`.
  Compare them on each sync; only the returned template path should differ.

Build output, not tracked: `lms_extension/www/_lms.html` and `lms_extension/public/frontend/`.

## What Asante changes

All changes to upstream-derived files live in **one commit** per sync, exported as
`patches/0001-Apply-changes-made-by-Asante.patch`. Keep it that way: everything else in the
sync should be either a pure upstream snapshot or code that exists only in this app.

| File | Change | Why |
|---|---|---|
| `frontend/package.json`, `frontend/vite.config.js`, `frontend/vite.signup-select.config.js` | Build paths `lms` → `lms_extension` | The extension serves its own build from `/assets/lms_extension/frontend/` |
| `lms_extension/templates/signup-form.html` | Asset paths `lms` → `lms_extension` | Loads the signup-select bundle this app builds |
| `frontend/src/pages/Courses/Courses.vue` | Students default to the Enrolled tab; instructors (who are not moderators, evaluators or system managers) only see courses they teach; staff get Live / New / Upcoming / Created / Unpublished tabs | Institutes' course visibility rules |
| `frontend/src/utils/index.js` | "Student Portal" sidebar item linking to `/student-portal` | Link to the institutes' student portal (outside the SPA) |

Code that exists only in this app (no conflicts on sync, but check it still fits):

- `lms_extension/hooks.py` `signup_form_template`: overrides lms's signup form with ours.
- `lms_extension/patches/migrate_due_date_to_schedule.py`: one-off migration from the old
  `custom_due_date` custom field to upstream's assignment scheduling.
- `lms_extension/lms_extension/custom/lms_assignment.json`: `custom_due_date` is kept hidden and
  optional for its historical data. Upstream's `enable_scheduling` / `schedule_start` /
  `schedule_end` replace it.

### Changes dropped because upstream now covers them

Don't reintroduce these when resolving conflicts:

- Assignment due date (`custom_due_date` in `Assignment.vue`, `AssignmentForm.vue`,
  `Assignments.vue`): replaced by upstream assignment scheduling in v2.67.
- Mobile fallback for non-route links (`MobileLayout.vue` `handleClick`): upstream's phone shell
  lists sidebar links on the You page and already handles links outside the SPA
  (`components/Settings/youRows.ts` `destinationRow`).

## How to sync

Run from this app's directory (`apps/lms_extension`). Use a branch.

1. **Update upstream and pick the target commit.**
   ```bash
   git -C ../lms fetch upstream && git -C ../lms checkout main && git -C ../lms pull --ff-only
   NEW=$(git -C ../lms rev-parse HEAD)
   OLD=<commit from the table above>
   ```

2. **See what upstream changed in the files Asante touches.** Read this before resolving conflicts.
   ```bash
   git -C ../lms log --oneline $OLD..$NEW -- \
     frontend/package.json frontend/vite.config.js frontend/vite.signup-select.config.js \
     frontend/src/pages/Courses/Courses.vue frontend/src/utils/index.js \
     lms/templates/signup-form.html lms/plugins.py lms/www
   ```
   Also look for upstream features that now cover an Asante change (as happened with
   assignment scheduling). Dropping the Asante change is usually better than keeping both.

3. **Commit the upstream snapshot.** Keep this commit pure upstream, so the next sync can diff
   against it.
   ```bash
   git ls-files frontend | xargs -d '\n' rm -f
   find frontend -mindepth 1 -type d -empty -not -path 'frontend/node_modules*' -delete
   git -C ../lms archive $NEW frontend | tar -x -C .
   for f in _lms.py certificate.py certificate.html new-sign-up.html; do
     cp ../lms/lms/www/$f lms_extension/www/$f
   done
   cp ../lms/lms/templates/signup-form.html lms_extension/templates/signup-form.html
   git add -A frontend lms_extension/www lms_extension/templates/signup-form.html
   git commit -m "Update to match frappe lms <version>" -m "Upstream: frappe/lms@$NEW"
   ```

4. **Reapply the Asante changes.**
   ```bash
   git apply --3way patches/0001-Apply-changes-made-by-Asante.patch
   ```
   Resolve conflicts using the "Why" column above. A file that upstream deleted or moved needs
   its change ported by hand. Then commit and regenerate the patch from that commit:
   ```bash
   git add -A frontend lms_extension/templates/signup-form.html
   git commit -m "Apply changes made by Asante"
   git format-patch -1 HEAD --stdout > patches/0001-Apply-changes-made-by-Asante.patch
   git add patches && git commit -m "Update Asante patch"
   ```

5. **Check for new hardcoded `lms` paths.** Upstream sometimes adds build paths that must point
   at `lms_extension`. Runtime URLs like `/assets/lms/frontend/Quiz.mp4` are fine, because the
   lms app serves them.
   ```bash
   grep -rn "\.\./lms/\|assets/lms/" frontend --include=*.js --include=*.ts --include=*.json \
     --exclude-dir=node_modules --exclude-dir=src
   ```

6. **Sync the Python-side mirrors.** Diff `lms_extension/plugins.py` against
   `../lms/lms/plugins.py` `show_custom_signup`. Check that the boot keys in
   `lms_extension/www/_lms.py` match what the frontend reads (`window.*`).

7. **Build and test.**
   ```bash
   cd frontend && yarn install --frozen-lockfile && yarn build && npx vitest run
   git checkout -- components.d.ts   # the build regenerates it; keep upstream's copy
   ```
   Then run `bench migrate` and restart.

8. **Update the "Current upstream base" table** in this file and commit.

## Gotchas

- **A failed build deletes the deployed frontend.** Vite empties
  `lms_extension/public/frontend` before building, so if the build fails the site has no
  frontend until a build succeeds.
- **The build needs a matching Frappe.** `@framework/ui` is a link to `../../frappe/ui`. A
  `MISSING_EXPORT ... @framework/ui` error means Frappe is older than this LMS version needs:
  pull `apps/frappe` and run `yarn install` there.
- **Known test failures that are not regressions.** `src/tests/ravenRuleModel.test.ts` reads
  `lms/raven_provider.py` relative to the app root, so it only passes inside the lms repo. Under
  load, a full `vitest run` can time out a handful of tests that pass when run on their own.
  Compare against a pristine upstream copy before treating a failure as yours.
- **`git apply --3way` needs a clean index.** It refuses files whose index entry differs from the
  working tree. Stage the snapshot first, or commit it as in step 3.
