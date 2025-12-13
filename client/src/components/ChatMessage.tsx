import { ChatMessage as ChatMessageType } from "@/hooks/useChat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { User, Bot, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.type === "user";

  return (
    <div
      className={cn(
        "flex gap-4 animate-fade-in",
        isUser ? "justify-end" : "justify-start w-full"
      )}
    >
      {/* {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <Bot className="w-4 h-4 text-primary-foreground" />
        </div>
      )} */}

      <Card
        className={cn(
          "py-2 px-4 rounded-3xl shadow-message",
          isUser
            ? "max-w-[80%] bg-chat-user text-chat-user-foreground"
            : "w-full bg-transparent text-white border-none"
        )}
      >
        <div className="prose text-base dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-code:text-foreground prose-pre:text-foreground prose-a:text-primary">
          <div
            dangerouslySetInnerHTML={{
              // Sanitize the HTML content before setting it
              __html: message.content,
            }}
            className="whitespace-pre-wrap break-words"
          />

          {message.references && message.references.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4" />
                <span className="text-sm font-medium">References</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {message.references.map((ref, index) => (
                  <a
                    href={ref.public_url}
                    target="_blank"
                    key={`${ref.public_url}_${index}`}
                  >
                    <Badge variant="secondary" className="text-xs">
                      {ref.filename}
                    </Badge>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
          <User className="w-4 h-4 text-muted-foreground" />
        </div>
      )} */}
    </div>
  );
};
