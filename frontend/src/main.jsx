import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

createRoot(document.getElementById('root')).render(
  <main>
    <p className="eyebrow">LOCAL INCIDENT INTELLIGENCE</p>
    <h1>IncidentIQ</h1>
    <p>Monitor incidents. Find context. Respond with confidence.</p>
    <section><h2>Workspace initialized</h2>
      <p>Infrastructure and application scaffolds are ready for development.</p>
      <p>Live incident ingestion and AI analysis have not been connected yet.</p>
    </section>
  </main>
);
