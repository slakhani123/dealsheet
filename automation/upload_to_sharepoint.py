#!/usr/bin/env python3
"""Upload the deal sheet to a SharePoint document library via Microsoft Graph.

Runs in GitHub Actions (stdlib only, no pip installs). Auth is the OAuth2
client-credentials flow against Microsoft Entra ID.

Required environment variables:
  AZURE_TENANT_ID       Entra tenant (directory) ID
  AZURE_CLIENT_ID       App registration (client) ID
  AZURE_CLIENT_SECRET   Client secret value
  SHAREPOINT_HOSTNAME   e.g. relfinance.sharepoint.com
  SHAREPOINT_FOLDER     Library and folder, e.g. "Shared Documents/Deals"
                        ("Shared Documents" or "Documents" both address the
                        default library; the folder must already exist)
  UPLOAD_FILE           Path of the file to upload

Optional:
  SHAREPOINT_SITE_PATH  e.g. "/sites/RELFinance"; leave empty for the root site

Simple (single-request) upload is used, which Graph limits to 4 MB — far above
the deal sheet's size. If the file ever approaches that, switch to an upload
session (createUploadSession).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.microsoft.com/v1.0"


def call(url, data=None, headers=None, method=None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} calling {url.split('?')[0]}\n{body[:800]}")


def main():
    required = [
        "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
        "SHAREPOINT_HOSTNAME", "SHAREPOINT_FOLDER", "UPLOAD_FILE",
    ]
    env = {k: os.environ.get(k, "").strip() for k in required}
    env["SHAREPOINT_SITE_PATH"] = os.environ.get("SHAREPOINT_SITE_PATH", "").strip()
    missing = [k for k in required if not env[k]]
    if missing:
        sys.exit("Missing required configuration: " + ", ".join(missing)
                 + " — check the repository's Actions secrets and variables.")

    token = call(
        f"https://login.microsoftonline.com/{env['AZURE_TENANT_ID']}/oauth2/v2.0/token",
        data=urllib.parse.urlencode({
            "client_id": env["AZURE_CLIENT_ID"],
            "client_secret": env["AZURE_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    site_path = env["SHAREPOINT_SITE_PATH"].strip("/")
    site_url = (f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}:/{site_path}"
                if site_path else f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}")
    site = call(site_url, headers=auth)

    # Resolve the target document library (drive). "Shared Documents" is the
    # web name of the default library, whose drive is named "Documents".
    parts = [p for p in env["SHAREPOINT_FOLDER"].split("/") if p]
    lib = parts[0].lower()
    drives = call(f"{GRAPH}/sites/{site['id']}/drives", headers=auth)["value"]
    drive = next(
        (d for d in drives
         if d["name"].lower() == lib
         or (lib in ("shared documents", "documents") and d["name"].lower() == "documents")),
        None,
    )
    if drive:
        inner = parts[1:]
    else:
        drive = call(f"{GRAPH}/sites/{site['id']}/drive", headers=auth)
        inner = parts

    filename = os.path.basename(env["UPLOAD_FILE"])
    item_path = "/".join(urllib.parse.quote(p) for p in inner + [filename])
    with open(env["UPLOAD_FILE"], "rb") as f:
        content = f.read()

    item = call(
        f"{GRAPH}/drives/{drive['id']}/root:/{item_path}:/content",
        data=content,
        method="PUT",
        headers={**auth, "Content-Type": "application/octet-stream"},
    )
    print(f"Uploaded {filename} ({len(content):,} bytes) to: {item.get('webUrl', '(no URL returned)')}")


if __name__ == "__main__":
    main()
