# readlater

Collect anything you want to read into a single folder, all as PDFs.

## Install

```bash
pip install -e ".[all]"

# Install the browser engine for best web-to-PDF quality
python -m playwright install chromium
```

## Quick start

```bash
# Save a blog post as PDF
readlater add https://example.com/interesting-article

# Save multiple URLs at once
readlater add https://blog.example.com/post1 https://news.example.com/story

# Save a local file (HTML, Markdown, Word doc, image, epub, or existing PDF)
readlater add ~/Downloads/report.docx
readlater add notes.md

# Give it a custom name
readlater add https://example.com/post -n "weekend-reading"
```

## Email setup

Configure Gmail and/or Outlook to pull in reading material from your inbox:

```bash
# Gmail (requires an App Password — https://myaccount.google.com/apppasswords)
readlater config-email gmail --email you@gmail.com --password your-app-password

# Outlook
readlater config-email outlook --email you@outlook.com --password your-app-password

# Fetch unread emails (saves bodies as PDF + extracts PDF attachments)
readlater email

# Only Gmail, max 10
readlater email -p gmail -m 10

# Custom IMAP search
readlater email --search '(FROM "newsletter@example.com")'
```

### Email workflow tip

In Gmail, create a filter that applies the label `ReadLater` to emails you want to
collect (newsletters, saved articles, etc). The tool will look for that label by default.

## Managing your reading list

```bash
# List everything in your reading folder
readlater list

# Open the reading folder in your file manager
readlater open

# View or change config
readlater config --show
readlater config --reading-dir ~/Dropbox/ReadingList
```

## Supported input formats

| Source | How |
|---|---|
| Web URL | Renders the full page (JS included) to PDF |
| Email body | Converts to a nicely formatted PDF |
| PDF attachment | Saves directly |
| `.html` / `.htm` | Renders to PDF |
| `.md` | Converts Markdown → PDF |
| `.txt` | Wraps in readable layout → PDF |
| `.docx` / `.doc` | Converts via LibreOffice |
| `.epub` | Converts via Calibre |
| `.png`, `.jpg`, etc | Embeds in PDF |

## PDF rendering priority

The tool tries renderers in this order:

1. **Playwright + Chromium** — best quality, handles JavaScript-heavy pages
2. **wkhtmltopdf** — fast, good for simple pages
3. **WeasyPrint** — pure Python fallback, no external binary needed

Install at least one. Playwright is recommended for best results.

## Config

Config lives at `~/.readlater/config.json`. PDFs go to `~/Reading/` by default.
