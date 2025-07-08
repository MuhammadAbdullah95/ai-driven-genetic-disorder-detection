import { Chat } from '@/types/api';
import { Plus, Power } from 'lucide-react';
import api from '@/lib/api';

interface SidebarProps {
  chats: Chat[];
  selectedChatId: string | null;
  onSelect: (chat: Chat) => void;
  onNewChat: () => void;
}

export default function Sidebar({ chats, selectedChatId, onSelect, onNewChat }: SidebarProps) {
  return (
    <aside className="w-72 bg-gray-900 text-white flex flex-col h-full border-r border-gray-800">
      {/* App Title */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-gray-800">
        <span className="font-bold text-lg tracking-wide">Genetic Chat</span>
      </div>
      {/* New Chat Button */}
      <button
        className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 m-4 rounded transition font-medium"
        onClick={onNewChat}
      >
        <Plus className="h-5 w-5" />
        New chat
      </button>
      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-2">
        {chats.length === 0 ? (
          <div className="text-gray-400 px-2 py-4">No chats yet.</div>
        ) : (
          <ul className="space-y-1">
            {chats.map(chat => (
              <li
                key={chat.id}
                className={`px-3 py-2 rounded cursor-pointer flex items-center transition-colors ${selectedChatId === chat.id ? 'bg-gray-700 text-primary-400 font-semibold' : 'hover:bg-gray-800'}`}
                onClick={() => onSelect(chat)}
              >
                <span className="truncate">{chat.title}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      {/* Logout Button */}
      <button
        className="flex items-center gap-2 bg-gray-800 hover:bg-red-700 text-red-400 hover:text-white px-4 py-3 m-4 rounded transition font-medium mt-auto"
        onClick={() => api.logout()}
      >
        <Power className="h-5 w-5" />
        Logout
      </button>
    </aside>
  );
} 