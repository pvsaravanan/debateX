import { useState, useRef, useEffect } from 'react';
import './Sidebar.css';

const PanelLeftOpenIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="18" x="3" y="3" rx="2" /><path d="M9 3v18" />
  </svg>
);

const PanelLeftCloseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="18" x="3" y="3" rx="2" /><path d="M9 3v18" /><path d="m16 15-3-3 3-3" />
  </svg>
);

const NewChatIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><line x1="12" x2="12" y1="7" y2="13" /><line x1="9" x2="15" y1="10" y2="10" />
  </svg>
);

const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
  </svg>
);

const EditIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
  </svg>
);

const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 6h18m-2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
);

const ChatIcons = [
  () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><line x1="20" x2="8.12" y1="4" y2="15.88" /><line x1="14.47" x2="20" y1="14.48" y2="20" /><line x1="8.12" x2="12" y1="8.12" y2="12" /></svg>),
  () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /></svg>),
  () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" /><path d="M2 14h2" /><path d="M20 14h2" /><path d="M15 13v2" /><path d="M9 13v2" /></svg>),
  () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /><path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" /></svg>)
];

const getChatIcon = (id) => {
  const index = parseInt(id.slice(-1), 16) % ChatIcons.length || 0;
  const Icon = ChatIcons[index];
  return <Icon />;
};

export default function Sidebar({
  isExpanded,
  onToggle,
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
}) {
  const [editingId, setEditingId] = useState(null);
  const [tempTitle, setTempTitle] = useState('');
  const editInputRef = useRef(null);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const handleStartRename = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setTempTitle(conv.title || 'New Conversation');
  };

  const handleFinishRename = () => {
    if (editingId && tempTitle.trim()) {
      onRenameConversation(editingId, tempTitle.trim());
    }
    setEditingId(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleFinishRename();
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  return (
    <div className={`sidebar ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="sidebar-header-toggle">
        <button className="icon-only-btn toggle-panel-btn" onClick={onToggle} title={isExpanded ? "Hide Sidebar" : "Show Sidebar"}>
          {isExpanded ? <PanelLeftCloseIcon /> : <PanelLeftOpenIcon />}
        </button>
      </div>

      <div className="sidebar-main-actions">
        <button className="action-row" onClick={onNewConversation} title="New Chat">
          <div className="icon-box"><NewChatIcon /></div>
          <span className="nav-label">New Chat</span>
        </button>
        <button className="action-row" title="Search">
          <div className="icon-box"><SearchIcon /></div>
          <span className="nav-label">Search</span>
        </button>
      </div>

      <div className="sidebar-section">
        <h3 className="section-title">Older</h3>
        <div className="conversation-list-v2">
          {conversations.map((conv) => (
            <div 
              key={conv.id} 
              className={`chat-row-container ${conv.id === currentConversationId ? 'active' : ''}`}
            >
              <button 
                className="chat-row"
                onClick={() => onSelectConversation(conv.id)}
                title={!isExpanded ? (conv.title || 'New Conversation') : ""}
              >

                {editingId === conv.id ? (
                  <input
                    ref={editInputRef}
                    className="rename-input"
                    value={tempTitle}
                    onChange={(e) => setTempTitle(e.target.value)}
                    onBlur={handleFinishRename}
                    onKeyDown={handleKeyDown}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="chat-label">{conv.title || 'New Conversation'}</span>
                )}
              </button>
              
              {isExpanded && editingId !== conv.id && (
                <div className="chat-actions">
                  <button onClick={(e) => handleStartRename(e, conv)} title="Rename"><EditIcon /></button>
                  <button onClick={(e) => { e.stopPropagation(); onDeleteConversation(conv.id); }} title="Delete"><TrashIcon /></button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
