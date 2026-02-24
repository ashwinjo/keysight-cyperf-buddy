# Quick Task 1: Browse Tab Shows Only Synced CVEs

**Goal**: Simplify Browse tab to display **only CVEs with Cyperf strike mappings** (testable=true) by default.

**Status**: Ready for execution

---

## Tasks

### Task 1: Update BrowsePage to filter testable CVEs
- **File**: `frontend/src/pages/BrowsePage.tsx`
- **Action**:
  - Remove pagination controls (complexity not needed)
  - Remove "Show Testable Only" checkbox (testable is now default)
  - Set `showOnlyTestable = true` as default state
  - Update heading/description to reflect "Synced CVEs" only
  - Keep search functionality to filter by CVE ID or strike name
  - Keep sorting capability
- **Verify**: Browser shows ONLY CVEs with testable=true badges
- **Done**: Commit with message about filtering to synced CVEs

---

## Success Criteria

- ✓ Browse page displays 0-500 CVEs, all with testable=true (green badges)
- ✓ All displayed CVEs have attack_profiles array populated
- ✓ Search still works (CVE ID or strike name)
- ✓ Sorting still works
- ✓ No pagination needed (single page of testable CVEs)
- ✓ UI is cleaner and focused
