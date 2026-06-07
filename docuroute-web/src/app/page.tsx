'use client';

import React, { useState, useEffect, useRef } from 'react';

// Strict Type Definition
type Message = {
  role: 'user' | 'ai';
  content: string;
};

export default function Home() {
  const [appMode, setAppMode] = useState<'landing' | 'chat'>('landing');
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'ai', 
      content: 'System initialized. I am the DocuRoute AI, pre-loaded with current machine specifications and calculation rules. How can I assist you with your processing line today?' 
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 100);
  };

  useEffect(() => {
    if (appMode === 'chat') {
      scrollToBottom();
    }
  }, [messages, appMode, isLoading]); 

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return; 

    const userMessage = inputValue;
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputValue(''); 
    
    setIsLoading(true);

    try {
      // NOTE: You MUST change this URL once you deploy the new Render backend for this ghost instance.
      const response = await fetch('https://docuroute-ai.onrender.com/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });

      if (!response.ok) throw new Error('Network response was not ok');
      
      const data = await response.json();
      
      // THE ARMOR PLATE: Reject null or malformed data before it breaks React
      if (!data || typeof data !== 'object' || !data.role) {
        throw new Error('Backend returned an invalid or empty data payload.');
      }

      setMessages((prev) => [...prev, data]);

    } catch (error) {
      console.error("Failed to fetch from backend:", error);
      setMessages((prev) => [
        ...prev, 
        { role: 'ai', content: 'ERROR: The system received an invalid response. Please try again or check the backend connection.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (appMode === 'chat') {
    return (
      <div className="flex flex-col h-screen bg-slate-900 text-white selection:bg-blue-500 font-sans overflow-hidden">
        
        <header className="flex-shrink-0 flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950 z-10">
          <div className="flex items-center gap-4">
            <div className="text-xl font-extrabold tracking-tighter">DocuRoute AI</div>
            <div className="h-4 w-px bg-slate-700"></div>
            <span className="text-sm text-slate-400 font-medium">DocuRoute AI Engineer</span>
          </div>
          <button onClick={() => setAppMode('landing')} className="text-sm font-medium hover:text-blue-400 transition-colors">
            Exit Configuration
          </button>
        </header>

        <main className="flex-1 overflow-y-auto flex justify-center p-4">
          <div className="w-full max-w-3xl flex flex-col gap-8 py-4">
            
            {messages.map((msg: Message, index: number) => (
              <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                
                {msg.role === 'ai' && (
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 font-bold text-xs mt-1">
                    AI
                  </div>
                )}

                <div className={`flex flex-col gap-2 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  {msg.role === 'ai' && <span className="text-sm font-semibold text-slate-300">DocuRoute AI</span>}
                  <div className={`p-4 rounded-xl leading-relaxed text-sm ${
                    msg.role === 'user' 
                      ? 'bg-slate-700 text-white rounded-tr-none' 
                      : 'bg-slate-800 border border-slate-700 text-slate-200 rounded-tl-none'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-4 justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="w-8 h-8 rounded-full bg-blue-600/50 flex items-center justify-center flex-shrink-0 font-bold text-xs mt-1 animate-pulse text-white/50">
                  AI
                </div>
                <div className="flex flex-col gap-2 max-w-[85%] items-start">
                  <span className="text-sm font-semibold text-slate-500">DocuRoute AI is analyzing...</span>
                  <div className="p-4 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 rounded-tl-none flex items-center gap-1.5 h-[52px]">
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </main>

        <footer className="flex-shrink-0 bg-slate-950 border-t border-slate-800 p-4 pb-8 flex justify-center z-10">
          <div className="w-full max-w-3xl relative">
            <div className={`bg-slate-800 border border-slate-700 rounded-xl flex items-end p-2 shadow-2xl focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}>
              <textarea 
                rows={1}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                placeholder="Ask for engineering specifications, capacity limits, or power requirements..." 
                className="flex-grow bg-transparent px-3 py-2 resize-none outline-none text-white placeholder-slate-400 max-h-32"
              />
              <button 
                onClick={handleSendMessage}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700 p-2 px-4 rounded-lg font-semibold transition-colors mb-0.5 ml-2 disabled:bg-slate-700 disabled:text-slate-400"
              >
                Send
              </button>
            </div>
            <div className="text-center mt-3 text-xs text-slate-500">
              DocuRoute AI can make mistakes. Verify critical engineering specifications before purchasing.
            </div>
          </div>
        </footer>

      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white selection:bg-blue-500 font-sans relative">
      <nav className="flex justify-between items-center p-6 border-b border-slate-800">
        <div className="text-2xl font-extrabold tracking-tighter">DocuRoute AI</div>
        <button onClick={() => setAppMode('chat')} className="text-sm font-medium hover:text-blue-400 transition-colors">
          Access AI Consultant
        </button>
      </nav>

      <main className="flex flex-col items-center justify-center pt-32 px-4 text-center">
        <div className="inline-block px-4 py-1.5 mb-6 border border-slate-800 rounded-full text-xs font-bold tracking-widest text-slate-300 bg-slate-900">
          INDUSTRIAL FOOD PROCESSING INTELLIGENCE
        </div>
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl mb-8 leading-tight">
          Heavy Machinery. <br className="hidden md:block"/> 
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">
            Engineered with Precision.
          </span>
        </h1>
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mb-12">
          Calculate exact capacity requirements, retrieve engineering specs, and configure your global freezing line instantly using DocuRoute AI.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <button onClick={() => setAppMode('chat')} className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)]">
            Start AI Configuration
          </button>
        </div>
      </main>
    </div>
  );
}