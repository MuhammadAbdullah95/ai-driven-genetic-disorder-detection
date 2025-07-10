export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Chat {
  id: string;
  title: string;
  chat_type: string;
  created_at: string;
  messages: Message[];
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  chat_history: Message[];
  chat_title: string;
}

export interface VariantInfo {
  chromosome: string;
  position: number;
  rsid: string;
  gene: string;
  reference: string;
  alternate: string;
  search_summary: string;
}

export interface AnalysisResponse {
  message: string;
  chat_id: string;
  variants_analyzed: number;
  results: VariantInfo[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  components: {
    database: string;
    ai_model: string;
    search_tools: string;
  };
}

export interface ApiError {
  detail: string;
  error_code?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
} 