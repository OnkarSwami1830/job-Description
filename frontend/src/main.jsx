import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, Download, FileUp, LoaderCircle, LogOut, Save, Sparkles, UploadCloud } from 'lucide-react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const sample = 'Infosys is hiring a Full Stack Developer in Pune. Build products with Java, Spring Boot, React, AWS, MySQL and Docker. Candidates need 2-4 years of experience, a B.Tech degree, strong communication, and a salary of 6-12 LPA.';

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('talentlens_token'));
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [improved, setImproved] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [resume, setResume] = useState('');
  const [resumeReview, setResumeReview] = useState('');
  const [reviewBusy, setReviewBusy] = useState(false);

  if (!token) return <AuthPage onAuth={session => { localStorage.setItem('talentlens_token', session.token); setToken(session.token); }} />;

  async function callApi(path, body, file = false) {
    const authHeaders = { Authorization: `Bearer ${token}` };
    const options = file ? { method: 'POST', headers: authHeaders, body } : { method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const response = await fetch(`${API}${path}`, options);
    if (!response.ok) throw new Error((await response.json()).detail || 'Request failed');
    return response.json();
  }
  async function analyze() {
    if (text.trim().length < 20) { setError('Add a fuller job description before analyzing.'); return; }
    setBusy(true); setError(''); setSaved(false);
    try { setResult(await callApi('/analyze', { job_description: text })); setImproved(''); } catch (err) { setError(`${err.message}. Is the FastAPI server running?`); } finally { setBusy(false); }
  }
  async function improve() {
    setBusy(true); setError('');
    try { const data = await callApi('/improve', { job_description: text }); setResult(data.analysis); setImproved(data.improved_description); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function reviewResume() {
    if (resume.trim().length < 40) { setError('Add the resume text before requesting a review.'); return; }
    setReviewBusy(true); setError('');
    try { const data = await callApi('/resume/review', { resume, job_description: text || null }); setResumeReview(data.review); } catch (err) { setError(err.message); } finally { setReviewBusy(false); }
  }
  async function upload(event) {
    const file = event.target.files?.[0]; if (!file) return;
    setBusy(true); setError(''); const form = new FormData(); form.append('file', file);
    try { setResult(await callApi('/upload', form, true)); setText(`Analyzed file: ${file.name}`); } catch (err) { setError(err.message); } finally { setBusy(false); event.target.value = ''; }
  }
  async function save() { try { await callApi('/jobs', { job_description: text }); setSaved(true); } catch (err) { setError(err.message); } }
  function download() { const blob = new Blob([JSON.stringify({ ...result, improved_description: improved || undefined }, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'job-analysis.json'; link.click(); URL.revokeObjectURL(url); }

  return <main className="shell">
    <nav><div className="brand"><span className="brand-mark"><Sparkles size={17} /></span> TalentLens <span className="beta">ATS / LIVE</span></div><div className="nav-right"><span className="status"><span className="pulse" /> Analyzer online</span><button className="logout" onClick={() => { localStorage.removeItem('talentlens_token'); setToken(null); }}><LogOut size={14} /> Sign out</button></div></nav>
    <section className="hero"><div className="eyebrow">RECRUITING INTELLIGENCE / 01</div><h1>Make every brief<br /><em>hireable.</em></h1><p>Turn a rough job description into structured signals, a quality score, and recruiter-ready copy.</p></section>
    <section className="workspace"><div className="input-panel"><div className="panel-head"><div><span className="kicker">01 / EDITOR</span><h2>Drop in your JD</h2></div><label className="upload"><FileUp size={16} /> Upload<input type="file" accept=".pdf,.docx,.txt" onChange={upload} /></label></div><textarea value={text} onChange={event => setText(event.target.value)} placeholder="Paste a job description here..." /><div className="input-foot"><button className="sample" onClick={() => setText(sample)}>Use sample JD</button><span>{text.length.toLocaleString()} characters</span><button className="analyze" onClick={analyze} disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{busy ? 'Working' : 'Analyze JD'}</button></div><div className="resume-tool"><div><span className="kicker">03 / RESUME REVIEW</span><h2>Review a resume</h2><p>Get strengths, gaps, recommendations, and a resume-ready summary.</p></div><textarea value={resume} onChange={event => setResume(event.target.value)} placeholder="Paste resume text here..." /><button className="analyze" onClick={reviewResume} disabled={reviewBusy}>{reviewBusy ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{reviewBusy ? 'Reviewing' : 'Summarize review'}</button>{resumeReview && <pre className="review-output">{resumeReview}</pre>}</div>{error && <div className="error">{error}</div>}</div>
      <div className="results-panel"><div className="panel-head"><div><span className="kicker">02 / ATS SIGNALS</span><h2>Analysis results</h2></div>{result && <div className="actions"><button className="icon-button" onClick={save}><Save size={16} /> {saved ? 'Saved' : 'Save'}</button><button className="icon-button" onClick={download}><Download size={16} /> JSON</button></div>}</div>{result ? <Results result={result} improved={improved} onImprove={improve} busy={busy} /> : <div className="empty"><div className="empty-icon"><UploadCloud size={24} /></div><strong>Your signals will appear here.</strong><span>Role, skills, score, gaps and<br />recommendations in one view.</span></div>}</div></section>
    <footer><span>AI-assisted · Human-led</span><span>Local workspace / v1</span></footer>
  </main>;
}
function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const response = await fetch(`${API}/auth/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not authenticate');
      onAuth(data);
    } catch (err) { setError(`${err.message}. Is MongoDB running?`); } finally { setBusy(false); }
  }

  return <main className="auth-shell"><div className="auth-art"><div className="brand"><span className="brand-mark"><Sparkles size={17} /></span> TalentLens</div><div className="auth-message"><span className="eyebrow">RECRUITING INTELLIGENCE / 01</span><h1>Make every brief<br /><em>hireable.</em></h1><p>Turn rough job descriptions into structured signals and recruiter-ready copy.</p></div><span className="auth-caption">AI-assisted · Human-led</span></div><section className="auth-card"><div className="auth-card-head"><span className="kicker">PRIVATE WORKSPACE</span><h2>{mode === 'login' ? 'Welcome back.' : 'Create your workspace.'}</h2><p>{mode === 'login' ? 'Sign in to continue analyzing your roles.' : 'Save analyses and keep your hiring work in one place.'}</p></div><form onSubmit={submit}><label>Email address<input type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@company.com" required /></label><label>Password<input type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters" minLength="8" required /></label>{error && <div className="error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}{busy ? 'Connecting' : mode === 'login' ? 'Enter TalentLens' : 'Create account'}</button></form><button className="auth-switch" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Need an account? Create one' : 'Already have an account? Sign in'}</button></section></main>;
}
function Results({ result, improved, onImprove, busy }) {
  const scores = [['Completeness', result.quality.completeness], ['Skill coverage', result.quality.skill_coverage], ['Clarity', result.quality.clarity], ['Inclusion', result.quality.diversity_inclusion]];
  return <div className="result-content"><div className="role-card"><div><span className="label">RECOMMENDED ROLE</span><strong>{result.job_title || result.job_role}</strong><div className="confidence"><CheckCircle2 size={15} /> {result.confidence}% extraction confidence</div></div><div className="score"><b>{result.jd_score}</b><span>/ 100<br />JD SCORE</span></div></div><div className="metrics"><Metric label="Experience" value={result.experience} /><Metric label="Salary" value={result.salary} /><Metric label="Work mode" value={result.work_mode} /><Metric label="Education" value={result.education} /></div><div className="quality"><div className="section-head"><span className="label">QUALITY BREAKDOWN</span><span>{result.quality.overall}/100 overall</span></div>{scores.map(([name, value]) => <div className="bar-row" key={name}><span>{name}</span><div><i style={{ width: `${value}%` }} /></div><b>{value}</b></div>)}</div><div className="skills"><span className="label">DETECTED SKILLS <b>{result.skills.length}</b></span><div className="chips">{result.skills.map(skill => <span key={skill}>{skill}</span>)}</div></div><div className="insights"><div><span className="label">MISSING SECTIONS</span>{result.missing_sections.length ? result.missing_sections.map(section => <p key={section}>+ {section}</p>) : <p className="good">Complete coverage</p>}</div><div><span className="label">RECOMMENDATIONS</span>{result.ai_recommendations.slice(0, 3).map(item => <p key={item}>+ {item}</p>)}</div></div><button className="improve" onClick={onImprove} disabled={busy}><Sparkles size={16} /> {improved ? 'Regenerate improved JD' : 'Improve this JD'}</button>{improved && <div className="improved"><span className="label">AI-GENERATED SECTIONS</span><pre>{improved}</pre></div>}</div>;
}
function Metric({ label, value }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
createRoot(document.getElementById('root')).render(<App />);
