# Phase 2 — LDN inbox: list notifications (D25)
# POST a notification, then verify it appears in GET /inbox listing.

POST {{gateway}}/inbox
Content-Type: application/ld+json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "type": "Create",
  "actor": "did:example:list-test",
  "object": "https://example.org/item/list-test"
}
HTTP 201
[Captures]
notif_url: jsonpath "$.id"

GET {{gateway}}/inbox
HTTP 200
[Asserts]
jsonpath "$.@context" == "http://www.w3.org/ns/ldp"
jsonpath "$.contains" isCollection
