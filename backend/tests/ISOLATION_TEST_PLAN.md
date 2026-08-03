# Multi-Tenant Isolation Test Plan

## Purpose

Verify that organization data isolation (SRS NFR-2, FR-9, FR-10) is enforced at the API/database level, not merely hidden in the UI.

---

## Test Data Setup

- User A (student1@example.com)
  - Admin of Org 1
  - Admin of Org 2

- User B (student2@example.com)
  - Admin of Org 3
  - Member of Org 2

---

## Test Cases

| # | Actor | Action | Target | Expected Result | Status |
|---|-------|--------|--------|-----------------|--------|
| T1 | User B | GET /organizations/{Org2}/member-check | Org they belong to (member) | 200, role=member | ✅ Passed (Step 8.1) |
| T2 | User B | GET /organizations/{Org1}/member-check | Org they don't belong to | 403 "not a member" | ✅ Passed (Step 8.1) |
| T3 | Anyone | GET /organizations/{any}/member-check | No auth token | 401 | ✅ Passed (Step 8.1) |
| T4 | User A | GET /organizations/{Org1}/admin-check | Own org, is admin | 200, role=admin | ✅ Passed (Step 8.2) |
| T5 | User B | GET /organizations/{Org2}/admin-check | Member, not admin, of this org | 403 "requires admin privileges" | ✅ Passed (Step 8.2) |
| T6 | User B | GET /organizations/{Org1}/admin-check | Not a member at all | 403 "not a member" (not the admin message) | ✅ Passed (Step 8.2) |
| T7 | User B | GET /organizations/{Org3}/admin-check | Own org, is admin | 200, role=admin | ✅ Passed (Step 8.2) |
| T8 | User B | GET /organizations/{random-valid-uuid}/member-check | Valid UUID but organization does not exist | 403 "not a member" | ⬜ Not yet tested |
| T9 | User A | POST /organizations/join with Org1's own invite code | Re-join own org | 400 "already a member" | ⬜ Not yet tested |

---

## Notes

- T2 vs T6 distinction matters:
  - Both return 403.
  - T2 means no membership row exists.
  - T6 means membership exists but the user has insufficient role.

- Confirmed these produce different `detail` messages, proving the dependency chain checks membership before role, not a single combined check.