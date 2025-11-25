import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  conversationApi,
  Conversation,
  ConversationCreate,
  ConversationUpdate,
} from "@/lib/api";

export const useConversations = () => {
  const queryClient = useQueryClient();

  const { data: conversations = [], isLoading } = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: () => conversationApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: ConversationCreate) => conversationApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ConversationUpdate }) =>
      conversationApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["conversation", variables.id],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  return {
    conversations,
    isLoading,
    createConversation: createMutation.mutateAsync,
    updateConversation: updateMutation.mutateAsync,
    deleteConversation: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
