# Phase 2 — D13: SPARQL endpoints require VP Bearer auth
# Verify 401 when no Authorization header is provided

# No auth → 401 on /sparql
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
```
SELECT * WHERE {} LIMIT 1
```
HTTP 401
[Asserts]
header "WWW-Authenticate" contains "Bearer"
jsonpath "$.detail" contains "VP Bearer token required"

# No auth → 401 on /sparql/update
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded

```
update=INSERT DATA { GRAPH <urn:test:unauth> { <urn:s> <urn:p> <urn:o> } }
```
HTTP 401

# Malformed token → 401
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
Authorization: Bearer not-a-valid-base64url-token!!!
```
SELECT * WHERE {} LIMIT 1
```
HTTP 401
