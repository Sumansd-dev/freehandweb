import React from 'react';
import { Monitor, RefreshCw, Lock, ExternalLink, Activity } from 'lucide-react';

export default function LiveBrowserPanel({
  browserState,
  browserStatus,
  currentTask,
  onRefresh
}) {
  const url = browserState?.url || 'http://127.0.0.1:8000/portal/';
  const title = browserState?.title || 'Autonomous Browser Ready';
  const screenshot = browserState?.screenshot;

  return (
    <section className="panel" aria-labelledby="browser-panel-title">
      <div className="panel-header">
        <div className="panel-title" id="browser-panel-title">
          <Monitor size={16} />
          <span>Live Browser Panel</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="panel-controls">
          <span className="status-chip active" style={{ fontSize: '0.7rem' }}>
            <Activity size={12} />
            <span>{browserStatus}</span>
          </span>
          <button 
            type="button"
            className="btn-stop"
            style={{ background: 'rgba(56, 189, 248, 0.1)', borderColor: '#38bdf8', color: '#38bdf8' }}
            onClick={onRefresh}
            title="Refresh Live View"
          >
            <RefreshCw size={12} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="panel-content">
        {/* Address & Navigation Bar */}
        <div className="browser-url-bar">
          <Lock size={13} color="#10b981" />
          <input 
            type="text" 
            readOnly 
            value={url} 
            title="Current Browser URL"
            aria-label="Current Website URL" 
          />
          <a 
            href={url.startsWith('file://') ? '/portal/' : url} 
            target="_blank" 
            rel="noreferrer"
            title="Open in new window"
            style={{ color: '#94a3b8' }}
          >
            <ExternalLink size={13} />
          </a>
        </div>

        {/* Browser Page Viewport */}
        <div className="browser-viewport-container">
          <div className="browser-live-tag">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }}></span>
            <span>REAL PLAYWRIGHT VIEWPORT</span>
          </div>

          {screenshot ? (
            <img 
              src={screenshot} 
              alt="Live Playwright Browser Viewport" 
              className="browser-img-preview"
            />
          ) : (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
              <RefreshCw size={24} style={{ animation: 'spin-slow 2s linear infinite', margin: '0 auto 0.75rem' }} />
              <p style={{ fontSize: '0.85rem' }}>Synchronizing Playwright viewport...</p>
            </div>
          )}
        </div>

        {/* Task & Status Bar */}
        <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', color: '#94a3b8' }}>
          <div>
            <strong style={{ color: '#f1f5f9' }}>Page: </strong>
            <span>{title}</span>
          </div>
          {currentTask && (
            <div style={{ color: '#38bdf8', fontWeight: 500 }}>
              <span>{currentTask}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
