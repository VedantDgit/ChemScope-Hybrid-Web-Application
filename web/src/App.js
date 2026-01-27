import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Pie, Bar } from 'react-chartjs-2';
import 'chart.js/auto';
import History from './History';
import './App.css';

function App() {
  /* ---------------- STATES ---------------- */
  const [darkMode, setDarkMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const [summary, setSummary] = useState(null);
  const [reportUrl, setReportUrl] = useState(null);
  const [history, setHistory] = useState([]);

  const fileInputRef = useRef(null);

  /* ---------------- TAB TITLE ---------------- */
  useEffect(() => {
    document.title = 'Chemical Equipment Visualizer';
  }, []);

  /* ---------------- FETCH LAST 5 HISTORY ---------------- */
  const fetchHistory = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/datasets/', {
        params: { page: 1, page_size: 5 },
      });
      setHistory(res.data.items || []);
    } catch (err) {
      console.error('History fetch failed', err);
      setHistory([]);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  /* ---------------- UPLOAD ---------------- */
  const uploadFile = async (e) => {
    const file = e?.target?.files?.[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(
        'http://127.0.0.1:8000/upload/',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      setSummary(res.data?.data || null);
      setReportUrl(res.data?.report || null);
      fetchHistory();
    } catch (err) {
      console.error(err);
      alert('Upload failed (check backend logs)');
    } finally {
      setLoading(false);
    }
  };

  /* ---------------- DRAG & DROP ---------------- */
  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);

    const file = e.dataTransfer?.files?.[0];
    if (!file) return;

    uploadFile({ target: { files: [file] } });
  };

  /* ---------------- CHARTS ---------------- */
  const renderCharts = () => {
    if (!summary) return null;

    return (
      <div className="charts-area">
        <div className="chart-card">
          <h3>Equipment Type Distribution</h3>
          <div className="chart-inner">
            <Pie
              data={{
                labels: Object.keys(summary.type_distribution || {}),
                datasets: [
                  {
                    data: Object.values(summary.type_distribution || {}),
                    backgroundColor: [
                      '#60a5fa',
                      '#34d399',
                      '#fbbf24',
                      '#f87171',
                      '#a78bfa',
                      '#93c5fd',
                    ],
                    borderWidth: 2,
                    radius: '85%',
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom',
                    labels: {
                      boxWidth: 14,
                      padding: 14,
                    },
                  },
                },
              }}
            />
          </div>
        </div>

        <div className="chart-card">
          <h3>System Averages</h3>
          <div className="chart-inner">
            <Bar
              data={{
                labels: ['Pressure', 'Temperature'],
                datasets: [
                  {
                    label: 'Average Values',
                    data: [
                      summary.average_pressure || 0,
                      summary.average_temperature || 0,
                    ],
                    backgroundColor: ['#38bdf8', '#6366f1'],
                    borderRadius: 8,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                },
              }}
            />
          </div>
        </div>
      </div>
    );
  };

  /* ---------------- UI ---------------- */
  return (
    <div className={`app-root ${darkMode ? 'dark' : 'light'}`}>
      <header className="topbar">
        <div className="brand">🧪 Chemical Equipment Visualizer</div>
        <button
          className="theme-btn"
          onClick={() => setDarkMode(!darkMode)}
        >
          {darkMode ? '☀️ Light' : '🌙 Dark'}
        </button>
      </header>

      <main className="container">
        {/* UPLOAD */}
        <section
          className={`upload-card ${dragActive ? 'drag-active' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <h2>Upload CSV</h2>
          <p className="muted">Drag & drop or click to upload</p>

          <label className="file-input">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={uploadFile}
            />
            <span>
              {loading ? <div className="spinner" /> : 'Choose CSV'}
            </span>
          </label>

          {summary && (
            <div className="summary">
              <div>Total Rows: {summary.total_rows}</div>
              <div>Avg Pressure: {summary.average_pressure}</div>
              <div>Avg Temperature: {summary.average_temperature}</div>

              {reportUrl && (
                <a href={reportUrl} target="_blank" rel="noreferrer">
                  Download PDF
                </a>
              )}
            </div>
          )}
        </section>

        {/* CHARTS */}
        {renderCharts()}

        {/* HISTORY */}
        <History
          items={history}
          onLoad={(item) => {
            setSummary(item.summary || null);
            setReportUrl(item.report_url || null);
          }}
        />
      </main>

      <footer className="footer">
        Upload CSV to visualize chemical equipment data
      </footer>
    </div>
  );
}

export default App;
