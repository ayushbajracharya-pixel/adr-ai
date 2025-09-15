import { useMutation } from '@tanstack/react-query';
import { chatApi, QueryRequest, QueryResponse } from '@/lib/api';
import { useState } from 'react';
import { sanitizeHtml } from '@/lib/utils';

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  references?: QueryResponse['references'];
}

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const sendMessageMutation = useMutation({
    mutationFn: chatApi.sendQuery,
    onMutate: async (request: QueryRequest) => {
      // Add user message immediately
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'user',
        content: request.query,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, userMessage]);
      return { userMessage };
    },
    onSuccess: (data: QueryResponse) => {
      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: sanitizeHtml(data.response) ,
        timestamp: new Date(),
        references: data.references,
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    },
    onError: (error) => {
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      console.error('Chat error:', error);
    },
  });

  const sendMessage = (query: string) => {
    if (query.trim()) {
      sendMessageMutation.mutate({ query: query.trim() });
    }
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return {
    messages,
    sendMessage,
    clearMessages,
    isLoading: sendMessageMutation.isPending,
    error: sendMessageMutation.error,
  };
};