/**
 * Gmail → Monday.com Reading List
 *
 * Watches joellearningcenter@gmail.com for new emails and creates
 * items on your Monday.com "Reading List" board.
 *
 * Setup:
 *   1. Open script.google.com while signed in as joellearningcenter@gmail.com
 *   2. Create a new project, paste this file
 *   3. Fill in CONFIG below (API token + board ID)
 *   4. Run setupTrigger() once
 *   Done — it checks every 5 minutes automatically.
 */

// ============================================================
// CONFIGURATION — fill these in
// ============================================================
const CONFIG = {
  // Your Monday.com API token (from avatar → Administration → API)
  MONDAY_API_TOKEN: "YOUR_MONDAY_API_TOKEN_HERE",

  // Your Monday.com board ID (from the board URL: monday.com/boards/BOARD_ID)
  MONDAY_BOARD_ID: "YOUR_BOARD_ID_HERE",

  // Gmail label applied to processed emails (so we don't process twice)
  PROCESSED_LABEL: "AddedToMonday",

  // How many emails to process per run (stay under Apps Script limits)
  MAX_PER_RUN: 10,
};

// ============================================================
// MAIN — runs every 5 minutes via trigger
// ============================================================
function processNewEmails() {
  const label = getOrCreateLabel(CONFIG.PROCESSED_LABEL);
  const threads = GmailApp.search(
    "-label:" + CONFIG.PROCESSED_LABEL + " is:unread",
    0,
    CONFIG.MAX_PER_RUN
  );

  if (threads.length === 0) {
    Logger.log("No new emails to process.");
    return;
  }

  Logger.log("Processing " + threads.length + " email thread(s)...");

  for (const thread of threads) {
    const messages = thread.getMessages();
    const firstMsg = messages[0];

    const subject = firstMsg.getSubject() || "Untitled";
    const from = firstMsg.getFrom();
    const body = firstMsg.getPlainBody() || "";
    const date = firstMsg.getDate();

    // Extract URLs from the email body
    const urls = extractUrls(body);
    const firstUrl = urls.length > 0 ? urls[0] : "";

    // Check for PDF attachments
    const attachments = firstMsg.getAttachments();
    const pdfAttachments = attachments.filter(function (a) {
      return a.getContentType() === "application/pdf";
    });

    // Detect content type — PDF attachments always override to PDF
    const contentType = pdfAttachments.length > 0
      ? "PDF"
      : detectContentType(subject, body, firstUrl);

    // Create Monday.com item
    const created = createMondayItem(subject, contentType, firstUrl, date);

    if (created) {
      Logger.log("  + " + subject + " [" + contentType + "]");

      // If there are PDF attachments, add them as file updates
      for (const pdf of pdfAttachments) {
        addFileToMondayItem(created, pdf);
      }
    } else {
      Logger.log("  ! Failed: " + subject);
    }

    // Mark as processed
    thread.addLabel(label);
    thread.markRead();
  }

  Logger.log("Done. Processed " + threads.length + " thread(s).");
}

// ============================================================
// MONDAY.COM API
// ============================================================
function createMondayItem(title, contentType, sourceUrl, dateAdded) {
  // First, get column IDs
  const columns = getColumnIds();

  // Build column values
  const colValues = {};

  if (columns["Type"]) {
    colValues[columns["Type"]] = contentType;
  }

  if (columns["Source URL"] && sourceUrl) {
    colValues[columns["Source URL"]] = { url: sourceUrl, text: sourceUrl };
  }

  if (columns["Date Added"] && dateAdded) {
    const d = new Date(dateAdded);
    const dateStr =
      d.getFullYear() +
      "-" +
      String(d.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(d.getDate()).padStart(2, "0");
    colValues[columns["Date Added"]] = { date: dateStr };
  }

  const query =
    'mutation ($boardId: ID!, $itemName: String!, $colValues: JSON!) { ' +
    "create_item(board_id: $boardId, item_name: $itemName, column_values: $colValues) { id } }";

  const variables = {
    boardId: CONFIG.MONDAY_BOARD_ID,
    itemName: title,
    colValues: JSON.stringify(colValues),
  };

  const data = mondayQuery(query, variables);
  if (data && data.create_item) {
    return data.create_item.id;
  }
  return null;
}

function addFileToMondayItem(itemId, attachment) {
  // Monday.com file upload requires multipart form data
  // This adds a note with the filename instead (simpler, more reliable)
  const query =
    'mutation ($itemId: ID!, $body: String!) { ' +
    "create_update(item_id: $itemId, body: $body) { id } }";

  const variables = {
    itemId: itemId,
    body: "PDF attachment: " + attachment.getName(),
  };

  mondayQuery(query, variables);
}

function getColumnIds() {
  const query =
    "query ($boardId: [ID!]) { " +
    "boards(ids: $boardId) { columns { id title } } }";

  const data = mondayQuery(query, { boardId: [CONFIG.MONDAY_BOARD_ID] });
  const columns = {};

  if (data && data.boards && data.boards[0]) {
    for (const col of data.boards[0].columns) {
      columns[col.title] = col.id;
    }
  }

  return columns;
}

function mondayQuery(query, variables) {
  const payload = { query: query };
  if (variables) {
    payload.variables = variables;
  }

  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      Authorization: CONFIG.MONDAY_API_TOKEN,
      "API-Version": "2024-10",
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(
    "https://api.monday.com/v2",
    options
  );
  const result = JSON.parse(response.getContentText());

  if (result.errors) {
    Logger.log(
      "Monday.com API error: " +
        result.errors.map(function (e) { return e.message; }).join("; ")
    );
    return null;
  }

  return result.data;
}

// ============================================================
// HELPERS
// ============================================================
function extractUrls(text) {
  const urlRegex = /https?:\/\/[^\s<>"')\]]+/g;
  const matches = text.match(urlRegex);
  return matches || [];
}

function detectContentType(subject, body, url) {
  const combined = (subject + " " + body + " " + url).toLowerCase();

  // Audio indicators
  if (
    combined.includes("spotify.com") ||
    combined.includes("podcast") ||
    combined.includes("apple.com/podcast") ||
    combined.includes("earnings call") ||
    combined.includes("earnings-call") ||
    combined.includes(".mp3") ||
    combined.includes(".m4a")
  ) {
    return "AUDIO";
  }

  // PDF indicators
  if (
    combined.includes(".pdf") ||
    combined.includes("attached") ||
    combined.includes("whitepaper") ||
    combined.includes("report")
  ) {
    return "PDF";
  }

  // Default to LINK
  return "LINK";
}

function getOrCreateLabel(name) {
  let label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
  }
  return label;
}

// ============================================================
// TRIGGER MANAGEMENT
// ============================================================

/**
 * Run this function ONCE to set up the automatic 5-minute trigger.
 * Go to Run → setupTrigger in the Apps Script editor.
 */
function setupTrigger() {
  // Remove any existing triggers for this function
  const existing = ScriptApp.getProjectTriggers();
  for (const trigger of existing) {
    if (trigger.getHandlerFunction() === "processNewEmails") {
      ScriptApp.deleteTrigger(trigger);
    }
  }

  // Create a new time-based trigger that runs every 5 minutes
  ScriptApp.newTrigger("processNewEmails")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log("Trigger created! processNewEmails will run every 5 minutes.");
  Logger.log("You can close this tab — it runs automatically in the background.");
}

/**
 * Run this to stop the automatic checking.
 */
function removeTrigger() {
  const existing = ScriptApp.getProjectTriggers();
  let removed = 0;
  for (const trigger of existing) {
    if (trigger.getHandlerFunction() === "processNewEmails") {
      ScriptApp.deleteTrigger(trigger);
      removed++;
    }
  }
  Logger.log("Removed " + removed + " trigger(s). Auto-check is now off.");
}

/**
 * Run this manually to test with one email before enabling the trigger.
 */
function testOneEmail() {
  const threads = GmailApp.search("is:unread", 0, 1);
  if (threads.length === 0) {
    Logger.log("No unread emails found. Send yourself a test email first.");
    return;
  }
  const msg = threads[0].getMessages()[0];
  Logger.log("Subject: " + msg.getSubject());
  Logger.log("Body preview: " + msg.getPlainBody().substring(0, 200));

  const urls = extractUrls(msg.getPlainBody());
  Logger.log("URLs found: " + JSON.stringify(urls));

  const contentType = detectContentType(
    msg.getSubject(),
    msg.getPlainBody(),
    urls[0] || ""
  );
  Logger.log("Detected type: " + contentType);
  Logger.log("\nRun processNewEmails() to actually create the Monday.com item.");
}
