"""Run in the optional Playwright image with temporary pinned Mermaid assets mounted."""
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

text = Path('/README.md').read_text()
diagrams = re.findall(r'```mermaid\n(.*?)\n```', text, re.S)
assert len(diagrams) == 1
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox'])
    page = browser.new_page()
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path='/mermaid/mermaid.min.js')
    result = page.evaluate('''async (code) => {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
      const parsed = await mermaid.parse(code);
      const rendered = await mermaid.render('architecture', code);
      document.body.innerHTML = rendered.svg;
      return {diagramType: parsed.diagramType, nodes: document.querySelectorAll('.node').length,
              text: document.body.textContent};
    }''', diagrams[0])
    assert result['nodes'] == 13, result['nodes']
    for label in ['Spring Boot', 'Kafka', 'PostgreSQL', 'pgvector', 'Ollama',
                  'Prometheus', 'Grafana', 'Alertmanager', 'Python RAG', 'React']:
        assert label in result['text'], label
    print(json.dumps({'parser': 'mermaid 11.12.0', 'parsed_and_rendered': True,
                      'diagram_type': result['diagramType'], 'nodes': result['nodes'],
                      'limitation': 'Local parser/browser validation, not GitHub server-side rendering.'}, indent=2))
    browser.close()
