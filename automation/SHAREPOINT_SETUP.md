# SharePoint upload — one-time setup

Every time `Deals_Sheet_REL.xlsx` is pushed to this repo, the GitHub Action
`.github/workflows/upload-to-sharepoint.yml` uploads it to a SharePoint document
library so the team always sees the latest copy in the shared area. The workflow
does nothing until the credentials below are configured — until then it will fail
with "Missing required configuration", which is harmless.

Forward this document to whoever administers your Microsoft 365 tenant.

## Part 1 — Microsoft Entra app registration (IT admin, ~10 minutes)

1. Go to https://entra.microsoft.com → **Identity → Applications → App registrations → New registration**.
   - Name: `REL Deal Sheet Uploader`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: leave blank. → **Register**.
2. On the app's Overview page, note the **Application (client) ID** and **Directory (tenant) ID**.
3. **API permissions → Add a permission → Microsoft Graph → Application permissions**, then either:
   - **Recommended (least privilege): `Sites.Selected`** — the app can only touch
     sites it is explicitly granted. After adding it and clicking **Grant admin
     consent**, grant the app write access to the one site, e.g. with PnP PowerShell:
     ```powershell
     Grant-PnPAzureADAppSitePermission -AppId "<client-id>" -DisplayName "REL Deal Sheet Uploader" `
       -Site "https://<tenant>.sharepoint.com/sites/<SiteName>" -Permissions Write
     ```
     (equivalently: Graph `POST /sites/{site-id}/permissions` with role `write`).
   - **Simpler but broader: `Sites.ReadWrite.All`** — write access to all sites in
     the tenant. Add it and click **Grant admin consent**. Use only if the
     Sites.Selected grant step is impractical.
4. **Certificates & secrets → New client secret**. Choose an expiry (12–24 months)
   and **set a calendar reminder to rotate it** — uploads stop silently when it
   expires. Copy the secret **Value** immediately (it is shown only once).

## Part 2 — GitHub repository configuration (anyone with repo admin)

In https://github.com/slakhani123/dealsheet → **Settings → Secrets and variables → Actions**:

**Secrets** (Secrets tab → New repository secret):

| Name | Value |
|---|---|
| `AZURE_TENANT_ID` | Directory (tenant) ID from step 2 |
| `AZURE_CLIENT_ID` | Application (client) ID from step 2 |
| `AZURE_CLIENT_SECRET` | Client secret value from step 4 |

**Variables** (Variables tab → New repository variable):

| Name | Example | Notes |
|---|---|---|
| `SHAREPOINT_HOSTNAME` | `relfinance.sharepoint.com` | no `https://` |
| `SHAREPOINT_SITE_PATH` | `/sites/RELFinance` | leave **empty** for the tenant root site |
| `SHAREPOINT_FOLDER` | `Shared Documents/Deals` | library + folder; the folder must already exist |

## Part 3 — Test

Repo → **Actions → Upload deal sheet to SharePoint → Run workflow** (on branch
`claude/deal-sheet-auto-populate-svgr0b`). A green run prints the SharePoint URL
of the uploaded file in the step log. After that, no manual steps ever — each
morning sweep that changes the sheet re-uploads it automatically.

## Troubleshooting

- **HTTP 401/invalid client** — wrong tenant/client ID or expired secret.
- **HTTP 403 on upload** — consent not granted, or (with Sites.Selected) the
  per-site grant in Part 1 step 3 was skipped.
- **HTTP 404 resolving the site** — check `SHAREPOINT_HOSTNAME` / `SHAREPOINT_SITE_PATH`.
- **HTTP 404 on upload** — the folder in `SHAREPOINT_FOLDER` doesn't exist; create it in SharePoint first.
