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
        stage1: null,
        stage2: null,
        round3: null,
        round4: null,
        stage3: null,
        metadata: null,
        loading: { stage1: false, stage2: false, round3: false, round4: false, stage3: false },
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      await api.sendMessageStream(activeId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            updateLastMessage((m) => { m.loading.stage1 = true; });
            break;
          case 'stage1_complete':
            updateLastMessage((m) => { m.stage1 = event.data; m.loading.stage1 = false; });
            break;
          case 'stage2_start':
            updateLastMessage((m) => { m.loading.stage2 = true; });
            break;
          case 'stage2_complete':
            updateLastMessage((m) => { m.stage2 = event.data; m.metadata = event.metadata; m.loading.stage2 = false; });
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
          case 'stage3_start':
            updateLastMessage((m) => { m.loading.stage3 = true; });
            break;
          case 'stage3_complete':
            updateLastMessage((m) => { m.stage3 = event.data; m.loading.stage3 = false; });
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
              m.loading.stage1 = false;
              m.loading.stage2 = false;
              m.loading.round3 = false;
              m.loading.round4 = false;
              m.loading.stage3 = false;
            });
            setIsLoading(false);
            break;
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
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
