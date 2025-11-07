// background.js

// --- Upload helper function ---
async function uploadToGitHub(data, token, repo) {
    try {
      // create a unique filename per problem
      const fileName = `${data.title.replace(/\s+/g, "_")}_${Date.now()}.py`;
      const path = `leetcode/${fileName}`;
  
      // encode the file content in Base64
      const content = btoa(
        `# ${data.title}\n# ${data.url}\n# Language: ${data.language}\n# Difficulty: ${data.difficulty}\n\n${data.code}`
      );
  
      // make the API request to GitHub
      const res = await fetch(`https://api.github.com/repos/${repo}/contents/${path}`, {
        method: "PUT",
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github.v3+json",
        },
        body: JSON.stringify({
          message: `Add ${data.title}`,
          content,
        }),
      });
  
      const result = await res.json();
  
      if (!res.ok) {
        console.error("Upload failed:", result);
      } else {
        console.log("Uploaded successfully:", result.content?.path);
      }
    } catch (err) {
      console.error("Error uploading:", err);
    }
  }
  
  // --- Listen for messages from content.js ---
  chrome.runtime.onMessage.addListener(async (message) => {
    if (message.action === "upload") {
      const { data } = message;
  
      // get stored token and repo
      const { token, repo } = await chrome.storage.sync.get(["token", "repo"]);
  
      if (!token || !repo) {
        console.warn("Missing GitHub token or repo in storage.");
        return;
      }
  
      await uploadToGitHub(data, token, repo);
    }
  });
  
  // --- Automatically trigger upload after successful LeetCode submission ---
  chrome.webRequest.onCompleted.addListener(
    async (details) => {
      if (
        details.url.includes("/submissions/detail/") &&
        details.url.endsWith("/check/")
      ) {
        console.log("📡 Submission detected:", details.url);
        // tell content.js to capture code and send it
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          chrome.tabs.sendMessage(tabs[0].id, "manual-upload");
        });
      }
    },
    { urls: [
        "https://leetcode.com/*", 
        "https://neetcode.io/* "
        ] 
    }
  );
  