import { Chat } from '@/types/api';
import { Plus, Power } from 'lucide-react';
import api from '@/lib/api';
import { motion, AnimatePresence } from "framer-motion";
import { TrashIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useState, useEffect } from 'react';
import { ChevronLeft } from 'lucide-react';
import Link from 'next/link';

interface SidebarProps {
  chats: Chat[];
  selectedChatId: string | null;
  onSelect: (chat: Chat) => void;
  onNewChat: () => void;
  onNewDietPlannerChat: () => void;
  onNewBloodReportAnalyzerChat: () => void;
  onDelete: (chatId: string) => void;
  onClose?: () => void;
  width?: number;
  minimized: boolean;
  onToggleMinimize?: () => void;
  onToggleExpand?: () => void;
}

export default function Sidebar({ chats, selectedChatId, onSelect, onNewChat, onNewDietPlannerChat, onNewBloodReportAnalyzerChat, onDelete, onClose, width }: SidebarProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [deletingChatId, setDeletingChatId] = useState<string | null>(null);
  const [deletedChats, setDeletedChats] = useState<string[]>([]);
  // Chat search state
  const [search, setSearch] = useState("");
  const filteredChats = search.trim()
    ? chats.filter(chat => chat.title.toLowerCase().includes(search.trim().toLowerCase()))
    : chats;
  // Optimistically filter out deleted chats
  const visibleChats = filteredChats.filter(chat => !deletedChats.includes(chat.id));

  return (
    <aside className="bg-white dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100 flex flex-col h-full border-r border-medical-100 dark:border-bluegray-800 shadow-md relative"
      style={width ? { width } : {}}>
      {/* App Title */}
      <div className="flex items-center gap-3 justify-between px-6 py-6 border-b border-medical-100 dark:border-bluegray-800 relative">
        <span className="flex items-center gap-3 font-bold text-2xl tracking-wide">
          {/* DNA SVG Icon */}
          <span className="inline-block w-7 h-7">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="16" cy="16" rx="14" ry="14" fill="#26b6cf" fillOpacity="0.15" />
              <path d="M10 24c6-6 6-10 0-16M22 8c-6 6-6 10 0 16" stroke="#009eb2" strokeWidth="2" strokeLinecap="round"/>
              <path d="M12 20c2-2 6-2 8 0" stroke="#22c55e" strokeWidth="2" strokeLinecap="round"/>
              <path d="M20 12c-2 2-6 2-8 0" stroke="#22c55e" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </span>
          <span className="text-2xl font-extrabold tracking-wide text-medical-700/90 dark:text-medical-200 ml-1">Genetic AI Lab</span>
        </span>
      </div>
      {/* Vertically Centered Sidebar Toggle Button */}
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/2 p-1 bg-white/80 dark:bg-bluegray-800/80 rounded-full shadow-md border border-medical-100 dark:border-bluegray-700 hover:bg-medical-100 dark:hover:bg-bluegray-700 transition focus:outline-none z-20"
          aria-label="Hide sidebar"
          style={{ transform: 'translateY(-50%) translateX(50%)' }}
        >
          <ChevronLeft className="h-4 w-4 text-medical-600" />
        </button>
      )}
      {/* New Chat Buttons */}
      <div className="px-6 mt-6 mb-2 space-y-2">
        <button
          className="flex items-center gap-2 bg-medical-50 dark:bg-bluegray-800 hover:bg-medical-100 dark:hover:bg-bluegray-700 text-medical-600 dark:text-medical-200 px-5 py-2.5 rounded-lg transition font-semibold active:scale-95 shadow text-base w-full"
          onClick={onNewChat}
        >
          <PlusIcon className="h-5 w-5" />
          New Genetic Chat
        </button>
        <button
          className="flex items-center gap-2 bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/40 text-green-600 dark:text-green-200 px-5 py-2.5 rounded-lg transition font-semibold active:scale-95 shadow text-base w-full"
          onClick={onNewDietPlannerChat}
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l2.5 5m6-5v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6m6 0V9a2 2 0 00-2-2H9a2 2 0 00-2 2v4.01" />
          </svg>
          Diet Planner
        </button>
        <Link href="/analyze/blood-report" className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 dark:text-red-200 px-5 py-2.5 rounded-lg transition font-semibold active:scale-95 shadow text-base w-full">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3C12 3 7 8.5 7 13a5 5 0 0010 0c0-4.5-5-10-5-10z" />
            <circle cx="12" cy="17" r="2" fill="currentColor" />
          </svg>
          Blood Report Analyzer
        </Link>
      </div>
      {/* Chat Search Bar */}
      <div className="px-6 mb-2">
        <input
          type="text"
          className="w-full px-3 py-2 rounded-lg border border-medical-200 dark:border-bluegray-700 bg-medical-50 dark:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100 placeholder-bluegray-400"
          placeholder="Search chats..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>
      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-2 mt-2">
        {visibleChats.length === 0 ? (
          <div className="text-bluegray-400 px-4 py-6">No chats found.</div>
        ) : (
          <ul className="space-y-1 leading-relaxed">
            <AnimatePresence>
              {visibleChats.map(chat => (
                <motion.li
                  key={chat.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2 }}
                  className={`px-4 py-2 rounded-lg cursor-pointer flex items-center justify-between transition-colors shadow-sm border border-transparent text-base font-medium ${selectedChatId === chat.id ? 'bg-medical-100 dark:bg-bluegray-700 text-medical-700 font-semibold dark:text-medical-100 border-medical-400 dark:border-medical-500' : 'hover:bg-medical-50 dark:hover:bg-bluegray-800 text-bluegray-700/90 dark:text-bluegray-100 hover:font-semibold'}`}
                  onClick={() => onSelect(chat)}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="truncate">{chat.title}</span>
                    {chat.chat_type === 'diet_planner' && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 flex-shrink-0">
                        🥗
                      </span>
                    )}
                    {chat.chat_type === 'genetic' && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 flex-shrink-0">
                        🧬
                      </span>
                    )}
                  </div>
                  <button
                    className="ml-2 text-alert-400 hover:text-alert-600 px-2 py-1 rounded transition-transform duration-150 active:scale-90"
                    title="Delete chat"
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (confirm('Delete this chat?')) {
                        setDeletingChatId(chat.id);
                        setDeletedChats(prev => [...prev, chat.id]);
                        try {
                          await api.deleteChat(chat.id);
                          onDelete(chat.id);
                        } catch {
                          alert('Failed to delete chat');
                          setDeletedChats(prev => prev.filter(id => id !== chat.id));
                        }
                        setDeletingChatId(null);
                      }
                    }}
                    disabled={deletingChatId === chat.id}
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
      {/* Logout Button */}
      <button
        className="flex items-center gap-2 bg-bluegray-50 dark:bg-bluegray-800 hover:bg-alert-100 dark:hover:bg-alert-700 text-alert-600 hover:text-alert-800 dark:text-alert-300 dark:hover:text-white px-5 py-3 mx-6 mb-6 rounded-lg transition font-medium mt-auto shadow"
        onClick={() => api.logout()}
      >
        <Power className="h-5 w-5" />
        Logout
      </button>
    </aside>
  );
} 