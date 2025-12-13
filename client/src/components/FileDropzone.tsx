import { useRef } from "react";
import { Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isDragOver: boolean;
}

export const FileDropzone = ({
  onDrop,
  onDragOver,
  onDragLeave,
  onFileInput,
  isDragOver,
}: FileDropzoneProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={handleClick}
      className={cn(
        "relative cursor-pointer transition-all duration-300 ease-in-out",
        "border-2 border-dashed rounded-lg p-12",
        "flex flex-col items-center justify-center space-y-6",
        "hover:bg-accent/5 hover:border-primary/30",
        isDragOver
          ? "border-primary bg-primary/5 scale-[1.02]"
          : "border-muted-foreground/25"
      )}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown"
        multiple
        onChange={onFileInput}
        className="hidden"
      />

      <div
        className={cn(
          "rounded-full p-6 transition-colors duration-300",
          isDragOver ? "bg-primary/10" : "bg-muted/20"
        )}
      >
        {isDragOver ? (
          <Upload className="h-12 w-12 text-primary animate-bounce" />
        ) : (
          <FileText className="h-12 w-12 text-muted-foreground" />
        )}
      </div>

      <div className="text-center space-y-3">
        <h3 className="text-xl font-semibold text-foreground">
          {isDragOver ? "Drop your files here" : "Upload your documents"}
        </h3>
        <p className="text-muted-foreground max-w-sm">
          Drag and drop your files here, or click to browse. Supports PDF, DOCX,
          and MD files up to 5MB.
        </p>
      </div>

      <Button
        variant="outline"
        className="mt-4 hover:bg-primary hover:text-primary-foreground transition-colors"
      >
        <Upload className="h-4 w-4 mr-2" />
        Choose Files
      </Button>

      {isDragOver && (
        <div className="absolute inset-0 bg-primary/5 rounded-lg pointer-events-none" />
      )}
    </div>
  );
};
