import { Chat } from '@/types/api';
import { Plus, Power } from 'lucide-react';
import api from '@/lib/api';
import { motion, AnimatePresence } from "framer-motion";
import { TrashIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useState, useEffect } from 'react';
import { ChevronLeft } from 'lucide-react';

interface SidebarProps {
  chats: Chat[];
  selectedChatId: string | null;
  onSelect: (chat: Chat) => void;
  onNewChat: () => void;
  onDelete: (chatId: string) => void;
  onClose?: () => void;
}

export default function Sidebar({ chats, selectedChatId, onSelect, onNewChat, onDelete, onClose }: SidebarProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <aside className="w-72 bg-white dark:bg-bluegray-900 text-bluegray-900 dark:text-bluegray-100 flex flex-col h-full border-r border-medical-100 dark:border-bluegray-800 shadow-md relative">
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
      {/* New Chat Button */}
      <button
        className="flex items-center gap-2 bg-medical-50 dark:bg-bluegray-800 hover:bg-medical-100 dark:hover:bg-bluegray-700 text-medical-600 dark:text-medical-200 px-5 py-2.5 mt-6 mb-2 mx-6 rounded-lg transition font-semibold active:scale-95 shadow text-base"
        onClick={onNewChat}
      >
        <PlusIcon className="h-5 w-5" />
        New chat
      </button>
      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-2 mt-2">
        {chats.length === 0 ? (
          <div className="text-bluegray-400 px-4 py-6">No chats yet.</div>
        ) : (
          <ul className="space-y-1 leading-relaxed">
            <AnimatePresence>
              {chats.map(chat => (
                <motion.li
                  key={chat.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2 }}
                  className={`px-4 py-2 rounded-lg cursor-pointer flex items-center justify-between transition-colors shadow-sm border border-transparent text-base font-medium ${selectedChatId === chat.id ? 'bg-medical-100 dark:bg-bluegray-700 text-medical-700 font-semibold dark:text-medical-100 border-medical-400 dark:border-medical-500' : 'hover:bg-medical-50 dark:hover:bg-bluegray-800 text-bluegray-700/90 dark:text-bluegray-100 hover:font-semibold'}`}
                  onClick={() => onSelect(chat)}
                >
                  <span className="truncate">{chat.title}</span>
                  <button
                    className="ml-2 text-alert-400 hover:text-alert-600 px-2 py-1 rounded transition-transform duration-150 active:scale-90"
                    title="Delete chat"
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (confirm('Delete this chat?')) {
                        try {
                          await api.deleteChat(chat.id);
                          onDelete(chat.id);
                        } catch {
                          alert('Failed to delete chat');
                        }
                      }
                    }}
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