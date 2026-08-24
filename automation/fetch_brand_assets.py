#!/usr/bin/env python3
"""Download REL brand assets and the loan-note statement workbook from
SharePoint via Microsoft Graph, for embedding into the financial model.

Runs in GitHub Actions (stdlib only). Auth and site resolution mirror
upload_to_sharepoint.py (OAuth2 client-credentials flow).

Required environment variables:
  AZURE_TENANT_ID       Entra tenant (directory) ID
  AZURE_CLIENT_ID       App registration (client) ID
  AZURE_CLIENT_SECRET   Client secret value
  SHAREPOINT_HOSTNAME   e.g. netorg11487911.sharepoint.com
  SHAREPOINT_SITE_PATH  e.g. /sites/RELfinance (optional; empty = root site)
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.microsoft.com/v1.0"

THEME = "11. 2026 Rebrand/New Website 2026/rel-preview/rel-finance-theme/assets"
FILES = {
    "brand-assets/rel-finance-logo.png": f"{THEME}/images/rel-finance-logo.png",
    "brand-assets/rel-finance-logo-square.png": f"{THEME}/images/rel-finance-logo-square.png",
    "brand-assets/favicon-512.png": f"{THEME}/images/favicon-512.png",
    "brand-assets/Loan_Note_Schedules_New.xlsx":
        "4.0 Investors/4.2 Loan Note Investors/3A Palace Green Loan Notes/"
        "Loan_Note_Schedules_New.xlsx",
}
CSS_FOLDER = f"{THEME}/css"


def call(url, data=None, headers=None, method=None, raw=False):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} calling {url.split('?')[0]}\n{detail}") from None
    return body if raw else json.loads(body.decode())


def item_path_url(drive_id, path):
    quoted = "/".join(urllib.parse.quote(p) for p in path.split("/"))
    return f"{GRAPH}/drives/{drive_id}/root:/{quoted}"


def download(drive_id, path, dest, auth):
    meta = call(item_path_url(drive_id, path) + "?select=id,name,size", headers=auth)
    # Fetch content via the item id; the pre-signed redirect must be followed
    # WITHOUT the Graph bearer token, so resolve downloadUrl explicitly.
    info = call(f"{GRAPH}/drives/{drive_id}/items/{meta['id']}"
                "?select=id,name,@microsoft.graph.downloadUrl", headers=auth)
    url = info.get("@microsoft.graph.downloadUrl")
    if not url:
        raise RuntimeError(f"no downloadUrl for {path}")
    content = call(url, raw=True)  # pre-signed: no auth header
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(content)
    print(f"Downloaded {dest} ({len(content):,} bytes)")


def main():
    required = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                "SHAREPOINT_HOSTNAME"]
    env = {k: os.environ.get(k, "").strip()
           for k in required + ["SHAREPOINT_SITE_PATH"]}
    missing = [k for k in required if not env[k]]
    if missing:
        sys.exit("Missing required configuration: " + ", ".join(missing))

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

    # Diagnostics: application permissions carried by the token (names only).
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    print("Token roles:", claims.get("roles", "(none)"))

    site_path = env["SHAREPOINT_SITE_PATH"].strip("/")
    site_url = (f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}:/{site_path}"
                if site_path else f"{GRAPH}/sites/{env['SHAREPOINT_HOSTNAME']}")
    site = call(site_url, headers=auth)
    drives = call(f"{GRAPH}/sites/{site['id']}/drives", headers=auth)["value"]
    drive = next((d for d in drives if d["name"].lower() == "documents"), None)
    if not drive:
        drive = call(f"{GRAPH}/sites/{site['id']}/drive", headers=auth)
    drive_id = drive["id"]
    print(f"Resolved drive: {drive.get('name')} ({drive_id})")

    targets = dict(FILES)
    try:
        children = call(item_path_url(drive_id, CSS_FOLDER) + ":/children", headers=auth)
        for child in children.get("value", []):
            if "file" in child:
                targets[f"brand-assets/css/{child['name']}"] = f"{CSS_FOLDER}/{child['name']}"
    except RuntimeError as e:
        print(f"WARN: could not list css folder: {e}")

    failures = []
    for dest, path in targets.items():
        try:
            download(drive_id, path, dest, auth)
        except RuntimeError as e:
            failures.append(f"{dest}: {e}")

    if failures:
        print("Failed downloads:\n  " + "\n  ".join(failures))
    if len(failures) == len(targets):
        sys.exit("All downloads failed")


if __name__ == "__main__":
    main()
