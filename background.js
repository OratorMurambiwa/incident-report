// GitHub API handler
class GitHubAPI {
  constructor() {
    this.baseURL = 'https://api.github.com';
  }

  async commitFile(token, repo, branch, filePath, content, message) {
    const url = `${this.baseURL}/repos/${repo}/contents/${filePath}`;
    const encodedContent = btoa(unescape(encodeURIComponent(content)));
    let attempt = 1;
    let baseFilePath = filePath.replace(/(\.[^.]+)$/, '');
    let ext = filePath.match(/(\.[^.]+)$/) ? filePath.match(/(\.[^.]+)$/)[1] : '';
    while (attempt < 10) { // Try up to 10 unique filenames
      try {
        let createUrl = `${this.baseURL}/repos/${repo}/contents/${filePath}`;
        let response = await fetch(createUrl, {
          method: 'PUT',
          headers: {
            'Authorization': `token ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github.v3+json'
          },
          body: JSON.stringify({
            message: message,
            content: encodedContent,
            branch: branch
          })
        });
        let result = await response.json();
        if (response.status === 201) {
          // File created
          return result;
        } else if (response.status === 422 && result.message && result.message.includes('already exists')) {
          // File exists, try a new filename
          attempt++;
          filePath = `${baseFilePath}-${attempt}${ext}`;
          continue;
        } else if (!response.ok) {
          throw new Error(result.message || response.statusText);
        }
        return result;
      } catch (error) {
        if (attempt >= 10) throw error;
        attempt++;
        filePath = `${baseFilePath}-${attempt}${ext}`;
      }
    }
    throw new Error('Failed to create a unique file after 10 attempts');
  }

  async testConnection(token, repo) {
    const url = `${this.baseURL}/repos/${repo}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `token ${token}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      return response.ok;
    } catch (error) {
      console.error('Connection test failed:', error);
      return false;
    }
  }
}

// File name generator
class FileNameGenerator {
  static generateFileName(title, language) {
    const fileExtensions = {
      'python3': 'py',
      'python': 'py',
      'cpp': 'cpp',
      'c++': 'cpp',
      'java': 'java',
      'javascript': 'js',
      'js': 'js',
      'typescript': 'ts',
      'ts': 'ts',
      'go': 'go',
      'rust': 'rs',
      'swift': 'swift',
      'kotlin': 'kt',
      'scala': 'scala',
      'php': 'php',
      'ruby': 'rb',
      'c': 'c',
      'c#': 'cs',
      'csharp': 'cs'
    };

    const ext = fileExtensions[language.toLowerCase()] || 'txt';
    const fileName = title
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '') // Remove special characters
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/-+/g, '-') // Replace multiple hyphens with single
      .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens

    return `${fileName}.${ext}`;
  }
}

// Main handler
class LeetCodeAutoCommit {
  constructor() {
    this.githubAPI = new GitHubAPI();
    this.processingSubmissions = new Set(); // Prevent duplicate processing
  }

  async handleSubmission(data) {
    const { title, code, language, timestamp } = data;
    
    // Prevent duplicate processing
    const submissionKey = `${title}-${timestamp}`;
    if (this.processingSubmissions.has(submissionKey)) {
      return;
    }
    this.processingSubmissions.add(submissionKey);

    try {
      // Get settings
      const settings = await this.getSettings();
      
      if (!settings.autoCommit) {
        console.log('LeetCode AutoCommit: Auto-commit is disabled');
        return;
      }

      if (!settings.token || !settings.repo) {
        console.log('LeetCode AutoCommit: Missing GitHub token or repository');
        return;
      }

      // Generate file path
      const fileName = FileNameGenerator.generateFileName(title, language);
      const filePath = `${settings.folder}/${fileName}`;
      
      // Create commit message
      const commitMessage = `Add solution: ${title}`;

      console.log('LeetCode AutoCommit: Committing solution', {
        title,
        language,
        fileName,
        filePath
      });

      // Commit to GitHub
      const result = await this.githubAPI.commitFile(
        settings.token,
        settings.repo,
        settings.branch,
        filePath,
        code,
        commitMessage
      );

      console.log('GitHub API commit result:', result); // Log the full result

      // Only log the result, do not show notifications
      if (result && (result.content || result.commit)) {
        console.log('Solution committed successfully!', title ? `${title} has been added to your repository.` : 'A solution has been added to your repository.');
      } else if (result && result.message) {
        console.error('Commit failed', `GitHub API error: ${result.message}`);
      } else {
        console.error('Commit failed', 'Unknown error. Check extension logs for details.');
      }

    } catch (error) {
      console.error('LeetCode AutoCommit: Failed to commit solution', error);
      this.showNotification('Commit failed', `Error: ${error.message}`);
    } finally {
      // Clean up processing flag after a delay
      setTimeout(() => {
        this.processingSubmissions.delete(submissionKey);
      }, 5000);
    }
  }

  async getSettings() {
    return new Promise((resolve) => {
      chrome.storage.sync.get([
        'token',
        'repo',
        'branch',
        'folder',
        'autoCommit'
      ], (items) => {
        resolve({
          token: items.token || '',
          repo: items.repo || '',
          branch: items.branch || 'main',
          folder: items.folder || 'leetcode',
          autoCommit: items.autoCommit !== false // Default to true
        });
      });
    });
  }

  showNotification(title, message) {
    chrome.notifications.create({
      type: 'basic',
      title: title,
      message: message
    });
  }
}

// Initialize the handler
const handler = new LeetCodeAutoCommit();

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SUBMISSION_ACCEPTED') {
    handler.handleSubmission(message.data);
  }
});

// Handle installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('LeetCode AutoCommit extension installed');
    
    // Open options page or show welcome message
    chrome.tabs.create({
      url: chrome.runtime.getURL('popup.html')
    });
  }
}); 