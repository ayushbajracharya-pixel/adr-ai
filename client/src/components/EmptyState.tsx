import { Card } from '@/components/ui/card';
import { MessageSquare, FileSearch, Zap, Brain } from 'lucide-react';

export const EmptyState = () => {
  const suggestions = [
    {
      icon: FileSearch,
      title: "Document Analysis",
      description: "Ask about specific documents or ADRs",
      example: "What are the main architectural decisions we've made?"
    },
    {
      icon: Brain,
      title: "Technical Questions",
      description: "Get insights on technologies and patterns",
      example: "What are the pros and cons of using Kafka?"
    },
    {
      icon: Zap,
      title: "Quick Queries",
      description: "Ask for summaries or explanations",
      example: "Summarize our microservices architecture approach"
    }
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
        <MessageSquare className="w-8 h-8 text-primary" />
      </div>
      
      <h2 className="text-2xl font-semibold mb-2">Welcome to AI Assistant</h2>
      <p className="text-muted-foreground text-center mb-8 max-w-md">
        I can help you analyze documents, answer technical questions, and provide insights 
        based on your architectural decision records.
      </p>
      
      <div className="grid gap-4 max-w-2xl w-full">
        {suggestions.map((suggestion, index) => {
          const Icon = suggestion.icon;
          return (
            <Card key={index} className="p-4 hover:shadow-message transition-shadow">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium mb-1">{suggestion.title}</h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    {suggestion.description}
                  </p>
                  <p className="text-xs text-primary bg-primary/10 px-2 py-1 rounded font-mono">
                    "{suggestion.example}"
                  </p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};