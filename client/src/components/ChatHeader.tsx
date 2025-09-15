import { Button } from "@/components/ui/button";
import { MessageSquare, Trash2 } from "lucide-react";

interface ChatHeaderProps {
  onClearMessages: () => void;
  messageCount: number;
}

export const ChatHeader = ({
  onClearMessages,
  messageCount,
}: ChatHeaderProps) => {
  return (
    <header className="flex items-center justify-between p-4 border-b border-border bg-card">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <MessageSquare className="w-4 h-4 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">AI Assistant</h1>
          <p className="text-sm text-muted-foreground">
            Ask me anything about your documents
          </p>
        </div>
      </div>

      {messageCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearMessages}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Clear
        </Button>
      )}
    </header>
  );
};
