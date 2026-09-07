import { useState } from 'react';

const API_BASE = 'http://localhost:8000';


interface RunResponse {
  content: string;
  session_id: string | null;
  steel_session_id: string | null;
  viewer_url: string | null;
  warning: string | null;
}

async function runAgent(prompt:string, sessionId: string | null): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ prompt, session_id: sessionId ?? undefined }),
  });
  if (!res.ok) {
    throw new Error(`Server returned ${res.status}`);
  }
  return res.json();
}

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [content, setContent] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // agno's own conversation session — lets the model remember it was mid-task
  const [agnoSessionId, setAgnoSessionId] = useState<string | null>(null);
  // Steel's browser session — what the login popup and the resume call target
  const [steelSessionId, setSteelSessionId] = useState<string | null>(null);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);

  async function handleSubmit(promptText: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await runAgent(promptText, agnoSessionId);
      setContent(result.content);
      setWarning(result.warning);
      setAgnoSessionId(result.session_id);
      // Only replace these if this run actually surfaced a session — an
      // unrelated later run without steel_session_create shouldn't clear a
      // login popup you haven't dealt with yet.
      if (result.steel_session_id) setSteelSessionId(result.steel_session_id);
      if (result.viewer_url) setViewerUrl(result.viewer_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function openLoginPopup() {
    if (!viewerUrl) return;
    // interactive=true/showControls=true is the documented Steel Cloud flag
    // pair for a fully controllable embed. On self-hosted this may fall back
    // to a view-only session — worth testing directly against your instance.
    const url = `${viewerUrl}?interactive=true&showControls=true`;
    window.open(url, 'steel-login', 'width=520,height=760');
  }

  function handleContinueAfterLogin() {
    if (!steelSessionId) return;
    const resumePrompt = `I've logged in now. Please continue using Steel session ${steelSessionId}.`;
    setPrompt('');
    void handleSubmit(resumePrompt);
  }

  return (
    <div style={{ maxWidth: 720, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>Steel Surfer</h1>

      <form onSubmit={(e) => {
        e.preventDefault();
        void handleSubmit(prompt);
      }}
      >
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='Ask the agent to browse something...'
          rows={3}
          style={{ width: '100%'}}
        />
        <button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? 'Running...' : 'Send'}
        </button>
      </form>

      {error && <p style={{ color: 'crimson' }}>Error: {error}</p> }
      {warning && <p style={{ color: '#a35c00'}}>⚠️ {warning}</p>}

      {content && (
        <div style={{ whiteSpace: 'pre-wrap', marginTop: '1rem'}}>{content}</div>
      )}

      {viewerUrl && (
        <div
          style={{
            marginTop: '1.5rem',
            padding: '1rem',
            border: '1px solid #ddd',
            borderRadius: 8,
          }}
        >
          <p>
            The agent may need you to log in for this task. Open the live session, 
            sign in there, then click continue.
          </p>
          <button onClick={openLoginPopup}>Open login window</button>{' '}
          <button onClick={handleContinueAfterLogin} disabled={loading}>
            I've logged in - continue
          </button>
        </div>
      )}
    </div>
  );
}

