#!/usr/bin/env python3
"""Download REL brand assets and the loan-note statement workbook from
SharePoint via Microsoft Graph, for embedding into the financial model.

Runs in GitHub Actions (stdlib only). Auth is the same OAuth2
client-credentials flow as upload_to_sharepoint.py.

Required environment variables:
  AZURE_TENANT_ID       Entra tenant (directory) ID
  AZURE_CLIENT_ID       App registration (client) ID
  AZURE_CLIENT_SECRET   Client secret value
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.microsoft.com/v1.0"

# Default document library of the RELfinance SharePoint site.
DRIVE = "b!CuJhFtmdykeTy8o_bruvfvEc5gYQFvRNje5Xzg2KdGyGuV_djirWR6Xxexjtay2B"

# Item IDs resolved from the site's "11. 2026 Rebrand" website theme and the
# 3A Palace Green loan-note statement workbook.
ITEMS = {
    "brand-assets/rel-finance-logo.png": "013Q3WC5FF5OLKEQ743FFZHWIFQP7BQCDX",
    "brand-assets/rel-finance-logo-square.png": "013Q3WC5HUWEVPKH76INF2YUGEJKE6N4H4",
    "brand-assets/favicon-512.png": "013Q3WC5E6KBVMCBB4DVFYROOOHZIHDT5E",
    "brand-assets/Loan_Note_Schedules_New.xlsx": "013Q3WC5AQV3NBW6H6WFEJC2FUQ6FBP4OU",
}

# Website theme css folder — downloaded whole for the brand colour palette.
CSS_FOLDER = "013Q3WC5FNTRKB5ORHDFF2TGKQVSDXCBVW"


def call(url, data=None, headers=None, method=None, raw=False):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=120) as resp:
        body = resp.read()
    return body if raw else json.loads(body.decode())


def main():
    env = {k: os.environ.get(k, "").strip()
           for k in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")}
    missing = [k for k, v in env.items() if not v]
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

    targets = dict(ITEMS)
    try:
        children = call(f"{GRAPH}/drives/{DRIVE}/items/{CSS_FOLDER}/children", headers=auth)
        for child in children.get("value", []):
            if "file" in child:
                targets[f"brand-assets/css/{child['name']}"] = child["id"]
    except urllib.error.HTTPError as e:
        print(f"WARN: could not list css folder: HTTP {e.code}")

    failures = []
    for path, item_id in targets.items():
        try:
            content = call(f"{GRAPH}/drives/{DRIVE}/items/{item_id}/content",
                           headers=auth, raw=True)
        except urllib.error.HTTPError as e:
            failures.append(f"{path}: HTTP {e.code}")
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        print(f"Downloaded {path} ({len(content):,} bytes)")

    if failures:
        print("Failed downloads:\n  " + "\n  ".join(failures))
    if len(failures) == len(targets):
        sys.exit("All downloads failed")


if __name__ == "__main__":
    main()
