document.getElementById("save").addEventListener("click", () => {
    const token = document.getElementById("token").value.trim();
    const repo = document.getElementById("repo").value.trim();
  
    chrome.storage.sync.set({ token, repo }, () => {
      alert("Settings saved successfully!");
    });
  });
  