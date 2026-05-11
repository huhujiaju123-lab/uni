# Feishu Aily API Notes

Source: https://aily.feishu.cn/hc/8qluoxsa/zi14u22m

Use this reference when replacing the old “send IM message to Airy” handoff with direct Aily OpenAPI calls.

## Core Model

Aily multi-turn API has three core objects:

- `Session`: conversation container. One session can contain many messages.
- `Message`: user or assistant message inside a session.
- `Run`: one execution of an Aily app against the current session context.

The normal call sequence is:

1. Create Session
2. Create Message
3. Create Run with `app_id`
4. Poll Get Run until terminal or `REQUIRES_MESSAGE`
5. List Messages filtered by `run_id`

## Authentication

All calls use Feishu Open Platform access token:

```text
Authorization: Bearer <access_token>
Content-Type: application/json
```

Supported authorization modes:

- User Access Token: `app_id` is the target Aily app ID.
- Tenant Access Token: `app_id` must be the current application Aily ID; other app IDs fail validation.

Optional header when creating sessions:

```text
X-aily-BizUserID: <unique_user_id>
```

Use a stable internal user ID or Feishu user ID for analytics and tracing.

## Endpoints

Base URL:

```text
https://open.feishu.cn/open-apis
```

Session:

```text
POST   /aily/v1/sessions
GET    /aily/v1/sessions/{session_id}
DELETE /aily/v1/sessions/{session_id}
```

Message:

```text
POST /aily/v1/sessions/{session_id}/messages
GET  /aily/v1/sessions/{session_id}/messages/{message_id}
GET  /aily/v1/sessions/{session_id}/messages
POST /aily/v1/sessions/{session_id}/messages/{message_id}/feedback
```

Run:

```text
POST /aily/v1/sessions/{session_id}/runs
GET  /aily/v1/sessions/{session_id}/runs/{run_id}
GET  /aily/v1/sessions/{session_id}/runs
POST /aily/v1/sessions/{session_id}/runs/{run_id}/cancel
GET  /aily/v1/sessions/{session_id}/runs/{run_id}/suggestions
```

## Create Message

Required body:

```json
{
  "idempotent_id": "<uuid-or-timestamp>",
  "content_type": "MDX",
  "content": "你好"
}
```

Notes:

- `idempotent_id` is required. Same session plus same idempotent ID is treated as the same message for 72 hours.
- `content_type` can be `MDX` or `TEXT`.
- `file_ids` can be attached when using uploaded files.

## Create Run

Minimal body:

```json
{
  "app_id": "spring_xxx__c"
}
```

Optional body:

```json
{
  "app_id": "spring_xxx__c",
  "skill_id": "<skill_id>",
  "skill_input": "{\"key\":\"value\"}",
  "metadata": "{\"source\":\"codex\"}"
}
```

Notes:

- `skill_id` can reduce intent matching latency.
- `skill_input` must be a JSON string, not a JSON object.
- One session can only have one active run at a time.

## Polling And Output

Poll:

```text
GET /aily/v1/sessions/{session_id}/runs/{run_id}
```

Then fetch output:

```text
GET /aily/v1/sessions/{session_id}/messages?run_id={run_id}&with_partial_message=true
```

Use `with_partial_message=true` to read in-progress output. Filter messages where:

```text
sender.sender_type == "ASSISTANT"
```

## Run Status

Common statuses:

- `QUEUED`: created and waiting to run.
- `IN_PROGRESS`: processing.
- `COMPLETED`: terminal success; fetch final messages.
- `REQUIRES_MESSAGE`: needs more user input; fetch current messages and send a new user message.
- `EXPIRED`: run timed out. Current max run time is 1 hour.
- `CANCELLED`: run was cancelled.
- `FAILED`: run failed; an error message is also produced in the session.

When run is non-terminal or `REQUIRES_MESSAGE`, the session is locked:

- new messages can be rejected
- new runs cannot be created

## Integration Target In This Workspace

Replace `feishu-analysis-pipeline/scripts/publish_and_handoff.py` IM handoff with direct Aily mode:

1. Publish or update Feishu report.
2. Create Aily session.
3. Send prompt containing report link and beautification requirements.
4. Create run for configured Aily app.
5. Poll until `COMPLETED`.
6. List assistant messages and return generated content or generated document link.

Required local configuration:

```json
{
  "aily_app_id": "spring_xxx__c",
  "access_token_env": "FEISHU_USER_ACCESS_TOKEN"
}
```

Do not store access tokens in repository files.
