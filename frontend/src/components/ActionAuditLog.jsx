import React from 'react';
import { 
  ListFilter, 
  Square, 
  ShieldAlert, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Check, 
  X,
  FileCheck2,
  Train
} from 'lucide-react';

export default function ActionAuditLog({
  actions,
  currentStep,
  totalSteps,
  pendingConfirmation,
  onApproveConfirmation,
  onCancelConfirmation,
  onStopTask,
  isRunning,
  completionSummary,
  extractedData
}) {
  const progressPercent = totalSteps > 0 ? Math.round((currentStep / totalSteps) * 100) : 0;

  return (
    <section className="panel" aria-labelledby="audit-panel-title">
      <div className="panel-header">
        <div className="panel-title" id="audit-panel-title">
          <ListFilter size={16} />
          <span>Action Audit Log</span>
        </div>
        {isRunning && (
          <button 
            type="button" 
            className="btn-stop" 
            onClick={onStopTask}
            title="Emergency Stop / Cancel Active Task"
            aria-label="Stop active browser task"
          >
            <Square size={12} fill="#f43f5e" />
            <span>Stop Task</span>
          </button>
        )}
      </div>

      <div className="panel-content">
        {/* Progress & Task Control Bar */}
        <div className="task-control-bar">
          <div className="task-progress-info">
            <span className="progress-text">
              {totalSteps > 0 ? `Step ${currentStep} of ${totalSteps}` : 'Agent Ready'}
            </span>
            <div className="progress-bar-bg">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            {progressPercent}% Complete
          </span>
        </div>

        {/* Confirmation Guardrail Alert Card */}
        {pendingConfirmation && (
          <div className="confirmation-card" role="alert" aria-live="assertive">
            <div className="confirm-title">
              <ShieldAlert size={18} color="#f59e0b" />
              <span>CONFIRM-BEFORE-COMMIT REQUIRED</span>
            </div>
            <p className="confirm-desc">
              {pendingConfirmation.prompt_text || pendingConfirmation.explanation || "Sensitive ticket booking action requires explicit authorization."}
            </p>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.75rem', fontFamily: 'monospace' }}>
              Action: {pendingConfirmation.action_type?.toUpperCase()} ➔ {pendingConfirmation.selector}
            </div>
            <div className="confirm-actions">
              <button 
                type="button" 
                className="btn-confirm-approve"
                onClick={() => onApproveConfirmation(pendingConfirmation.confirmation_id)}
                aria-label="Approve sensitive action"
              >
                <Check size={14} style={{ display: 'inline', marginRight: '4px' }} />
                Approve & Book
              </button>
              <button 
                type="button" 
                className="btn-confirm-cancel"
                onClick={() => onCancelConfirmation(pendingConfirmation.confirmation_id)}
                aria-label="Cancel sensitive action"
              >
                <X size={14} style={{ display: 'inline', marginRight: '4px' }} />
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Completion Summary Card */}
        {completionSummary && (
          <div className="summary-card">
            <div className="summary-title">
              <FileCheck2 size={16} />
              <span>Task Completion Summary</span>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: 1.4, marginBottom: '0.5rem' }}>
              {completionSummary}
            </p>
            {extractedData?.pnr && (
              <div style={{ background: '#090d16', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid #1e293b', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Train size={14} color="#38bdf8" />
                <span style={{ color: '#38bdf8', fontWeight: 700 }}>{extractedData.pnr}</span>
                <span style={{ color: '#10b981', marginLeft: 'auto', fontWeight: 600 }}>CONFIRMED</span>
              </div>
            )}
          </div>
        )}

        {/* Action Audit Timeline */}
        <div style={{ marginTop: '0.85rem', marginBottom: '0.35rem', fontSize: '0.72rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>
          Real-Time Execution Events ({actions.length})
        </div>

        <div className="action-timeline" role="log" aria-label="Action Audit Log">
          {actions.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#475569', padding: '2.5rem 1rem' }}>
              <Clock size={24} style={{ margin: '0 auto 0.5rem' }} />
              <p style={{ fontSize: '0.82rem' }}>No actions logged yet.</p>
              <p style={{ fontSize: '0.75rem', color: '#334155' }}>Speak or submit a command to start.</p>
            </div>
          ) : (
            actions.map((act) => (
              <div 
                key={act.id} 
                className={`timeline-item ${act.status || 'info'}`}
              >
                <div className="timeline-header">
                  <span className="action-type-pill">{act.action_type || act.action || 'ACTION'}</span>
                  <span className="action-time">{act.timestamp}</span>
                </div>
                <div className="action-target">
                  {act.element || act.selector || 'Webpage Target'}
                </div>
                {act.explanation && (
                  <div className="action-explanation">
                    {act.explanation}
                  </div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.2rem', fontSize: '0.7rem' }}>
                  {act.status === 'success' ? (
                    <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                      <CheckCircle2 size={12} /> Succeeded {act.duration ? `(${act.duration})` : ''}
                    </span>
                  ) : act.status === 'executing' ? (
                    <span style={{ color: '#38bdf8' }}>⚡ Executing in Playwright...</span>
                  ) : act.status === 'warning' ? (
                    <span style={{ color: '#f59e0b' }}>⚠️ Guardrail Intercepted</span>
                  ) : act.status === 'failed' ? (
                    <span style={{ color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                      <AlertCircle size={12} /> Failed
                    </span>
                  ) : (
                    <span style={{ color: '#64748b' }}>Pending</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
