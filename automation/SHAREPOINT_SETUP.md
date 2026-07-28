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

### RESOLVED VALUES for REL (use these exactly)

The target was confirmed as a SharePoint library on the RELfinance site
(from `https://netorg11487911.sharepoint.com/.../sites/RELfinance/...Deals Sheet REL.xlsx`).
Set these repository **variables**:

| Name | Value |
|---|---|
| `SHAREPOINT_HOSTNAME` | `netorg11487911.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | `/sites/RELfinance` |
| `SHAREPOINT_FOLDER` | `REL Finance - Master/2.0 Financial Data/2.7 Deal Sheet` |
| `SHAREPOINT_TARGET_NAME` | `Deals Sheet REL.xlsx` |
| `ONEDRIVE_USER` | *(leave unset — this is a site, not personal OneDrive)* |

**Contact list (optional, same credentials):** the second workflow
`upload-contacts-to-sharepoint.yml` uploads `Contact_List_REL.xlsx` whenever it
changes, to the same site. By default it lands in `SHAREPOINT_FOLDER` as
`Contact List REL.xlsx`. To send it somewhere else, set the optional variables
`SHAREPOINT_CONTACTS_FOLDER` and/or `SHAREPOINT_CONTACTS_TARGET_NAME` — no
extra secrets needed.

> **Decision made (overwrite in place):** the upload writes over the existing
> master `Deals Sheet REL.xlsx` every run. **Operational rule:** the git repo is
> now the source of truth — do **not** hand-edit `Deals Sheet REL.xlsx` directly
> in SharePoint, because the next morning's run will overwrite those edits. Any
> manual change should be made via the automation (or by asking Claude to update
> the sheet), so it goes through the repo first.

Verify `SHAREPOINT_FOLDER` against the actual library: the first segment
(`REL Finance - Master`) may be either a document library or a folder inside the
default `Documents` library. The uploader handles both automatically **as long as
the full path is correct and the folder already exists** — open the folder in
SharePoint and confirm the three segments match.

For the app-registration permission (Part 1 step 3), grant `Sites.Selected`
scoped to exactly this site:
`https://netorg11487911.sharepoint.com/sites/RELfinance`.

### Field reference (generic)

| Name | Example | Notes |
|---|---|---|
| `SHAREPOINT_HOSTNAME` | `contoso.sharepoint.com` | no `https://` |
| `SHAREPOINT_SITE_PATH` | `/sites/Finance` | leave **empty** for the tenant root site |
| `SHAREPOINT_FOLDER` | `Documents/Deals` | library + folder; the folder must already exist |
| `SHAREPOINT_TARGET_NAME` | `Deals Sheet REL.xlsx` | optional; filename to write **as** in SharePoint. Omit to keep the repo name `Deals_Sheet_REL.xlsx`. |
| `ONEDRIVE_USER` | `user@contoso.com` | **alternative to** `SHAREPOINT_HOSTNAME` — targets that user's OneDrive instead of a site; needs `Files.ReadWrite.All`. Set one target or the other, not both. |

### File-target mode

Chosen: **overwrite in place** (`SHAREPOINT_TARGET_NAME = Deals Sheet REL.xlsx`),
recorded in the resolved-values table above. To switch to a non-destructive
separate file later, change that variable to e.g.
`Deals Sheet REL (auto-updated).xlsx` — no code change needed.

### Finding the right values from a synced folder path

The team's target is the locally synced folder
`C:\Users\shyam\OneDrive - relfinance.co.uk\REL Finance - Master\2.0 Financial Data\2.7 Deal Sheet`.
To translate that into the values above: in File Explorer, right-click the
`2.7 Deal Sheet` folder → **View online** (or open it at onedrive.com and copy the
browser URL). Then:

- URL starts with `relfinance.sharepoint.com/sites/...` → it is a SharePoint
  library (synced or shortcutted into OneDrive). Use the SharePoint variables:
  hostname `relfinance.sharepoint.com`, site path `/sites/<name-in-url>`, and
  folder = the library plus subfolders as shown in the URL (e.g.
  `Master/2.0 Financial Data/2.7 Deal Sheet`). **This is the preferred target** —
  it allows the least-privilege `Sites.Selected` permission.
- URL starts with `relfinance-my.sharepoint.com/personal/shyam_relfinance_co_uk/...`
  → it is a personal OneDrive folder. Set `ONEDRIVE_USER=shyam@relfinance.co.uk`
  and `SHAREPOINT_FOLDER=REL Finance - Master/2.0 Financial Data/2.7 Deal Sheet`
  (leave `SHAREPOINT_HOSTNAME` unset), and grant the app `Files.ReadWrite.All`
  application permission in Part 1 step 3 instead of `Sites.Selected`.
  Caveat: if `REL Finance - Master` shows a link/shortcut icon in OneDrive, it is
  really a SharePoint library — use the SharePoint route above; writing through a
  OneDrive shortcut path will fail with 404.

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
