const SERVER = "http://127.0.0.1:24247";

// Right-click context menu: "Save link as PDF" and "Save page as PDF"
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "ReadLater: Save this page as PDF",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "save-link",
    title: "ReadLater: Save link as PDF",
    contexts: ["link"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "save-page") {
    saveUrl(tab.url, tab.title);
  } else if (info.menuItemId === "save-link") {
    saveUrl(info.linkUrl, null);
  }
});

function saveUrl(url, title) {
  fetch(`${SERVER}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title }),
  })
    .then((r) => r.json())
    .then((data) => {
      console.log("ReadLater:", data);
    })
    .catch((err) => {
      console.error(
        "ReadLater: Could not connect to server. Is 'readlater serve' running?",
        err
      );
    });
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "save-current") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (tab) {
        saveUrl(tab.url, tab.title);
        sendResponse({ status: "saving" });
      }
    });
    return true; // async response
  }

  if (msg.action === "save-email-html") {
    // The popup captured email HTML from the page
    fetch(`${SERVER}/save-html`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html: msg.html, title: msg.title }),
    })
      .then((r) => r.json())
      .then((data) => sendResponse(data))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (msg.action === "check-server") {
    fetch(`${SERVER}/status`)
      .then((r) => r.json())
      .then((data) => sendResponse({ connected: true, ...data }))
      .catch(() => sendResponse({ connected: false }));
    return true;
  }
});
