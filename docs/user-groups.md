Access is controlled by membership of two groups, `Editors` and `Developers` (named by `EDITORS_GROUP_NAME` and `DEVELOPERS_GROUP_NAME` in the settings). Every logged-in user can view everything, including the publish page and its messages. Actions that change anything are disabled for users who lack the right group, and are rejected with a 403 on the server.

Superusers get no special treatment: a superuser must also be in the `Editors` group to edit. The Django admin link is the only thing shown to superusers on that basis.

### Only Editors can:

- Publish, unpublish, hold and unhold documents
- Delete documents
- Edit a document's details and metadata
- Add and delete identifiers
- Upload documents
- Create stubs

### Editors and Developers can:

- Request enrichment
- Reparse documents
- Unlock documents

### Developers can, on the identifiers page

- See “human readable” and “score” columns
- See schema namespaces, uuids and MarkLogic URI

### Developers can, on the history page

- See event number, Submission sequence number and Marklogic version
- See the calling agent

### Developers can access Tools

The Tools pages are deliberately developer-only, even to view.

- View the Tools hub
- Inspect published documents missing an FCLID
