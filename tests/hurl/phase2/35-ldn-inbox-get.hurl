# Phase 2 — LDN inbox: get single notification (D25)
# POST a notification, capture ID, then GET it back.

POST {{gateway}}/inbox
Content-Type: application/ld+json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "type": "Announce",
  "actor": "did:example:get-test",
  "object": "https://example.org/item/get-test"
}
HTTP 201
[Captures]
notif_id: header "Location"

# Extract just the UUID from the Location URL and fetch it
# Location is like {{gateway}}/inbox/{uuid}
GET {{notif_id}}
HTTP 200
[Asserts]
jsonpath "$.actor" == "did:example:get-test"
jsonpath "$.type" == "Announce"
jsonpath "$['@context']" == "https://www.w3.org/ns/activitystreams"

# Non-existent notification
GET {{gateway}}/inbox/00000000-0000-0000-0000-000000000000
HTTP 404
