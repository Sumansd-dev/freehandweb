import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, Sparkles, Volume2, MessageSquare } from 'lucide-react';

const LANGUAGES = [
  { code: 'kn', name: 'ಕನ್ನಡ', label: 'Kannada', speechCode: 'kn-IN' },
  { code: 'hi', name: 'हिन्दी', label: 'Hindi', speechCode: 'hi-IN' },
  { code: 'ta', name: 'தமிழ்', label: 'Tamil', speechCode: 'ta-IN' },
  { code: 'en', name: 'English', label: 'English', speechCode: 'en-IN' }
];

const SUGGESTIONS = {
  kn: [
    "ಬೆಂಗಳೂರು ಇಂದ ಮೈಸೂರಿಗೆ ನಾಳೆ ರೈಲು ಹುಡುಕಿ",
    "ನಾಳೆ ಬೆಳಗ್ಗೆ ಬೆಂಗಳೂರಿನಿಂದ ಮೈಸೂರಿಗೆ ಸ್ಲೀಪರ್ ಟಿಕೆಟ್ ಬುಕ್ ಮಾಡಿ"
  ],
  hi: [
    "बेंगलुरु से मैसूर कल की ट्रेन खोजें",
    "कल सुबह बेंगलुरु से मैसूर के लिए स्लीपर टिकट बुक करें"
  ],
  ta: [
    "பெங்களூரிலிருந்து மைசூருக்கு நாளை ரயில் தேடுங்கள்",
    "நாளை காலை பெங்களூர் முதல் மைசூர் வரை ஸ்லீப்பர் டிக்கெட் புக் செய்யவும்"
  ],
  en: [
    "Find a sleeper train from Bengaluru to Mysuru tomorrow morning",
    "Search trains from Bangalore to Mysore for tomorrow"
  ]
};

export default function VoiceAssistantOrb({
  selectedLanguage,
  onLanguageChange,
  onSendCommand,
  transcript,
  aiResponse,
  audioSrc,
  agentStatus // 'idle' | 'listening' | 'processing' | 'speaking' | 'executing'
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [localTranscript, setLocalTranscript] = useState('');
  const [textInput, setTextInput] = useState('');
  const recognitionRef = useRef(null);
  const audioPlayerRef = useRef(new Audio());

  // Set up speech recognition if supported in browser
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      const currentLang = LANGUAGES.find(l => l.code === selectedLanguage);
      recognition.lang = currentLang?.speechCode || 'kn-IN';

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event) => {
        let currentText = '';
        for (let i = 0; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript;
        }
        setLocalTranscript(currentText);
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (localTranscript.trim()) {
          onSendCommand(localTranscript.trim(), selectedLanguage);
        }
      };

      recognitionRef.current = recognition;
    }
  }, [selectedLanguage, localTranscript, onSendCommand]);

  // Handle incoming audio playback from ElevenLabs or Web Speech fallback
  useEffect(() => {
    if (audioSrc) {
      audioPlayerRef.current.src = audioSrc;
      audioPlayerRef.current.play().catch(e => console.warn('Audio play prevented:', e));
    } else if (aiResponse && agentStatus === 'speaking') {
      // Fallback Web Speech synthesis
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(aiResponse);
        const currentLang = LANGUAGES.find(l => l.code === selectedLanguage);
        utterance.lang = currentLang?.speechCode || 'en-US';
        window.speechSynthesis.speak(utterance);
      }
    }
  }, [audioSrc, aiResponse, agentStatus, selectedLanguage]);

  const toggleRecording = () => {
    if (isRecording) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      setLocalTranscript('');
      if (recognitionRef.current) {
        try {
          const currentLang = LANGUAGES.find(l => l.code === selectedLanguage);
          recognitionRef.current.lang = currentLang?.speechCode || 'kn-IN';
          recognitionRef.current.start();
          setIsRecording(true);
        } catch (e) {
          console.error('Failed to start speech recognition:', e);
        }
      } else {
        alert('Voice capture requires a browser supporting Web Speech API (Chrome/Edge/Safari). You can also use the text input below.');
      }
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!textInput.trim()) return;
    onSendCommand(textInput.trim(), selectedLanguage);
    setTextInput('');
  };

  const handleChipClick = (suggestion) => {
    onSendCommand(suggestion, selectedLanguage);
  };

  const orbStateClass = isRecording ? 'listening' : agentStatus;

  return (
    <section className="panel" aria-labelledby="assistant-panel-title">
      <div className="panel-header">
        <div className="panel-title" id="assistant-panel-title">
          <Sparkles size={16} />
          <span>Vernacular Voice Assistant</span>
        </div>
        <span className="status-chip active" style={{ fontSize: '0.7rem' }}>
          {isRecording ? '🔴 Listening' : `State: ${agentStatus.toUpperCase()}`}
        </span>
      </div>

      <div className="panel-content">
        {/* Language Selector */}
        <div className="language-selector-group" role="tablist" aria-label="Select preferred language">
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              type="button"
              role="tab"
              aria-selected={selectedLanguage === lang.code}
              className={`lang-btn ${selectedLanguage === lang.code ? 'active' : ''}`}
              onClick={() => onLanguageChange(lang.code)}
            >
              <span>{lang.name}</span>
              <span className="lang-sub">{lang.label}</span>
            </button>
          ))}
        </div>

        {/* Animated Voice Orb */}
        <div className="orb-section">
          <div 
            className={`orb-wrapper ${orbStateClass}`}
            onClick={toggleRecording}
            title={isRecording ? 'Click to stop listening' : 'Click / Push-to-Talk to speak'}
            role="button"
            tabIndex={0}
            aria-label="Push-to-talk voice activation orb"
          >
            <div className="orb-ring orb-ring-2"></div>
            <div className="orb-ring orb-ring-1"></div>
            <div className="orb-core">
              {isRecording ? (
                <Mic size={36} color="#ffffff" style={{ animation: 'pulse-dot 1s infinite' }} />
              ) : agentStatus === 'speaking' ? (
                <Volume2 size={36} color="#ffffff" />
              ) : (
                <Mic size={36} color="#ffffff" />
              )}
            </div>
          </div>

          <div style={{ marginTop: '0.85rem', textAlign: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isRecording ? '#f43f5e' : '#38bdf8' }}>
              {isRecording 
                ? 'Listening to your voice... Speak now' 
                : agentStatus === 'processing'
                ? 'Processing vernacular intent with Bedrock...'
                : agentStatus === 'executing'
                ? 'Executing browser actions...'
                : agentStatus === 'speaking'
                ? 'Speaking response...'
                : 'Click Orb or Push-to-Talk to speak'}
            </span>
          </div>
        </div>

        {/* Transcript Box */}
        {(transcript || localTranscript) && (
          <div className="transcript-box">
            <div className="box-label">
              <MessageSquare size={12} />
              <span>Recognized Command</span>
            </div>
            <p className="transcript-text">
              "{transcript || localTranscript}"
            </p>
          </div>
        )}

        {/* AI Vernacular Response Box */}
        {aiResponse && (
          <div className="ai-response-box">
            <div className="box-label" style={{ color: '#38bdf8' }}>
              <Volume2 size={12} />
              <span>Agent Spoken Explanation</span>
            </div>
            <p className="ai-response-text">
              {aiResponse}
            </p>
          </div>
        )}

        {/* Quick Suggestion Chips */}
        <div className="quick-chips-wrapper">
          <div className="chip-title">Quick Vernacular Commands:</div>
          <div className="chips-list">
            {(SUGGESTIONS[selectedLanguage] || SUGGESTIONS.en).map((item, idx) => (
              <button
                key={idx}
                type="button"
                className="quick-chip"
                onClick={() => handleChipClick(item)}
              >
                <span>🗣️</span>
                <span>{item}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Text Input Fallback */}
        <form className="text-fallback-form" onSubmit={handleFormSubmit}>
          <input 
            type="text" 
            className="text-fallback-input"
            placeholder={`Type a command in ${LANGUAGES.find(l => l.code === selectedLanguage)?.name || 'any language'}...`}
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            aria-label="Text command fallback input"
          />
          <button type="submit" className="btn-send" aria-label="Send command">
            <Send size={15} />
          </button>
        </form>
      </div>
    </section>
  );
}
