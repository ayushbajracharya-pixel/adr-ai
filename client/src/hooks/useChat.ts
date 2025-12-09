import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  conversationApi,
  QueryRequest,
  QueryResponse,
  Conversation,
  ConversationWithMessages,
} from "@/lib/api";
import { useState, useEffect } from "react";
import { sanitizeHtml } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  references?: QueryResponse["references"];
}

export const useChat = (conversationId: string | null) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const queryClient = useQueryClient();

  // Load conversation messages if conversationId is provided
  const { data: conversation } = useQuery<ConversationWithMessages>({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversationApi.get(conversationId!),
    enabled: !!conversationId,
  });

  // Update messages when conversation loads
  useEffect(() => {
    if (conversation) {
      const formattedMessages: ChatMessage[] = conversation.messages.map(
        (msg) => ({
          id: msg.id,
          type: msg.role,
          content:
            msg.role === "assistant" ? sanitizeHtml(msg.content) : msg.content,
          timestamp: new Date(msg.created_at),
          references: msg.references || undefined,
        })
      );
      setMessages(formattedMessages);
    } else if (!conversationId) {
      // Clear messages if no conversation
      setMessages([]);
    }
  }, [conversation, conversationId]);

  const sendMessageMutation = useMutation({
    mutationFn: (request: QueryRequest) => {
      if (!conversationId) {
        throw new Error("No conversation selected");
      }
      return conversationApi.sendMessage(conversationId, request);
    },
    onMutate: async (request: QueryRequest) => {
      // Add user message immediately
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        type: "user",
        content: request.query,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      return { userMessage };
    },
    onSuccess: (data: QueryResponse) => {
      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: `temp-${Date.now() + 1}`,
        type: "assistant",
        content: sanitizeHtml(data.response),
        timestamp: new Date(),
        references: data.references,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Invalidate conversation query to refetch with new messages
      if (conversationId) {
        queryClient.invalidateQueries({
          queryKey: ["conversation", conversationId],
        });
      }
    },
    onError: (error) => {
      // Add error message
      const errorMessage: ChatMessage = {
        id: `temp-${Date.now() + 1}`,
        type: "assistant",
        content:
          "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
      console.error("Chat error:", error);
    },
  });

  const sendMessage = (query: string) => {
    if (query.trim() && conversationId) {
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
    conversation,
  };
};
