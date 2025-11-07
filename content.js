// content.js

// --- Helper: collect problem data ---
function getProblemData() {
    const url = window.location.href;
    let title = "Untitled";
    let code = "";
    let language = "Unknown";
    let difficulty = "Unknown";
  
    // --- Detect if we're on LeetCode or NeetCode ---
    const isLeetCode = url.includes("leetcode.com");
    const isNeetCode = url.includes("neetcode.io");
  
    if (isLeetCode) {
      // LeetCode layout
      title = document.querySelector("h1")?.innerText?.trim() || "Untitled";
  
      // LeetCode editor uses a hidden textarea under .monaco-editor
      const codeBox = document.querySelector(".monaco-editor textarea");
      code = codeBox ? codeBox.value : "";
  
      // language dropdown (top of editor)
      language =
        document.querySelector("span[class*='ant-select-selection-item']")
          ?.innerText || "Unknown";
  
      // difficulty badge (top right corner)
      difficulty =
        document.querySelector("div[class*='text-difficulty']")
          ?.innerText ||
        document.querySelector("div[class*='css-10o4wqw']")
          ?.innerText ||
        "Unknown";
    } else if (isNeetCode) {
      // NeetCode layout
      title =
        document.querySelector("h1")?.innerText?.trim() ||
        document.querySelector(".font-bold")?.innerText?.trim() ||
        "Untitled";
  
      // Code editor (simpler DOM)
      const codeBox =
        document.querySelector("textarea") ||
        document.querySelector(".cm-content");
      code = codeBox ? codeBox.value || codeBox.innerText || "" : "";
  
      // Default since NeetCode doesn't show language/difficulty like LeetCode
      language = "Python";
      difficulty = "Unspecified";
    }
  
    return { title, code, url, language, difficulty };
  }
  
  // --- Listen for background.js trigger ---
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg === "manual-upload") {
      console.log("Upload signal received — collecting problem data...");
      const data = getProblemData();
      chrome.runtime.sendMessage({ action: "upload", data });
    }
  });
  
  // --- Optional manual backup: detect 'Submit' clicks ---
  document.addEventListener("click", async (e) => {
    if (e.target.innerText && e.target.innerText.includes("Submit")) {
      setTimeout(async () => {
        const data = getProblemData();
        chrome.runtime.sendMessage({ action: "upload", data });
      }, 3000);
    }
  });
  