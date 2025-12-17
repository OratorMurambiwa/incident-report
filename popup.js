// Load saved settings when popup opens
document.addEventListener('DOMContentLoaded', () => {
  chrome.storage.sync.get([
    'token', 
    'repo', 
    'branch', 
    'folder', 
    'autoCommit'
  ], (items) => {
    if (items.token) document.getElementById('token').value = items.token;
    if (items.repo) document.getElementById('repo').value = items.repo;
    if (items.branch) document.getElementById('branch').value = items.branch;
    if (items.folder) document.getElementById('folder').value = items.folder;
    if (items.autoCommit !== undefined) document.getElementById('autoCommit').checked = items.autoCommit;
  });
});

// Save settings
document.getElementById('save').addEventListener('click', () => {
  const settings = {
    token: document.getElementById('token').value,
    repo: document.getElementById('repo').value,
    branch: document.getElementById('branch').value || 'main',
    folder: document.getElementById('folder').value || 'leetcode',
    autoCommit: document.getElementById('autoCommit').checked
  };

  chrome.storage.sync.set(settings, () => {
    showStatus('Settings saved successfully!', 'success');
  });
});

// Test GitHub connection
document.getElementById('test').addEventListener('click', async () => {
  const token = document.getElementById('token').value;
  const repo = document.getElementById('repo').value;
  
  if (!token || !repo) {
    showStatus('Please enter both token and repository', 'error');
    return;
  }

  try {
    const response = await fetch(`https://api.github.com/repos/${repo}`, {
      headers: {
        'Authorization': `token ${token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });

    if (response.ok) {
      showStatus('Connection successful! Repository found.', 'success');
    } else {
      showStatus('Connection failed. Check your token and repository name.', 'error');
    }
  } catch (error) {
    showStatus('Network error. Please check your internet connection.', 'error');
  }
});

function showStatus(message, type) {
  const statusEl = document.getElementById('status');
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.style.display = 'block';
  
  setTimeout(() => {
    statusEl.style.display = 'none';
  }, 3000);
} 