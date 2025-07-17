"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Chat, Message, ChatResponse } from "@/types/api";
import FileUpload from "@/components/FileUpload";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Sidebar from "@/components/Sidebar";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from '../theme-context';
import { Menu } from 'lucide-react';
import { ChevronRight } from 'lucide-react';

function hasMsg(obj: any): obj is { msg: string } {
  return typeof obj === 'object' && obj !== null && 'msg' in obj && typeof obj.msg === 'string';
}

// Add TypingIndicator component inline
function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 mt-2">
      <div className="w-3 h-3 bg-medical-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
      <div className="w-3 h-3 bg-medical-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
      <div className="w-3 h-3 bg-medical-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
      <span className="ml-2 text-bluegray-400 text-base font-medium">Assistant is typing...</span>
    </div>
  );
}

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  // Add state for editing message
  const [editingMsgIdx, setEditingMsgIdx] = useState<number | null>(null);
  const [editingMsgValue, setEditingMsgValue] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [deleteLoadingIdx, setDeleteLoadingIdx] = useState<number | null>(null);
  // Add user profile dropdown state
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  // Close menu on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target as Node)) {
        setProfileMenuOpen(false);
      }
    }
    if (profileMenuOpen) {
      document.addEventListener('mousedown', handleClick);
    } else {
      document.removeEventListener('mousedown', handleClick);
    }
    return () => document.removeEventListener('mousedown', handleClick);
  }, [profileMenuOpen]);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    api.getChats().then(setChats);
  }, []);

  const [messagesLoading, setMessagesLoading] = useState(false);
  const [justCreatedChat, setJustCreatedChat] = useState(false);

  useEffect(() => {
    if (!selectedChat) return;
    setMessagesLoading(!justCreatedChat);
    api.getChat(selectedChat.id).then(chat => {
      setMessages(chat.messages || []);
      setMessagesLoading(false);
    });
  }, [selectedChat]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectChat = (chat: Chat) => {
    setSelectedChat(chat);
    setInputMessage("");
    setSelectedFile(null);
    setJustCreatedChat(false);
  };

  const handleNewChat = () => {
    setSelectedChat(null);
    setMessages([]);
    setInputMessage("");
    setSelectedFile(null);
    setJustCreatedChat(true);
  };

  const handleNewDietPlannerChat = async () => {
    setLoading(true);
    try {
      const chat = await api.createDietPlannerChat();
      setChats(prev => [chat, ...prev]);
      setSelectedChat(chat);
      setMessages([]);
      setInputMessage("");
      setSelectedFile(null);
    } catch (error) {
      console.error('Error creating diet planner chat:', error);
    } finally {
      setLoading(false);
    }
  };

  const [fileProcessing, setFileProcessing] = useState(false);
  const [lastFileUploadTime, setLastFileUploadTime] = useState<number | null>(null);

  const handleSendMessage = async () => {
    if ((!selectedChat && !inputMessage.trim() && !selectedFile) || (selectedChat && !inputMessage.trim() && !selectedFile)) return;
    setLoading(true);
    let chat = selectedChat;
    let chatId = chat?.id;
    try {
      // If no chat exists, create one first
      if (!chat) {
        chat = await api.createChat("New Chat");
        setChats(prev => [chat as Chat, ...prev]);
        setSelectedChat(chat as Chat);
        chatId = chat.id;
      }
      const userMsg: Message = {
        role: "user",
        content: inputMessage || `Uploaded file: ${selectedFile?.name}`,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMsg]);
      setInputMessage("");
      // Handle file upload (non-streaming for now)
      if (selectedFile) {
        setFileProcessing(true);
        setLastFileUploadTime(Date.now());
        const formData = new FormData();
        formData.append("file", selectedFile);
        // Show animated assistant message while waiting
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: "<file-processing>",
            created_at: new Date().toISOString(),
          },
        ]);
        const response = await api.sendMessageWithFile(String(chatId), formData);
        setSelectedFile(null);
        // Poll for assistant response if not immediately present
        let foundAssistant = false;
        let pollCount = 0;
        while (!foundAssistant && pollCount < 30) { // up to ~30s
          const updatedChat = await api.getChat(String(chatId));
          setMessages(updatedChat.messages || []);
          foundAssistant = (updatedChat.messages || []).some(
            m => m.role === "assistant" && m.created_at && (!lastFileUploadTime || new Date(m.created_at).getTime() > lastFileUploadTime)
          );
          if (!foundAssistant) {
            await new Promise(res => setTimeout(res, 1000));
            pollCount++;
          }
        }
        setFileProcessing(false);
      } else {
        // Static (non-streaming) text message
        const response = await api.sendMessage(String(chatId), inputMessage);
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content:
              typeof response.response === "string" && response.response.trim()
                ? response.response
                : (hasMsg(response.response) ? response.response.msg : JSON.stringify(response.response)),
            created_at: new Date().toISOString(),
          },
        ]);
      }
      api.getChats().then(setChats);
    } catch (error: any) {
      let errorMsg =
        error.code === "ECONNABORTED"
          ? "Request timed out. The analysis took too long. Please try again with a smaller file or simpler query."
          : (hasMsg(error) ? error.msg : (error.response?.data?.detail || error.message || JSON.stringify(error)));
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: errorMsg,
          created_at: new Date().toISOString(),
        },
      ]);
      setLoading(false);
    }
    setLoading(false);
  };

  const [sidebarWidth, setSidebarWidth] = useState(288); // default width in px
  const [isResizing, setIsResizing] = useState(false);
  const sidebarMinWidth = 180;
  const sidebarMaxWidth = 480;
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [sidebarMinimized, setSidebarMinimized] = useState(false);

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      if (!isResizing) return;
      const newWidth = Math.min(Math.max(e.clientX, sidebarMinWidth), sidebarMaxWidth);
      setSidebarWidth(newWidth);
    }
    function handleMouseUp() {
      setIsResizing(false);
    }
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  return (
    <div className="flex h-screen bg-medical-50 dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100">
      <AnimatePresence>
        {!sidebarMinimized && sidebarOpen && (
          <motion.div
            ref={sidebarRef}
            style={{ width: sidebarWidth, minWidth: sidebarMinWidth, maxWidth: sidebarMaxWidth, transition: isResizing ? 'none' : 'width 0.2s' }}
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="z-20 h-full relative group"
          >
            <Sidebar
              chats={chats}
              selectedChatId={selectedChat?.id || null}
              onSelect={handleSelectChat}
              onNewChat={handleNewChat}
              onNewDietPlannerChat={handleNewDietPlannerChat}
              onDelete={(chatId: string) => {
                setChats(prev => prev.filter(c => c.id !== chatId));
                if (selectedChat?.id === chatId) {
                  setSelectedChat(null);
                  setMessages([]);
                }
              }}
              onClose={() => setSidebarOpen(false)}
              minimized={false}
              onToggleMinimize={() => setSidebarMinimized(true)}
              width={sidebarWidth}
            />
            {/* Drag handle, appears on hover */}
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-ew-resize z-30 bg-transparent group-hover:bg-blue-200/30 transition"
              style={{ userSelect: 'none' }}
              onMouseDown={() => setIsResizing(true)}
            />
          </motion.div>
        )}
        {sidebarMinimized && (
          <Sidebar
            chats={chats}
            selectedChatId={selectedChat?.id || null}
            onSelect={handleSelectChat}
            onNewChat={handleNewChat}
            onNewDietPlannerChat={handleNewDietPlannerChat}
            onDelete={(chatId: string) => {
              setChats(prev => prev.filter(c => c.id !== chatId));
              if (selectedChat?.id === chatId) {
                setSelectedChat(null);
                setMessages([]);
              }
            }}
            onClose={() => setSidebarOpen(false)}
            minimized={true}
            onToggleExpand={() => setSidebarMinimized(false)}
          />
        )}
      </AnimatePresence>
      <main className={`flex-1 flex flex-col h-full min-h-0 ${!sidebarOpen ? 'px-4 md:px-8' : ''}`}>
        {/* Minimal Transparent Header with Theme Toggle */}
        <div className="h-12 flex items-center justify-end px-6 pt-4 bg-transparent shadow-none border-none relative">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full border border-medical-300 bg-medical-50 dark:bg-bluegray-800 dark:border-medical-500 hover:bg-medical-100 dark:hover:bg-bluegray-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-medical-400 shadow"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-medical-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 5.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-medical-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z" /></svg>
            )}
          </button>
          {/* User Profile Icon and Dropdown */}
          <div className="relative ml-4" ref={profileMenuRef}>
            <button
              className="w-10 h-10 rounded-full bg-gradient-to-br from-medical-400 to-medical-600 flex items-center justify-center shadow border-2 border-medical-200 dark:border-medical-500 focus:outline-none focus:ring-2 focus:ring-medical-400"
              onClick={() => setProfileMenuOpen(v => !v)}
              aria-label="User menu"
            >
              {/* Simple SVG avatar */}
              <svg className="w-7 h-7 text-white" fill="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" fill="#26b6cf" />
                <ellipse cx="12" cy="10" rx="4" ry="4" fill="#fff" />
                <ellipse cx="12" cy="17" rx="6" ry="3" fill="#fff" />
              </svg>
            </button>
            {profileMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-bluegray-900 border border-medical-200 dark:border-bluegray-700 rounded-lg shadow-lg z-50 py-2 animate-fade-in">
                <button className="w-full text-left px-4 py-2 hover:bg-medical-100 dark:hover:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100" onClick={() => { setProfileMenuOpen(false); alert('Profile page coming soon!'); }}>Profile</button>
                <button className="w-full text-left px-4 py-2 hover:bg-medical-100 dark:hover:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100" onClick={() => { setProfileMenuOpen(false); alert('Settings page coming soon!'); }}>Settings</button>
                <button className="w-full text-left px-4 py-2 hover:bg-alert-100 dark:hover:bg-alert-700 text-alert-600 dark:text-alert-300 border-t border-medical-100 dark:border-bluegray-700" onClick={() => { setProfileMenuOpen(false); api.logout(); }}>Logout</button>
              </div>
            )}
          </div>
        </div>
        {/* Main Chat Area */}
        <div className="flex-1 h-0 overflow-y-auto overflow-x-hidden px-2 py-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
          {selectedChat ? (
            messagesLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-400 text-xl animate-pulse">
                <div className="w-3/4 h-6 bg-gray-200 rounded mb-4" />
                <div className="w-2/3 h-6 bg-gray-200 rounded mb-4" />
                <div className="w-1/2 h-6 bg-gray-200 rounded" />
                <span className="mt-8">Loading messages...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-xl">Start the conversation!</div>
            ) : (
              <AnimatePresence>
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {/* Avatar */}
                    {msg.role === "assistant" && (
                      <div className="flex-shrink-0 mr-2">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-medical-400 to-medical-600 flex items-center justify-center shadow-lg border-2 border-medical-200 dark:border-medical-500">
                          {/* DNA Icon for assistant */}
                          <span className="text-xl">
                            <svg viewBox="0 0 24 24" fill="none" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                              <ellipse cx="12" cy="12" rx="10" ry="10" fill="#26b6cf" fillOpacity="0.18" />
                              <path d="M8 18c4-4 4-7 0-12M16 6c-4 4-4 7 0 12" stroke="#009eb2" strokeWidth="1.5" strokeLinecap="round"/>
                              <path d="M9.5 15c1.5-1.5 4.5-1.5 6 0" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round"/>
                              <path d="M14.5 9c-1.5 1.5-4.5 1.5-6 0" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round"/>
                            </svg>
                          </span>
                        </div>
                      </div>
                    )}
                    <div
                      className={`inline-block break-words px-6 py-4 rounded-xl shadow-lg relative transition-all duration-200
                        ${msg.role === "user"
                          ? "bg-genetic-50 dark:bg-genetic-400/10 text-bluegray-900 dark:text-bluegray-100 rounded-br-none ml-auto shadow-genetic-400/20 border border-genetic-100 dark:border-genetic-400 text-lg font-semibold max-w-xl"
                          : "bg-medical-50 dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100 font-medium rounded-bl-none mr-auto shadow-medical-400/10 border border-medical-100 dark:border-medical-700 text-lg leading-relaxed max-w-xl"}
                      `}
                      style={{ maxWidth: '80%', wordBreak: 'break-word' }}
                    >
                      {msg.content === "<file-processing>" ? (
                        <div className="flex items-center gap-3 animate-pulse">
                          <span className="inline-block w-6 h-6 border-4 border-blue-300 border-t-transparent rounded-full animate-spin"></span>
                          <span className="text-bluegray-700 dark:text-bluegray-100 font-semibold">Assistant is analyzing your file and preparing insights. This may take a moment...</span>
                        </div>
                      ) : (
                        <>
                          <div className="text-xs text-bluegray-400 font-medium mb-2 flex items-center gap-1">
                            {msg.role === "user" ? (
                              <>
                                <span className="inline-block w-6 h-6 rounded-full bg-gradient-to-br from-genetic-400 to-genetic-600 flex items-center justify-center shadow-lg mr-1">🧑</span>
                                You
                              </>
                            ) : (
                              <>Assistant</>
                            )}
                            &middot; {mounted ? new Date(msg.created_at).toLocaleString() : ''}
                          </div>
                          {/* Message Content with Markdown and type-based coloring */}
                          {typeof msg.content === "string" ? (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              className={
                                `markdown prose prose-lg max-w-none text-bluegray-700/90 dark:text-bluegray-100 leading-relaxed
                                ${msg.role === 'assistant' ? 'prose-medical dark:prose-invert bg-medical-50 dark:bg-bluegray-900 border border-medical-200 dark:border-medical-700 rounded-xl p-4 shadow-md' : ''}`
                              }
                              components={{
                                h1: ({node, ...props}) => (
                                  <h1 {...props} className="font-bold text-bluegray-900 dark:text-white text-2xl mb-4" />
                                ),
                                h2: ({node, ...props}) => (
                                  <h2 {...props} className="font-bold text-bluegray-900 dark:text-white text-xl mb-3" />
                                ),
                                h3: ({node, ...props}) => (
                                  <h3 {...props} className="font-semibold text-bluegray-900 dark:text-bluegray-100 text-lg mb-2" />
                                ),
                                p: ({node, ...props}) => (
                                  <p {...props} className="mb-3 text-bluegray-700 dark:text-bluegray-100" />
                                ),
                                li: ({node, ...props}) => (
                                  <li {...props} className="text-bluegray-700 dark:text-bluegray-100" />
                                ),
                                blockquote: ({node, ...props}) => (
                                  <blockquote {...props} className="border-l-4 border-medical-500 pl-4 italic text-bluegray-500 dark:text-bluegray-200 mb-3" />
                                ),
                                strong: ({node, ...props}) => (
                                  <strong {...props} className="font-bold text-bluegray-900 dark:text-white" />
                                ),
                                table: ({node, ...props}) => (
                                  <table {...props} className="w-full border-collapse border border-medical-300 dark:border-medical-700 my-4" />
                                ),
                                th: ({node, ...props}) => (
                                  <th {...props} className="bg-medical-100 dark:bg-bluegray-800 text-medical-700 dark:text-medical-200 border border-medical-300 dark:border-medical-700 px-3 py-2 font-semibold" />
                                ),
                                td: ({node, ...props}) => (
                                  <td {...props} className="border border-medical-200 dark:border-medical-700 px-3 py-2" />
                                ),
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          ) : (msg.content && hasMsg(msg.content as any)) ? (
                            <span>{(msg.content as any).msg}</span>
                          ) : (
                            <span>{JSON.stringify(msg.content)}</span>
                          )}
                        </>
                      )}
                    </div>
                    {/* User avatar on right */}
                    {msg.role === "user" && (
                      <div className="flex-shrink-0 ml-2">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-genetic-400 to-genetic-600 flex items-center justify-center shadow-lg border-2 border-genetic-200">
                          <span className="text-xl">🧑</span>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
                {loading && !fileProcessing && selectedChat && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="flex justify-start"
                  >
                      <TypingIndicator />
                  </motion.div>
                )}
                {fileProcessing && (
                  <div className="flex items-center gap-3 animate-pulse my-4">
                    <span className="inline-block w-6 h-6 border-4 border-blue-300 border-t-transparent rounded-full animate-spin"></span>
                    <span className="text-bluegray-700 dark:text-bluegray-100 font-semibold">Assistant is analyzing your file and preparing insights. This may take a moment...</span>
                  </div>
                )}
                {/* Typing indicator removed */}
              </AnimatePresence>
            )
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-2xl font-semibold">
              What's on the agenda today?
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        {/* Input Area */}
        <form
          className="p-6 border-t border-medical-100 dark:border-bluegray-800 flex justify-center bg-transparent"
          onSubmit={e => {
            e.preventDefault();
            handleSendMessage();
          }}
        >
          <div className="flex items-center gap-2 w-full max-w-xl mx-auto bg-white/95 dark:bg-bluegray-800 rounded-2xl shadow px-4 py-2">
            <FileUpload
              onFileSelect={setSelectedFile}
              onFileRemove={() => setSelectedFile(null)}
              selectedFile={selectedFile}
              className="mr-2"
            />
            <input
              type="text"
              className="flex-1 bg-transparent border-none outline-none text-lg font-normal text-bluegray-900 dark:text-bluegray-100 placeholder-bluegray-400 placeholder:font-normal"
              placeholder="Ask anything..."
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="flex-shrink-0 w-10 h-10 rounded-full bg-medical-500 hover:bg-medical-600 text-white flex items-center justify-center shadow focus:outline-none focus:ring-2 focus:ring-medical-400 disabled:opacity-50 transition-transform duration-150 active:scale-95 text-lg"
              disabled={loading || (!inputMessage.trim() && !selectedFile)}
            >
              {loading ? (
                <span className="text-base font-medium">...</span>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-5 w-5">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

// --- API additions needed in lib/api.ts ---
// async createChat(title: string): Promise<Chat> { ... }
// async sendMessage(chatId: string, message: string): Promise<ChatResponse> { ... }
// async sendMessageWithFile(chatId: string, formData: FormData): Promise<ChatResponse> { ... }