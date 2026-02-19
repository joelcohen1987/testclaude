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

### Forward-to-save (easiest email workflow)

You don't need a new email address. Gmail and Outlook both let you forward emails to
yourself with a special tag, and ReadLater will automatically pick them up.

**Gmail — use the `+` trick:**

Gmail ignores anything after a `+` in your address. So if your email is `jane@gmail.com`,
then `jane+readlater@gmail.com` goes to the same inbox. Set up a filter once:

1. In Gmail, go to Settings > Filters > Create new filter
2. Set "To" to `yourname+readlater@gmail.com`
3. Click "Create filter", check **Apply the label: ReadLater** and **Skip the inbox**
4. Done!

Now whenever you want to save an email: **forward it to `yourname+readlater@gmail.com`**.
ReadLater will automatically find it and convert it to PDF.

**Outlook:**

Outlook supports `+` addressing too. Forward emails to `yourname+readlater@outlook.com`
and set up a rule in Outlook to move those to a "ReadLater" folder.

### Automatic checking

Instead of manually running `readlater email`, you can have it check automatically:

```bash
# Check email every 5 minutes (also starts the Chrome extension server)
readlater watch --with-server

# Check every 2 minutes, Gmail only
readlater watch -i 2 -p gmail

# Set it to start automatically when your computer boots (never think about it again)
readlater autostart install

# To undo that
readlater autostart uninstall
```

### Manual email workflow tip

In Gmail, create a filter that applies the label `ReadLater` to emails you want to
collect (newsletters, saved articles, etc). The tool will look for that label by default.

## Chrome extension (one-click save from your browser)

This is the easiest way to use ReadLater. A button in your browser toolbar lets you save
any page — blog posts, Gmail emails, Outlook emails — with one click.

### Setup (one time)

1. Open Chrome and go to `chrome://extensions`
2. Turn on **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder from this project
5. You'll see a blue "R" icon appear in your toolbar

### Using it

1. **Start the server** — open a terminal and run:
   ```
   readlater serve
   ```
   Leave this running in the background. (The Chrome extension talks to this.)

2. **Save a webpage** — navigate to any page, click the blue "R" icon, click **Save This Page as PDF**.

3. **Save an email** — open an email in Gmail or Outlook (in Chrome), click the "R" icon, click **Save Email Content**. It grabs the email body and converts it to PDF.

4. **Right-click to save** — right-click on any page or link and choose **ReadLater: Save this page/link as PDF**.

### Desktop drag-and-drop (optional)

There are also scripts in the `desktop/` folder you can put on your desktop:

- **Mac**: `save-to-readlater.command` — double-click to open, or drag files onto it
- **Windows**: `save-to-readlater.bat` — same idea
- **Linux**: `save-to-readlater.desktop` — copy to your desktop for a drag target

## Unified dashboard (access from any device)

A mobile-friendly web page that shows your entire reading/listening list — PDFs,
audio, links — in one place. Open it on your phone, iPad, or desktop browser.

```bash
# Start the dashboard
readlater dashboard

# Start dashboard + Chrome extension server together
readlater dashboard --with-server
```

Then open `http://localhost:8247` on your computer, or `http://<your-computer-ip>:8247`
on your iPhone/iPad (must be on the same Wi-Fi).

**To add it to your iPhone home screen:** Open the URL in Safari, tap the Share button,
tap "Add to Home Screen". Now it looks and feels like an app.

### Syncing across devices with OneDrive

Point your reading folder to OneDrive so everything syncs automatically:

```bash
readlater config --reading-dir ~/OneDrive/ReadLater
```

Now your PDFs and library are available in the OneDrive app on every device.

## Audio and podcasts

Save Spotify podcasts, YouTube videos, earnings calls, or any audio:

```bash
# Spotify podcast episode
readlater add https://open.spotify.com/episode/...

# YouTube earnings call / interview
readlater add https://www.youtube.com/watch?v=...

# Direct audio file (gets downloaded)
readlater add https://example.com/earnings-call-q4.mp3
```

These show up in your dashboard alongside PDFs. Tapping opens them in the
right app (Spotify, YouTube, etc).

The Chrome extension handles these too — if you're on a Spotify or YouTube page,
click the "R" button and it saves the link to your list.

## Managing your reading list

```bash
# List everything (PDFs, audio, links)
readlater list

# Open the reading folder in your file manager
readlater open

# View or change config
readlater config --show
readlater config --reading-dir ~/OneDrive/ReadLater
```

## Supported input formats

| Source | How |
|---|---|
| Web URL | Renders the full page (JS included) to PDF |
| Email body | Converts to a nicely formatted PDF |
| PDF attachment | Saves directly |
| Spotify link | Saved as link, opens in Spotify app |
| YouTube link | Saved as link, opens in YouTube app |
| Audio file (.mp3, etc) | Downloaded to reading folder |
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
