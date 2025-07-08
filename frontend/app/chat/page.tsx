"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Chat, Message, ChatResponse } from "@/types/api";
import FileUpload from "@/components/FileUpload";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Sidebar from "@/components/Sidebar";

function hasMsg(obj: any): obj is { msg: string } {
  return typeof obj === 'object' && obj !== null && 'msg' in obj && typeof obj.msg === 'string';
}

export default function ChatPage() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    let chat = selectedChat;
    let chatId = chat?.id;
    try {
      // If no chat exists, create one first
      if (!chat) {
        chat = await api.createChat(inputMessage.trim() ? inputMessage.trim().slice(0, 20) : "New Chat");
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
      if (selectedFile) {
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: "Parsing VCF file, please wait... ⏳",
            created_at: new Date().toISOString(),
          },
        ]);
      }
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
        ...prev.filter(m => m.content !== "Parsing VCF file, please wait... ⏳"),
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
        ...prev.filter(m => m.content !== "Parsing VCF file, please wait... ⏳"),
        {
          role: "assistant",
          content: errorMsg,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      <Sidebar
        chats={chats}
        selectedChatId={selectedChat?.id || null}
        onSelect={handleSelectChat}
        onNewChat={handleNewChat}
      />
      <main className="flex-1 flex flex-col h-full min-h-0">
        {/* Header */}
        <div className="h-16 flex items-center px-8 border-b border-gray-800 bg-gray-950">
          <span className="text-lg font-semibold">
            {selectedChat ? selectedChat.title : "Chat"}
          </span>
        </div>
        {/* Main Chat Area */}
        <div className="flex-1 h-0 overflow-y-auto overflow-x-hidden px-2 py-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
          {selectedChat ? (
            messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-xl">Start the conversation!</div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {/* Avatar */}
                  {msg.role === "assistant" && (
                    <div className="flex-shrink-0 mr-2">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg">
                        <span className="text-xl">🤖</span>
                      </div>
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] break-words px-4 py-2 rounded-lg shadow-lg relative transition-all duration-200
                      ${msg.role === "user"
                        ? "bg-gradient-to-br from-primary-600 to-primary-800 text-white rounded-br-none ml-auto shadow-primary-800/30"
                        : "bg-gradient-to-br from-gray-800 to-gray-900 text-gray-100 rounded-bl-none mr-auto shadow-gray-900/40"}
                    `}
                  >
                    <div className="text-xs opacity-60 mb-1 flex items-center gap-1">
                      {msg.role === "user" ? (
                        <>
                          <span className="inline-block w-6 h-6 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg mr-1">🧑</span>
                          You
                        </>
                      ) : (
                        <>Assistant</>
                      )}
                      &middot; {new Date(msg.created_at).toLocaleString()}
                    </div>
                    {/* Message Content with Markdown and type-based coloring */}
                    {typeof msg.content === "string" ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        className={
                          `prose prose-invert max-w-none text-base leading-relaxed` +
                          (msg.role === 'assistant' ? ' prose-blue bg-gray-900/80 border border-gray-800 rounded-xl p-4 shadow-md' : '')
                        }
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
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg">
                        <span className="text-xl">🧑</span>
                      </div>
                    </div>
                  )}
                </div>
              ))
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
          className="p-6 bg-gray-900 border-t border-gray-800 flex items-center gap-2"
          onSubmit={e => {
            e.preventDefault();
            handleSendMessage();
          }}
        >
          <FileUpload
            onFileSelect={setSelectedFile}
            onFileRemove={() => setSelectedFile(null)}
            selectedFile={selectedFile}
            className="mr-2"
          />
          <input
            type="text"
            className="flex-1 border-none rounded-md px-4 py-3 bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Ask anything..."
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="ml-2 px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 flex items-center gap-2 disabled:opacity-50"
            disabled={loading || (!inputMessage.trim() && !selectedFile)}
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      </main>
    </div>
  );
}

// --- API additions needed in lib/api.ts ---
// async createChat(title: string): Promise<Chat> { ... }
// async sendMessage(chatId: string, message: string): Promise<ChatResponse> { ... }
// async sendMessageWithFile(chatId: string, formData: FormData): Promise<ChatResponse> { ... }