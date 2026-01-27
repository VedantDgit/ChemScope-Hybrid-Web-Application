import React from 'react';

function History({ items = [], onLoad }) {
  return (
    <div className="history-card">
      <h3>Last 5 Uploads</h3>

      {(!items || items.length === 0) && (
        <p className="muted">No uploads yet</p>
      )}

      {Array.isArray(items) &&
        items.map((item) => (
          <div key={item.id} className="history-item">
            <strong>{item.filename}</strong>

            <div className="muted" style={{ fontSize: 12 }}>
              {new Date(item.uploaded_at).toLocaleString()}
            </div>

            <div style={{ marginTop: 6 }}>
              <button
                onClick={() => onLoad && onLoad(item)}
                style={{ padding: '4px 8px' }}
              >
                Load
              </button>

              {item.report_url && (
                <a
                  href={item.report_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ marginLeft: 8 }}
                >
                  PDF
                </a>
              )}
            </div>
          </div>
        ))}
    </div>
  );
}

export default History;
