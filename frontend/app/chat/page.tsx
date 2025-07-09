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
  const [isTyping, setIsTyping] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    api.getChats().then(setChats);
  }, []);

  useEffect(() => {
    if (!selectedChat) return;
    api.getChat(selectedChat.id).then(chat => setMessages(chat.messages || []));
  }, [selectedChat]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectChat = (chat: Chat) => {
    setSelectedChat(chat);
    setInputMessage("");
    setSelectedFile(null);
  };

  const handleNewChat = () => {
    setSelectedChat(null);
    setMessages([]);
    setInputMessage("");
    setSelectedFile(null);
  };

  const handleSendMessage = async () => {
    if ((!selectedChat && !inputMessage.trim() && !selectedFile) || (selectedChat && !inputMessage.trim() && !selectedFile)) return;
    setLoading(true);
    setIsTyping(true); // Start typing animation
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
      // Remove the static VCF parsing message and show only the animated typing indicator
      let response: ChatResponse;
      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        response = await api.sendMessageWithFile(String(chatId), formData);
        setSelectedFile(null);
      } else {
        response = await api.sendMessage(String(chatId), inputMessage);
      }
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
    } finally {
      setLoading(false);
      setIsTyping(false); // Stop typing animation
    }
  };

  return (
    <div className="flex h-screen bg-medical-50 dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100">
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="z-20"
          >
            <Sidebar
              chats={chats}
              selectedChatId={selectedChat?.id || null}
              onSelect={handleSelectChat}
              onNewChat={handleNewChat}
              onDelete={(chatId: string) => {
                setChats(prev => prev.filter(c => c.id !== chatId));
                if (selectedChat?.id === chatId) {
                  setSelectedChat(null);
                  setMessages([]);
                }
              }}
              onClose={() => setSidebarOpen(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>
      {!sidebarOpen && (
        <motion.button
          initial={{ x: -60, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -60, opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={() => setSidebarOpen(true)}
          className="absolute top-1/2 -translate-y-1/2 left-3 z-30 p-1.5 bg-white/80 dark:bg-bluegray-800/80 rounded-full shadow-md border border-medical-100 dark:border-bluegray-700 hover:bg-medical-100 dark:hover:bg-bluegray-700 transition focus:outline-none"
          aria-label="Show sidebar"
        >
          <ChevronRight className="h-5 w-5 text-medical-600" />
        </motion.button>
      )}
      <main className={`flex-1 flex flex-col h-full min-h-0 ${!sidebarOpen ? 'px-4 md:px-8' : ''}`}>
        {/* Minimal Transparent Header with Theme Toggle */}
        <div className="h-12 flex items-center justify-end px-6 pt-4 bg-transparent shadow-none border-none">
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
        </div>
        {/* Main Chat Area */}
        <div className="flex-1 h-0 overflow-y-auto overflow-x-hidden px-2 py-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
          {selectedChat ? (
            messages.length === 0 ? (
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
                      className={`max-w-2xl w-full break-words px-6 py-4 rounded-xl shadow-lg relative transition-all duration-200
                        ${msg.role === "user"
                          ? "bg-genetic-50 dark:bg-genetic-400/10 text-bluegray-900 dark:text-bluegray-100 rounded-br-none ml-auto shadow-genetic-400/20 border border-genetic-100 dark:border-genetic-400 text-lg font-semibold"
                          : "bg-medical-50 dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100 font-medium rounded-bl-none mr-auto shadow-medical-400/10 border border-medical-100 dark:border-medical-700 text-lg leading-relaxed"}
                      `}
                    >
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
              </AnimatePresence>
            )
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-2xl font-semibold">
              What's on the agenda today?
            </div>
          )}
          <div ref={messagesEndRef} />
          {isTyping && (
            <div className="flex items-center gap-3 mt-2 animate-fade-in">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg animate-pulse">
                <span className="text-2xl">🤖</span>
              </div>
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce delay-150" />
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-bounce delay-300" />
              </div>
              <span className="text-sm text-gray-400 ml-2">Assistant is thinking...</span>
            </div>
          )}
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