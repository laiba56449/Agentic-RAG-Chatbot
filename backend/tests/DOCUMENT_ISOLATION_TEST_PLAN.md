# Document Isolation Test Plan

Purpose: verify that document-level isolation (SRS FR-13, NFR-2) is enforced
server-side, at the database query level, for both Organization Mode and
Personal Mode — not merely hidden in the UI.

## Test Data (existing from Days 6-14)
- User A (student1@example.com) — Admin of Org 1, Admin of Org 2, has personal documents
- User B (student2@example.com) — Admin of Org 3, Member of Org 2, has personal documents
- Org 1 has at least one document uploaded by User A
- Org 2 has at least one document uploaded by User A
- User A and User B each have at least one personal document

## Test Cases

| # | Actor | Action | Target | Expected Result |
|---|-------|--------|--------|-----------------|
| D1 | User A | GET /organizations/{Org1}/documents | Own org (admin) | 200, sees Org 1's documents only |
| D2 | User B | GET /organizations/{Org2}/documents | Org they're a member (not admin) of | 200, sees Org 2's documents only |
| D3 | User B | GET /organizations/{Org1}/documents | Org they don't belong to at all | 403 "not a member" |
| D4 | User B | DELETE /organizations/{Org2}/documents/{doc_id} | Member, not admin, of this org | 403 "requires admin privileges" |
| D5 | User A | DELETE /organizations/{Org1}/documents/{doc_id from Org2} | Admin of Org1 (wrong org), doc belongs to Org2 | 404 "Document not found in this organization" |
| D6 | User A | GET /personal/documents | Own personal documents | 200, sees only User A's personal docs |
| D7 | User B | GET /personal/documents | Own personal documents | 200, sees only User B's personal docs (different from D6) |
| D8 | User B | DELETE /personal/documents/{User A's doc_id} | Another user's personal document | 404 "Document not found"; User A's document remains intact afterward |
| D9 | User A | DELETE /organizations/{Org1}/documents/{doc_id} | Their own org, real document, correct org | 204; document removed from DB and disk |
| D10 | Anyone | GET or DELETE any document endpoint | No auth token | 401 |

## Notes
- D3 vs D5 distinction: D3 fails at the *membership* layer (user isn't in the org
  at all); D5 fails at the *document ownership* layer (user IS a legitimate admin,
  just of the wrong org for this specific document). Both return different status
  codes/messages, confirming isolation is enforced at two independent layers.
- D8 is the single most important test in this document: personal-mode isolation
  has no role system to fall back on — it is pure ownership-based query filtering,
  and a failure here would mean one user's private files are deletable by anyone
  who can guess or observe a UUID.