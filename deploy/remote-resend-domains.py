#!/usr/bin/env python3
"""Inspect the Resend account: list domains and their DNS records.

Run on the EC2 instance (the Resend API key lives in backend/.env there).
Prints every domain with its verification status and the exact DNS records
Resend expects, so they can be added at the registrar.
"""
import json
import urllib.request

ENV = "/home/ubuntu/ticket-fox-web/backend/.env"


def read_key() -> str:
    try:
        with open(ENV, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("RESEND_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        return ""
    return ""


def api(path: str, key: str) -> dict:
    req = urllib.request.Request(
        f"https://api.resend.com{path}",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "TicketFox/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:400]
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def main() -> None:
    key = read_key()
    if not key:
        print("RESEND_API_KEY is not set in backend/.env")
        return
    print(f"key prefix: {key[:6]}...  (len={len(key)})")

    try:
        data = api("/domains", key)
    except Exception as exc:  # noqa: BLE001
        print(f"Resend API call failed: {type(exc).__name__}: {exc}")
        return

    domains = data.get("data", [])
    if not domains:
        print("No domains registered in this Resend account.")
        return

    for d in domains:
        print(f"\n== {d.get('name')}  status={d.get('status')}  id={d.get('id')}  region={d.get('region')}")
        try:
            detail = api(f"/domains/{d.get('id')}", key)
        except Exception as exc:  # noqa: BLE001
            print(f"   (detail failed: {exc})")
            continue
        for r in detail.get("records", []):
            print(
                f"   {str(r.get('type')):5} {str(r.get('name')):44} -> "
                f"{r.get('value')}   [{r.get('status')}]"
            )


if __name__ == "__main__":
    main()
