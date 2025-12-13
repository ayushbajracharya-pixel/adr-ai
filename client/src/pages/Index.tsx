import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import { ChatHeader } from "@/components/ChatHeader";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { EmptyState } from "@/components/EmptyState";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { uiRoutes } from "@/constants/uiRoutes";
import { File, Plus, Trash2, MessageSquare } from "lucide-react";
import { conversationApi } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const Index = () => {
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  
  const queryClient = useQueryClient();
  const { conversations, isLoading: conversationsLoading, createConversation, deleteConversation, isDeleting } = useConversations();
  const { messages, sendMessage, clearMessages, isLoading, conversation } = useChat(currentConversationId);
  
  // Enhanced send message that creates conversation if needed
  const handleSendMessage = async (message: string) => {
    if (!currentConversationId) {
      // Create a new conversation first, then send message
      setIsInitialLoading(true);
      try {
        const newConv = await createConversation({ title: null });
        setCurrentConversationId(newConv.id);
        // Send message after conversation is created
        try {
          await conversationApi.sendMessage(newConv.id, { query: message });
          // Refresh conversations and messages
          queryClient.invalidateQueries({ queryKey: ['conversation', newConv.id] });
          queryClient.invalidateQueries({ queryKey: ['conversations'] });
        } catch (error) {
          console.error("Failed to send message:", error);
          setIsInitialLoading(false);
        }
      } catch (error) {
        console.error("Failed to create conversation:", error);
        setIsInitialLoading(false);
      }
    } else {
      // Send message using existing conversation
      sendMessage(message);
    }
  };
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages]);

  // Reset initial loading state when messages arrive
  useEffect(() => {
    if (messages.length > 0 && isInitialLoading) {
      setIsInitialLoading(false);
    }
  }, [messages, isInitialLoading]);

  // Create new conversation
  const handleNewConversation = async () => {
    try {
      const newConv = await createConversation({ title: null });
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  };

  // Select conversation
  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id);
  };

  // Delete conversation
  const handleDeleteClick = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversationToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (conversationToDelete) {
      try {
        await deleteConversation(conversationToDelete);
        if (currentConversationId === conversationToDelete) {
          setCurrentConversationId(null);
          clearMessages();
        }
        setDeleteDialogOpen(false);
        setConversationToDelete(null);
      } catch (error) {
        console.error("Failed to delete conversation:", error);
      }
    }
  };

  return (
    <div className="flex h-screen w-full bg-gradient-chat">
      {/* Sidebar */}
      <Sidebar className="w-64 border-r">
        <SidebarHeader className="p-4">
          <Button
            onClick={handleNewConversation}
            className="w-full"
            variant="default"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Conversation
          </Button>
        </SidebarHeader>
        <SidebarContent>
          <SidebarMenu>
            {conversationsLoading ? (
              <div className="p-4 flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mb-2"></div>
                <div className="text-sm text-muted-foreground">Loading conversations...</div>
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground text-center">
                No conversations yet. Start a new one!
              </div>
            ) : (
              conversations.map((conv) => (
                <SidebarMenuItem key={conv.id}>
                  <div className="flex items-center w-full group">
                    <SidebarMenuButton
                      onClick={() => handleSelectConversation(conv.id)}
                      className={`flex-1 justify-start ${
                        currentConversationId === conv.id ? "bg-accent" : ""
                      }`}
                    >
                      <MessageSquare className="h-4 w-4 mr-2" />
                      <span className="truncate">
                        {conv.title || "New Conversation"}
                      </span>
                    </SidebarMenuButton>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="opacity-0 group-hover:opacity-100 h-8 w-8"
                      onClick={(e) => handleDeleteClick(conv.id, e)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </SidebarMenuItem>
              ))
            )}
          </SidebarMenu>
        </SidebarContent>
      </Sidebar>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col w-full mx-auto bg-background shadow-chat">
        <ChatHeader
          onClearMessages={clearMessages}
          messageCount={messages.length}
          conversationTitle={conversation?.title || null}
        />
        <div className="mt-2 text-right px-4">
          <Link to={uiRoutes.files}>
            <Button variant="outline" className="gap-2">
              <File className="h-4 w-4" />
              Go to files
            </Button>
          </Link>
        </div>

        <div className="flex-1 flex flex-col min-h-0 max-w-5xl w-full mx-auto">
          {messages.length === 0 ? (
            isLoading || isInitialLoading ? (
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-6">
                  <div className="flex justify-start">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center mr-4">
                      <div className="w-4 h-4 bg-primary-foreground rounded-full animate-pulse" />
                    </div>
                    <div className="bg-chat-assistant rounded-lg p-4 shadow-message">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                        <div
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        />
                        <div
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </ScrollArea>
            ) : (
              <EmptyState />
            )
          ) : (
            <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
              <div className="space-y-6">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center mr-4">
                      <div className="w-4 h-4 bg-primary-foreground rounded-full animate-pulse" />
                    </div>
                    <div className="bg-chat-assistant rounded-lg p-4 shadow-message">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                        <div
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        />
                        <div
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}

          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading || isInitialLoading || conversationsLoading}
            placeholder="Type your message..."
          />
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Conversation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Index;
