import React, { useState, useEffect, useRef, useCallback } from 'react';
import Navbar from '../components/Navbar';
import LiveBrowserPanel from '../components/LiveBrowserPanel';
import VoiceAssistantOrb from '../components/VoiceAssistantOrb';
import ActionAuditLog from '../components/ActionAuditLog';
import { 
  fetchSystemStatus, 
  sendCommand, 
  confirmAction, 
  stopTask, 
  WebSocketClient 
} from '../services/api';

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('kn');
  
  // Browser State
  const [browserState, setBrowserState] = useState({
    url: 'http://127.0.0.1:8000/portal/',
    title: 'BharatRail Express — Indian Railway Reservation System',
    screenshot: null
  });
  const [browserStatus, setBrowserStatus] = useState('READY');
  const [currentTask, setCurrentTask] = useState('');

  // Voice & Agent State
  const [agentStatus, setAgentStatus] = useState('idle'); // idle, listening, processing, speaking, executing
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [audioSrc, setAudioSrc] = useState(null);

  // Action Audit Log State
  const [actions, setActions] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [completionSummary, setCompletionSummary] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const wsClientRef = useRef(null);

  // Load system status
  useEffect(() => {
    fetchSystemStatus().then(status => {
      if (status) setSystemStatus(status);
    });
  }, []);

  // WebSocket Event Handler
  const handleWsEvent = useCallback((type, data) => {
    console.log('[Dashboard WS Event]:', type, data);

    switch (type) {
      case 'session_ready':
        if (data.screenshot) {
          setBrowserState(prev => ({
            ...prev,
            screenshot: data.screenshot,
            url: data.url || prev.url,
            title: data.title || prev.title
          }));
        }
        break;

      case 'task_started':
        setIsRunning(true);
        setAgentStatus('processing');
        setBrowserStatus('ANALYZING INTENT');
        setActions([]);
        setCurrentStep(0);
        setTotalSteps(0);
        setPendingConfirmation(null);
        setCompletionSummary(null);
        setExtractedData(null);
        setTranscript(data.command || '');
        break;

      case 'agent_thought':
        setCurrentTask(data.thought || '');
        break;

      case 'plan_ready':
        setTotalSteps(data.total_steps || 0);
        setAiResponse(data.explanation || '');
        if (data.audio) setAudioSrc(data.audio);
        setAgentStatus('executing');
        setBrowserStatus('EXECUTING');
        break;

      case 'action_started':
        setCurrentStep(data.step);
        setCurrentTask(data.explanation || `Executing ${data.action_type}...`);
        setBrowserStatus('INTERACTING');
        setActions(prev => [
          {
            id: `act_${data.step}_${Date.now()}`,
            step: data.step,
            action_type: data.action_type,
            selector: data.selector,
            element: data.element,
            explanation: data.explanation,
            status: 'executing',
            timestamp: data.timestamp
          },
          ...prev
        ]);
        break;

      case 'screenshot_update':
        setBrowserState(prev => ({
          ...prev,
          screenshot: data.screenshot,
          url: data.url || prev.url,
          title: data.title || prev.title
        }));
        if (data.current_task) setCurrentTask(data.current_task);
        break;

      case 'action_completed':
        setActions(prev => prev.map(a => 
          a.step === data.step 
            ? { ...a, status: data.success ? 'success' : 'failed', duration: data.duration } 
            : a
        ));
        break;

      case 'confirmation_required':
        setBrowserStatus('PAUSED FOR APPROVAL');
        setPendingConfirmation(data);
        setAgentStatus('speaking');
        if (data.audio) setAudioSrc(data.audio);
        if (data.screenshot) {
          setBrowserState(prev => ({ ...prev, screenshot: data.screenshot }));
        }
        break;

      case 'confirmation_approved':
        setPendingConfirmation(null);
        setBrowserStatus('INTERACTING');
        setAgentStatus('executing');
        break;

      case 'task_cancelled':
        setIsRunning(false);
        setAgentStatus('idle');
        setBrowserStatus('CANCELLED');
        setPendingConfirmation(null);
        break;

      case 'task_completed':
        setIsRunning(false);
        setAgentStatus('speaking');
        setBrowserStatus('COMPLETED');
        setCompletionSummary(data.summary);
        setExtractedData(data.extracted_data);
        if (data.audio) setAudioSrc(data.audio);
        break;

      case 'task_error':
        setIsRunning(false);
        setAgentStatus('idle');
        setBrowserStatus('ERROR');
        alert(`Task Error: ${data.error}`);
        break;

      default:
        break;
    }
  }, []);

  // Initialize WebSocket Client
  useEffect(() => {
    const ws = new WebSocketClient('default', handleWsEvent, setIsWsConnected);
    ws.connect();
    wsClientRef.current = ws;

    return () => {
      ws.disconnect();
    };
  }, [handleWsEvent]);

  // Actions
  const handleSendCommand = async (text, language) => {
    if (!text.trim()) return;
    setTranscript(text);
    setAudioSrc(null);
    setAiResponse('');
    setCompletionSummary(null);

    try {
      await sendCommand({
        text,
        language: language || selectedLanguage,
        targetUrl: browserState.url
      });
    } catch (e) {
      console.error('Failed to send command:', e);
      alert(`Error starting navigation: ${e.message}`);
    }
  };

  const handleApproveConfirmation = async (confirmationId) => {
    try {
      await confirmAction({ confirmationId, approved: true });
    } catch (e) {
      console.error('Failed to approve confirmation:', e);
    }
  };

  const handleCancelConfirmation = async (confirmationId) => {
    try {
      await confirmAction({ confirmationId, approved: false });
    } catch (e) {
      console.error('Failed to cancel confirmation:', e);
    }
  };

  const handleStopTask = async () => {
    try {
      await stopTask();
    } catch (e) {
      console.error('Failed to stop task:', e);
    }
  };

  const handleRefreshPreview = () => {
    if (wsClientRef.current) {
      wsClientRef.current.sendMessage('refresh_preview');
    }
  };

  return (
    <div className="app-container">
      <Navbar 
        systemStatus={systemStatus} 
        isWsConnected={isWsConnected} 
      />

      <main className="dashboard-grid">
        {/* Section A: Live Browser Panel */}
        <LiveBrowserPanel
          browserState={browserState}
          browserStatus={browserStatus}
          currentTask={currentTask}
          onRefresh={handleRefreshPreview}
        />

        {/* Section B: Vernacular Voice Assistant */}
        <VoiceAssistantOrb
          selectedLanguage={selectedLanguage}
          onLanguageChange={setSelectedLanguage}
          onSendCommand={handleSendCommand}
          transcript={transcript}
          aiResponse={aiResponse}
          audioSrc={audioSrc}
          agentStatus={agentStatus}
        />

        {/* Section C: Action Audit Log & Controls */}
        <ActionAuditLog
          actions={actions}
          currentStep={currentStep}
          totalSteps={totalSteps}
          pendingConfirmation={pendingConfirmation}
          onApproveConfirmation={handleApproveConfirmation}
          onCancelConfirmation={handleCancelConfirmation}
          onStopTask={handleStopTask}
          isRunning={isRunning}
          completionSummary={completionSummary}
          extractedData={extractedData}
        />
      </main>
    </div>
  );
}
