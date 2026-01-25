import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Pie, Bar } from 'react-chartjs-2';
import 'chart.js/auto';
import './App.css';

function App() {
  const [summary, setSummary] = useState(null);
  const [reportUrl, setReportUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(5);
  const [preview, setPreview] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const previewCloseRef = useRef(null);
  const fileInputRef = useRef(null);

  const uploadFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('http://127.0.0.1:8000/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setSummary(res.data.data);
      setReportUrl(res.data.report);
      await fetchHistory();
    } catch (err) {
      console.error(err);
      alert('Upload failed. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (p = 1) => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/datasets/', { params: { page: p, page_size: pageSize } });
      setHistory(res.data.items || []);
      setTotal(res.data.total || 0);
      setPage(res.data.page || p);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  React.useEffect(() => { fetchHistory(); }, []);

  useEffect(() => {
    if (previewOpen && previewCloseRef.current) {
      previewCloseRef.current.focus();
    }
  }, [previewOpen]);

  const openPreview = async (id) => {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/datasets/${id}/preview/`);
      setPreview(res.data);
      setPreviewOpen(true);
    } catch (err) {
      console.error('Preview failed', err);
      alert('Preview failed');
    }
  };

  const renderCharts = () => {
    if (!summary) return null;

    const typeDist = summary.type_distribution || {};
    const pieData = {
      labels: Object.keys(typeDist),
      datasets: [
        {
          data: Object.values(typeDist),
          backgroundColor: ['#4dc9f6', '#f67019', '#f53794', '#537bc4', '#acc236'],
        },
      ],
    };

    const barData = {
      labels: ['Avg Pressure', 'Avg Temperature'],
      datasets: [
        {
          label: 'Averages',
          data: [summary.average_pressure || 0, summary.average_temperature || 0],
          backgroundColor: ['#36a2eb', '#ff6384'],
        },
      ],
    };

    return (
      <div className="charts">
        <div className="chart-card">
          <h3>Type Distribution</h3>
          <Pie data={pieData} />
        </div>
        <div className="chart-card">
          <h3>Averages</h3>
          <Bar data={barData} />
        </div>
      </div>
    );
  };

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="brand">Chemical Equipment Visualizer</div>
      </header>

      <main className="container">
        <section className="upload-card">
          <h2>Upload CSV</h2>
          <p className="muted">Upload a CSV with columns: Equipment Name, Type, Flowrate, Pressure, Temperature</p>
          <label className="file-input" role="button" tabIndex={0} aria-label="Choose CSV file">
            <input ref={fileInputRef} type="file" accept=".csv" onChange={uploadFile} aria-label="CSV file input" />
            <span onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }} onClick={() => fileInputRef.current?.click()}>{loading ? 'Uploading...' : 'Choose CSV file'}</span>
          </label>
          {summary && (
            <div className="summary">
              <div><strong>Total Rows:</strong> {summary.total_rows}</div>
              <div><strong>Avg Pressure:</strong> {summary.average_pressure}</div>
              <div><strong>Avg Temperature:</strong> {summary.average_temperature}</div>
              {reportUrl && <a href={reportUrl} target="_blank" rel="noreferrer">Download report (PDF)</a>}
            </div>
          )}
        </section>

        {renderCharts()}

        <aside className="chart-card" style={{gridColumn: '2/3'}}>
          <h3>Recent Uploads</h3>
          <div>
            {history.length === 0 && <div className="muted">No uploads yet</div>}
            {history.map((item) => (
              <div key={item.id} style={{padding:'8px 0', borderBottom:'1px solid #f1f5f9'}}>
                <div style={{display:'flex', justifyContent:'space-between'}}>
                  <div style={{fontWeight:600}}>{item.filename}</div>
                  <div style={{fontSize:12, color:'#6b7280'}}>{new Date(item.uploaded_at).toLocaleString()}</div>
                </div>
                <div style={{marginTop:6, display:'flex', gap:8}}>
                  <button aria-label={`Load ${item.filename}`} onClick={() => { setSummary(item.summary); setReportUrl(item.report_url); }} style={{padding:'6px 8px', borderRadius:6}}>Load</button>
                  <button aria-label={`Preview ${item.filename}`} onClick={() => openPreview(item.id)} style={{padding:'6px 8px', borderRadius:6}}>Preview</button>
                  {item.report_url && <a aria-label={`Open PDF for ${item.filename}`} href={item.report_url} target="_blank" rel="noreferrer" style={{padding:'6px 8px', background:'#0b69ff', color:'#fff', borderRadius:6, textDecoration:'none'}}>PDF</a>}
                </div>
              </div>
            ))}

            <div style={{display:'flex', justifyContent:'space-between', marginTop:12}}>
              <button onClick={() => fetchHistory(Math.max(1, page - 1))} disabled={page <= 1}>Previous</button>
              <div style={{fontSize:12, color:'#6b7280'}}>Page {page} — {total} items</div>
              <button onClick={() => fetchHistory(page + 1)} disabled={page * pageSize >= total}>Next</button>
            </div>
          </div>
        </aside>
      </main>

      {previewOpen && (
        <div className="modal-backdrop" onClick={() => setPreviewOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>CSV Preview</h3>
            <div style={{maxHeight:300, overflow:'auto'}}>
              <table style={{width:'100%', borderCollapse:'collapse'}}>
                <thead>
                  <tr>
                    {preview.columns.map((c) => <th key={c} style={{borderBottom:'1px solid #e6eef6', textAlign:'left', padding:6}}>{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r, i) => (
                    <tr key={i}>
                      {preview.columns.map((c) => <td key={c} style={{padding:6, borderBottom:'1px solid #f1f5f9'}}>{String(r[c] ?? '')}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{marginTop:12, textAlign:'right'}}>
              <button ref={previewCloseRef} aria-label="Close preview" onClick={() => setPreviewOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">Built for demo — upload CSV to visualize data.</footer>
    </div>
  );
}

export default App;
