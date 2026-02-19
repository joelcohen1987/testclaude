const statusEl = document.getElementById("status");
const feedbackEl = document.getElementById("feedback");
const savePageBtn = document.getElementById("save-page");
const saveEmailBtn = document.getElementById("save-email");

// Check if local server is running
chrome.runtime.sendMessage({ action: "check-server" }, (res) => {
  if (res && res.connected) {
    statusEl.textContent = "Server running — ready to save";
    statusEl.className = "status connected";
  } else {
    statusEl.textContent =
      'Server not running. Open a terminal and run: readlater serve';
    statusEl.className = "status disconnected";
    savePageBtn.disabled = true;
    saveEmailBtn.disabled = true;
  }
});

// "Save This Page" button
savePageBtn.addEventListener("click", () => {
  feedbackEl.textContent = "Saving...";
  chrome.runtime.sendMessage({ action: "save-current" }, (res) => {
    feedbackEl.textContent = "Sent to ReadLater! PDF will appear in your Reading folder.";
    setTimeout(() => window.close(), 2000);
  });
});

// "Save Email Content" — grabs the visible email body from Gmail/Outlook web
saveEmailBtn.addEventListener("click", () => {
  feedbackEl.textContent = "Capturing email...";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];

    chrome.scripting.executeScript(
      {
        target: { tabId: tab.id },
        func: captureEmailContent,
      },
      (results) => {
        if (chrome.runtime.lastError) {
          feedbackEl.textContent = "Could not access page content.";
          return;
        }

        const result = results[0]?.result;
        if (result && result.html) {
          chrome.runtime.sendMessage(
            {
              action: "save-email-html",
              html: result.html,
              title: result.title,
            },
            (res) => {
              feedbackEl.textContent =
                "Email captured! PDF will appear in your Reading folder.";
              setTimeout(() => window.close(), 2000);
            }
          );
        } else {
          feedbackEl.textContent =
            "No email content detected. Try 'Save This Page' instead.";
        }
      }
    );
  });
});

// This function runs IN the web page to grab email content
function captureEmailContent() {
  // Gmail: the email body is in a div with class "a3s" or similar
  let emailEl =
    document.querySelector(".a3s.aiL") || // Gmail email body
    document.querySelector('[role="main"] .a3s') || // Gmail alt
    document.querySelector('[aria-label="Message body"]') || // Outlook web
    document.querySelector(".ReadMsgBody") || // Outlook web alt
    document.querySelector('[data-testid="message-view-body"]'); // Outlook new

  if (emailEl) {
    // Also grab the subject line
    let subject =
      document.querySelector('h2[data-thread-perm-id]')?.textContent || // Gmail
      document.querySelector('[role="heading"]')?.textContent || // Outlook
      document.title;

    return {
      html:
        "<html><body>" +
        "<h1>" + (subject || "Email") + "</h1>" +
        emailEl.outerHTML +
        "</body></html>",
      title: subject || "email",
    };
  }

  // Fallback: grab the whole page
  return null;
}
