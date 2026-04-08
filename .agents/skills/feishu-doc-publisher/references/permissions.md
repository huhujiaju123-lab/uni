# Feishu permissions used by this skill

This skill relies on two Feishu API paths:

- `POST /docx/v1/documents`
- `PATCH /drive/v1/permissions/{token}/public?type=docx`

Working permission defaults for this workspace:

- `link_share_entity = tenant_readable`
- `security_entity = anyone_can_view`
- `external_access = false`

Meaning:

- Anyone inside the current tenant with the link can read the document.
- The doc is not exposed outside the organization.

If document creation succeeds but the user cannot open the link, first check whether the current Feishu account belongs to the same tenant.
