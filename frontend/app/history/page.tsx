'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import type { Chat, Message } from '@/types/api';
import ReactMarkdown from 'react-markdown';

export default function HistoryPage() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    api.getChats()
      .then(setChats)
      .catch(() => setChats([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectChat = async (chat: Chat) => {
    setSelectedChat(chat);
    setLoadingMessages(true);
    try {
      const fullChat = await api.getChat(chat.id);
      setMessages(fullChat.messages || []);
    } catch {
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Chat History</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Chat List */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Your Chats</h2>
          {loading ? (
            <div>Loading...</div>
          ) : chats.length === 0 ? (
            <p>No chat history found.</p>
          ) : (
            <ul className="space-y-4">
              {chats.map((chat) => (
                <li
                  key={chat.id}
                  className={`p-4 bg-white rounded shadow flex items-center justify-between border ${selectedChat?.id === chat.id ? 'border-primary-500' : 'border-transparent'}`}
                  onClick={() => handleSelectChat(chat)}
                >
                  <div>
                    <div className="font-semibold">{chat.title}</div>
                    <div className="text-xs text-gray-500">{mounted ? new Date(chat.created_at).toLocaleString() : ''}</div>
                  </div>
                  <button
                    className="ml-4 text-red-500 hover:text-red-700 border border-red-500 px-2 py-1 rounded"
                    title="Delete chat"
                    onClick={e => {
                      e.stopPropagation();
                      if (confirm('Delete this chat?')) {
                        api.deleteChat(chat.id)
                          .then(() => setChats(chats => chats.filter(c => c.id !== chat.id)))
                          .catch(() => alert('Failed to delete chat'));
                      }
                    }}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {/* Message List */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Messages</h2>
          {selectedChat ? (
            loadingMessages ? (
              <div>Loading messages...</div>
            ) : messages.length === 0 ? (
              <p>No messages found for this chat.</p>
            ) : (
              <ul className="space-y-4">
                {messages.map((msg, idx) => (
                  <li key={idx} className={`p-3 rounded ${msg.role === 'user' ? 'bg-blue-50 text-blue-900' : 'bg-gray-100 text-gray-900'}`}>
                    <div className="text-xs mb-1 opacity-70">{msg.role === 'user' ? 'You' : 'Assistant'} &middot; {new Date(msg.created_at).toLocaleString()}</div>
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <div>{msg.content}</div>
                    )}
                  </li>
                ))}
              </ul>
            )
          ) : (
            <p>Select a chat to view its messages.</p>
          )}
        </div>
      </div>
    </div>
  );
} 