export interface Character {
  id: string;
  name: string;
  gender: 'male' | 'female' | 'other';
  avatar_url: string | null;
  system_prompt: string;
  opening_message?: string;
  personality: string[];
  voice_id: string | null;
  is_public: boolean;
  creator_id: string;
  creator_name?: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface User {
  id: string;
  username: string;
  email?: string;
}

export interface ChatSession {
  id: string;
  character_id: string;
  character?: Character;
  created_at: string;
}
