// Utility functions
const utils = {
  // Generate valid filename from problem title
  generateFileName: (title, language) => {
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
  },

  // Extract code from LeetCode editor
  extractCode: () => {
    // Monaco editor
    const monaco = document.querySelector('.monaco-editor');
    if (monaco) {
      const lines = monaco.querySelectorAll('.view-lines > div');
      if (lines.length > 0) {
        return Array.from(lines).map(line => line.innerText).join('\n');
      }
    }
    // Fallbacks
    const selectors = [
      '.view-lines',
      '.ace_content',
      '.CodeMirror-code',
      'pre code'
    ];
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && (el.innerText || el.textContent)) {
        return el.innerText || el.textContent;
      }
    }
    return '';
  },

  // Extract problem title
  extractTitle: () => {
    // Try all known selectors
    const selectors = [
      'a.text-title-large', // new LeetCode UI
      'h4.text-label',
      '[data-testid="question-title"]',
      '.question-title h3',
      'h1', 'h2', 'h3', 'h4',
      '.mr-2.text-label-1',
      '.title'
    ];
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && el.textContent) {
        // Remove problem number if present
        return el.textContent.replace(/^\d+\.\s*/, '').trim();
      }
    }
    // Fallback: extract from URL
    const urlMatch = window.location.pathname.match(/\/problems\/([^\/]+)/);
    if (urlMatch) {
      return urlMatch[1].split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
    return 'Unknown Problem';
  },

  // Extract programming language
  extractLanguage: () => {
    // Try the new selector for the language button
    const langBtn = document.querySelector('button.items-center.whitespace-nowrap');
    if (langBtn) {
      return langBtn.textContent.trim();
    }
    // ...existing fallback selectors...
    const selectors = [
      '.ant-select-selection-item',
      '[data-testid="language-selector"] .ant-select-selection-item',
      '.language-selector .ant-select-selection-item',
      '.select-language .ant-select-selection-item'
    ];
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element) {
        return element.textContent.trim();
      }
    }
    // Try to find language in other elements
    const languageElements = document.querySelectorAll('[class*="language"], [class*="lang"]');
    for (const element of languageElements) {
      const text = element.textContent.toLowerCase();
      if (text.includes('python') || text.includes('cpp') || text.includes('java') || 
          text.includes('javascript') || text.includes('typescript')) {
        return element.textContent.trim();
      }
    }
    return 'Unknown';
  }
};

// Monitor for submission results
class SubmissionMonitor {
  constructor() {
    this.isMonitoring = false;
    this.lastSubmissionTime = 0;
    this.init();
  }

  init() {
    // Start monitoring when page loads
    this.startMonitoring();
    
    // Re-start monitoring when navigating to different problems
    let currentUrl = window.location.href;
    setInterval(() => {
      if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        this.startMonitoring();
      }
    }, 1000);
  }

  startMonitoring() {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.observeSubmissionResults();
    this.observeSubmitButton();
  }

  observeSubmissionResults() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            this.checkForAcceptedSubmission(node);
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  observeSubmitButton() {
    // Monitor for submit button clicks
    document.addEventListener('click', (e) => {
      if (e.target.textContent?.toLowerCase().includes('submit') ||
          e.target.closest('[data-testid="submit-button"]') ||
          e.target.closest('.submit-button')) {
        this.lastSubmissionTime = Date.now();
      }
    });
  }

  checkForAcceptedSubmission(node) {
    // Check for "Accepted" status
    const acceptedSelectors = [
      '.text-success',
      '[data-testid="submission-status"]',
      '.submission-status',
      '.result-status'
    ];

    for (const selector of acceptedSelectors) {
      const elements = node.querySelectorAll ? node.querySelectorAll(selector) : [];
      for (const element of elements) {
        if (element.textContent?.toLowerCase().includes('accepted')) {
          // Only process if this is a recent submission
          if (Date.now() - this.lastSubmissionTime < 30000) { // 30 seconds
            this.processAcceptedSubmission();
            return;
          }
        }
      }
    }

    // Also check if the node itself contains "Accepted"
    if (node.textContent?.toLowerCase().includes('accepted')) {
      if (Date.now() - this.lastSubmissionTime < 30000) {
        this.processAcceptedSubmission();
      }
    }
  }

  async processAcceptedSubmission() {
    // Prevent multiple processing of the same submission
    if (this.processing) return;
    this.processing = true;

    // Wait a bit for the page to fully update
    setTimeout(async () => {
      try {
        const title = utils.extractTitle();
        const code = utils.extractCode();
        const language = utils.extractLanguage();

        console.log('Extracted title:', title);
        console.log('Extracted code:', code);
        console.log('Extracted language:', language);

        if (!title || !code) {
          console.log('LeetCode AutoCommit: Could not extract title or code');
          this.processing = false;
          return;
        }

        console.log('LeetCode AutoCommit: Detected accepted submission', {
          title,
          language,
          codeLength: code.length
        });

        // Send to background script
        chrome.runtime.sendMessage({
          type: 'SUBMISSION_ACCEPTED',
          data: {
            title,
            code,
            language,
            timestamp: Date.now()
          }
        });

      } catch (error) {
        console.error('LeetCode AutoCommit: Error processing submission', error);
      } finally {
        this.processing = false;
      }
    }, 2000);
  }
}

// Initialize the monitor
new SubmissionMonitor(); 
new SubmissionMonitor(); 