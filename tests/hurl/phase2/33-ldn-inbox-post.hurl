# Phase 2 — LDN inbox: POST notification (D25)

POST {{gateway}}/inbox
Content-Type: application/ld+json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "type": "Announce",
  "actor": "did:example:sender",
  "object": "https://example.org/dataset/1"
}
HTTP 201
[Asserts]
header "Location" contains "/inbox/"
jsonpath "$.id" contains "/inbox/"

# Reject missing @context
POST {{gateway}}/inbox
Content-Type: application/ld+json
{"type": "Announce"}
HTTP 400
[Asserts]
jsonpath "$.error" contains "@context"

# Reject wrong content type
POST {{gateway}}/inbox
Content-Type: text/plain
{"@context": "test"}
HTTP 415
