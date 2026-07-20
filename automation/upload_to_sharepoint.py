#!/usr/bin/env python3
"""Upload the deal sheet to a SharePoint document library via Microsoft Graph.

Runs in GitHub Actions (stdlib only, no pip installs). Auth is the OAuth2
client-credentials flow against Microsoft Entra ID.

Required environment variables:
  AZURE_TENANT_ID       Entra tenant (directory) ID
  AZURE_CLIENT_ID       App registration (client) ID
  AZURE_CLIENT_SECRET   Client secret value
  SHAREPOINT_FOLDER     Target folder path (must already exist), e.g.
                        "Shared Documents/Deals" for a site library, or
                        "REL Finance - Master/2.0 Financial Data/2.7 Deal Sheet"
                        for a OneDrive target. For site libraries the first
                        segment is the library name ("Shared Documents" or
                        "Documents" both address the default library).
  UPLOAD_FILE           Path of the file to upload

Target — set exactly one of:
  SHAREPOINT_HOSTNAME   e.g. relfinance.sharepoint.com (site library target;
                        optionally with SHAREPOINT_SITE_PATH, e.g.
                        "/sites/RELFinance"; empty site path = root site)
  ONEDRIVE_USER         a UPN, e.g. shyam@relfinance.co.uk — uploads into that
                        user's OneDrive for Business instead of a site. Needs
                        the Files.ReadWrite.All application permission. NOTE:
                        a "<Site> - <Library>" folder inside OneDrive is often
                        a shortcut to a SharePoint library; shortcuts cannot be
                        written through the OneDrive path — target the real
                        site with SHAREPOINT_HOSTNAME instead.

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
        "SHAREPOINT_FOLDER", "UPLOAD_FILE",
    ]
    env = {k: os.environ.get(k, "").strip() for k in required}
    for k in ("SHAREPOINT_HOSTNAME", "SHAREPOINT_SITE_PATH", "ONEDRIVE_USER"):
        env[k] = os.environ.get(k, "").strip()
    missing = [k for k in required if not env[k]]
    if not env["SHAREPOINT_HOSTNAME"] and not env["ONEDRIVE_USER"]:
        missing.append("SHAREPOINT_HOSTNAME (or ONEDRIVE_USER)")
    if missing:
        sys.exit("Missing required configuration: " + ", ".join(missing)
                 + " — check the repository's Actions secrets and variables.")
    if env["SHAREPOINT_HOSTNAME"] and env["ONEDRIVE_USER"]:
        sys.exit("Set either SHAREPOINT_HOSTNAME or ONEDRIVE_USER, not both.")

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

    parts = [p for p in env["SHAREPOINT_FOLDER"].split("/") if p]
    if env["ONEDRIVE_USER"]:
        drive = call(f"{GRAPH}/users/{urllib.parse.quote(env['ONEDRIVE_USER'])}/drive",
                     headers=auth)
        inner = parts
    else:
        site_path = env["SHAREPOINT_SITE_PATH"].strip("/")
        site_url = (f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}:/{site_path}"
                    if site_path else f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}")
        site = call(site_url, headers=auth)

        # Resolve the target document library (drive). "Shared Documents" is the
        # web name of the default library, whose drive is named "Documents".
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
