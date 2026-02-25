# Phase 2 — D13: GET /agents returns registered agents

# First register an agent
POST {{gateway}}/agents/register
Content-Type: application/json
```json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read", "write"]
}
```
HTTP 201

# Then list agents
GET {{gateway}}/agents
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "RegisteredAgent"
body contains "agentRole"
body contains "DevelopmentAgentRole"
