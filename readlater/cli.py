"""CLI entry point for readlater."""

import argparse
import sys
from pathlib import Path

from readlater.config import configure_email, get_config, get_reading_dir, save_config


def main():
    parser = argparse.ArgumentParser(
        prog="readlater",
        description="Collect anything into a central PDF reading folder.",
    )
    sub = parser.add_subparsers(dest="command")

    # --- readlater add <url_or_file> [url_or_file ...] ---
    add_p = sub.add_parser("add", help="Add a URL or file to your reading list")
    add_p.add_argument("sources", nargs="+", help="URLs or file paths to save as PDF")
    add_p.add_argument("-n", "--name", help="Custom filename (only works with single source)")

    # --- readlater email ---
    email_p = sub.add_parser("email", help="Fetch reading material from configured email accounts")
    email_p.add_argument("-p", "--provider", choices=["gmail", "outlook"], help="Only fetch from this provider")
    email_p.add_argument("-m", "--max", type=int, default=20, help="Max emails to fetch (default: 20)")
    email_p.add_argument("--no-body", action="store_true", help="Skip converting email bodies to PDF")
    email_p.add_argument("--no-attachments", action="store_true", help="Skip saving PDF attachments")
    email_p.add_argument("--search", help="Custom IMAP search criteria (e.g. '(FROM \"newsletter@example.com\")')")

    # --- readlater config-email <provider> ---
    cfg_p = sub.add_parser("config-email", help="Configure email account credentials")
    cfg_p.add_argument("provider", choices=["gmail", "outlook"])
    cfg_p.add_argument("--email", required=True, help="Your email address")
    cfg_p.add_argument("--password", required=True, help="App password (not your main password)")
    cfg_p.add_argument("--label", default="ReadLater", help="Label/folder to filter (default: ReadLater)")

    # --- readlater config ---
    config_p = sub.add_parser("config", help="View or set configuration")
    config_p.add_argument("--reading-dir", help="Set the reading folder path")
    config_p.add_argument("--show", action="store_true", help="Print current config")

    # --- readlater list ---
    sub.add_parser("list", help="List PDFs in your reading folder")

    # --- readlater open ---
    open_p = sub.add_parser("open", help="Open the reading folder in your file manager")

    # --- readlater serve ---
    serve_p = sub.add_parser("serve", help="Start the local server (needed for the Chrome extension)")
    serve_p.add_argument("--port", type=int, default=24247, help="Port to listen on (default: 24247)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "add":
        cmd_add(args)
    elif args.command == "email":
        cmd_email(args)
    elif args.command == "config-email":
        cmd_config_email(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "open":
        cmd_open(args)
    elif args.command == "serve":
        cmd_serve(args)


def cmd_add(args):
    from readlater.ingest import ingest_file
    from readlater.web import fetch_url_to_pdf

    sources = args.sources
    name = args.name

    if name and len(sources) > 1:
        print("Error: --name can only be used with a single source.")
        sys.exit(1)

    for source in sources:
        print(f"Adding: {source}")
        try:
            if source.startswith("http://") or source.startswith("https://"):
                fetch_url_to_pdf(source, filename=name)
            else:
                ingest_file(source, filename=name)
        except Exception as e:
            print(f"  Error: {e}")


def cmd_email(args):
    from readlater.email_fetch import fetch_emails

    saved = fetch_emails(
        provider=args.provider,
        max_emails=args.max,
        save_body=not args.no_body,
        save_attachments=not args.no_attachments,
        search_criteria=args.search,
    )
    if saved:
        print(f"\nDone. {len(saved)} file(s) saved to {get_reading_dir()}")
    else:
        print("No files saved.")


def cmd_config_email(args):
    configure_email(args.provider, args.email, args.password, args.label)
    print(f"{args.provider} configured successfully.")
    if args.provider == "gmail":
        print(
            "\nNote: You need a Gmail App Password (not your regular password).\n"
            "Generate one at: https://myaccount.google.com/apppasswords"
        )
    elif args.provider == "outlook":
        print(
            "\nNote: You may need an Outlook App Password.\n"
            "Generate one at: https://account.microsoft.com/security"
        )


def cmd_config(args):
    import json

    config = get_config()
    if args.reading_dir:
        config["reading_dir"] = str(Path(args.reading_dir).expanduser().resolve())
        save_config(config)
        print(f"Reading directory set to: {config['reading_dir']}")
    if args.show or not args.reading_dir:
        # Redact passwords
        display = json.loads(json.dumps(config))
        for prov in display.get("email", {}).values():
            if isinstance(prov, dict) and prov.get("app_password"):
                prov["app_password"] = "****"
        print(json.dumps(display, indent=2))


def cmd_list(args):
    reading_dir = get_reading_dir()
    pdfs = sorted(reading_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {reading_dir}")
        return
    print(f"Reading folder: {reading_dir}\n")
    for i, pdf in enumerate(pdfs, 1):
        size_kb = pdf.stat().st_size / 1024
        print(f"  {i:3}. {pdf.name}  ({size_kb:.0f} KB)")
    print(f"\n{len(pdfs)} PDF(s) total.")


def cmd_open(args):
    import platform
    import subprocess

    reading_dir = get_reading_dir()
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(reading_dir)])
        elif system == "Linux":
            subprocess.run(["xdg-open", str(reading_dir)])
        elif system == "Windows":
            subprocess.run(["explorer", str(reading_dir)])
        else:
            print(f"Open this folder manually: {reading_dir}")
    except Exception:
        print(f"Could not open folder. Path: {reading_dir}")


def cmd_serve(args):
    from readlater.server import run_server

    run_server(port=args.port)


if __name__ == "__main__":
    main()
