import React from 'react';
import { Radio, Cpu, Volume2, ShieldCheck, Globe } from 'lucide-react';

export default function Navbar({ systemStatus, isWsConnected }) {
  const bedrockEngine = systemStatus?.engines?.bedrock?.engine === 'aws_bedrock'
    ? 'AWS Bedrock'
    : 'Bedrock Engine (Ready)';

  const voiceProvider = systemStatus?.engines?.elevenlabs?.provider || 'Web Speech Voice';

  return (
    <header className="top-navbar">
      <div className="brand-section">
        <div className="brand-logo">
          <span>V</span>
        </div>
        <div className="brand-text">
          <h1>VAANIWEB</h1>
          <p>Your Voice. Your Language. Your Web.</p>
        </div>
      </div>

      <div className="nav-badges">
        {/* Playwright MCP */}
        <div className="status-chip active" title="Official Playwright MCP Automation Server">
          <Globe size={13} />
          <span>Playwright MCP</span>
        </div>

        {/* AI Engine */}
        <div className="status-chip active" title="Multilingual Intent & Planning Model">
          <Cpu size={13} />
          <span>{bedrockEngine}</span>
        </div>

        {/* Voice Engine */}
        <div className="status-chip active" title="Multilingual Speech Recognition & Synthesis">
          <Volume2 size={13} />
          <span>{voiceProvider}</span>
        </div>

        {/* Safety Guardrail */}
        <div className="status-chip active" title="Mandatory Confirm-Before-Commit Enforcement">
          <ShieldCheck size={13} color="#10b981" />
          <span>Confirm-Before-Commit</span>
        </div>

        {/* WebSocket Connection */}
        <div className={`status-chip ${isWsConnected ? 'active' : ''}`}>
          <div className="status-dot"></div>
          <span>{isWsConnected ? 'Live' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
}
