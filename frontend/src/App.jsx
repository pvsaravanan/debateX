import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      // Prevent fetching and overwriting optimistic UI updates for newly created conversations
      if (currentConversation && currentConversation.id === currentConversationId) {
        return;
      }
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = () => {
    // If we're already on an empty/new chat, do nothing
    if (currentConversationId === null || (currentConversation && currentConversation.messages.length === 0)) {
      return;
    }
    setCurrentConversationId(null);
    setCurrentConversation(null);
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations(conversations.filter(conv => conv.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleSendMessage = async (content) => {
    let activeId = currentConversationId;
    setIsLoading(true);
    
    try {
      if (!activeId) {
        const newConv = await api.createConversation();
        activeId = newConv.id;
        setCurrentConversationId(activeId);
        setConversations([{ id: newConv.id, created_at: newConv.created_at, message_count: 0 }, ...conversations]);
        setCurrentConversation({ id: activeId, messages: [] });
      }

      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), userMessage],
      }));

      const assistantMessage = {
        role: 'assistant',
        routing: null,
        stage1: null,
        stage2: null,
        round3: null,
        round4: null,
        stage3: null,
        disagreement_map: null,
        metacognition: null,
        metadata: null,
        // routing starts true so the thinking indicator appears the instant
        // the message is sent, before the first SSE event arrives
        loading: { routing: true, metacognition: false, round1: false, round2: false, round3: false, round4: false, round5: false },
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      await api.sendMessageStream(activeId, content, (eventType, event) => {
        switch (eventType) {
          case 'routing_start':
            updateLastMessage((m) => { m.loading.routing = true; });
            break;
          case 'routing_complete':
            updateLastMessage((m) => { m.routing = event.data; m.loading.routing = false; });
            break;
          case 'metacognition_start':
            updateLastMessage((m) => { m.loading.metacognition = true; });
            break;
          case 'metacognition_complete':
            updateLastMessage((m) => { m.metacognition = event.data; m.loading.metacognition = false; });
            break;
          case 'round1_start':
            updateLastMessage((m) => { m.loading.round1 = true; });
            break;
          case 'round1_complete':
            updateLastMessage((m) => { m.stage1 = event.data; m.loading.round1 = false; });
            break;
          case 'round2_start':
            updateLastMessage((m) => { m.loading.round2 = true; });
            break;
          case 'round2_complete':
            updateLastMessage((m) => {
              m.stage2 = event.data;
              m.metadata = { ...(m.metadata || {}), ...event.metadata };
              m.loading.round2 = false;
            });
            break;
          case 'round3_start':
            updateLastMessage((m) => { m.loading.round3 = true; });
            break;
          case 'round3_complete':
            updateLastMessage((m) => { m.round3 = event.data; m.loading.round3 = false; });
            break;
          case 'round4_start':
            updateLastMessage((m) => { m.loading.round4 = true; });
            break;
          case 'round4_complete':
            updateLastMessage((m) => { m.round4 = event.data; m.loading.round4 = false; });
            break;
          case 'round5_start':
            updateLastMessage((m) => { m.loading.round5 = true; });
            break;
          case 'round5_complete':
            updateLastMessage((m) => {
              m.stage3 = event.data;
              m.disagreement_map = event.disagreement_map || null;
              m.loading.round5 = false;
            });
            break;
          case 'title_complete':
            const newTitle = event.data.title;
            setConversations((prev) =>
              prev.map((c) => (c.id === activeId ? { ...c, title: newTitle } : c))
            );
            setCurrentConversation((prev) =>
              prev && prev.id === activeId ? { ...prev, title: newTitle } : prev
            );
            break;
          case 'complete':
            loadConversations();
            setIsLoading(false);
            break;
          case 'error':
            updateLastMessage((m) => {
              m.error = event.message || "An unexpected error occurred.";
              Object.keys(m.loading).forEach((k) => { m.loading[k] = false; });
            });
            setIsLoading(false);
            break;
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setCurrentConversation((prev) => {
        if (!prev?.messages?.length) return prev;
        const messages = [...prev.messages];
        const lastMsg = { ...messages[messages.length - 1] };
        if (lastMsg.role === 'assistant') {
          lastMsg.error = error?.message || 'Failed to reach the backend. Is it running on port 8001?';
          lastMsg.loading = Object.fromEntries(Object.keys(lastMsg.loading || {}).map((k) => [k, false]));
          messages[messages.length - 1] = lastMsg;
        }
        return { ...prev, messages };
      });
      setIsLoading(false);
    }
  };

  const updateLastMessage = (updateFn) => {
    setCurrentConversation((prev) => {
      const messages = [...prev.messages];
      const lastMsg = { ...messages[messages.length - 1] };
      lastMsg.loading = { ...lastMsg.loading };
      updateFn(lastMsg);
      messages[messages.length - 1] = lastMsg;
      return { ...prev, messages };
    });
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await api.updateConversation(id, { title: newTitle });
      setConversations(conversations.map(conv => 
        conv.id === id ? { ...conv, title: newTitle } : conv
      ));
      if (currentConversationId === id) {
        setCurrentConversation(prev => ({ ...prev, title: newTitle }));
      }
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  return (
    <div className={`app ${isSidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
      <Sidebar
        isExpanded={isSidebarExpanded}
        onToggle={() => setIsSidebarExpanded(!isSidebarExpanded)}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
      />
      <main>
        <ChatInterface
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}

export default App;
