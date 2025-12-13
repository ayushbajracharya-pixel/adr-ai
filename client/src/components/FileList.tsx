import { FileText, File, Loader2, X } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { UploadedFile } from "@/hooks/useFileUpload";
import { Button } from "./ui/button";

interface FileListProps {
  files: UploadedFile[];
  onRemove: (id: string) => void;
  isLoading?: boolean;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const getFileIcon = (fileName: string) => {
  return <FileText className="h-5 w-5 text-primary" />;
};

const getFileTypeBadge = (fileName: string) => {
  const extension = fileName.split(".").pop()?.toLowerCase();
  return (
    <Badge variant="secondary" className="text-xs">
      {extension?.toUpperCase() || "FILE"}
    </Badge>
  );
};

export const FileList = ({
  files,
  onRemove,
  isLoading = false,
}: FileListProps) => {
  if (files.length === 0 && !isLoading) {
    return (
      <div className="text-center py-12">
        <File className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">No files uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Uploaded Files ({files.length})
      </h3>

      {files.map((file) => {
        // Don't make it a link if file is still uploading or doesn't have a URL yet
        const fileContent = (
          <Card className={`p-4 transition-shadow ${file.public_url && !file.isUploading ? 'hover:shadow-md cursor-pointer' : ''}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {file.isUploading || file.isDeleting ? (
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                ) : (
                  getFileIcon(file.name)
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <p className="text-sm font-medium text-foreground truncate">
                      {file.name}
                    </p>
                    {getFileTypeBadge(file.name)}
                    {/* {file.isFromServer && (
                      <Badge variant="outline" className="text-xs">
                        Server
                      </Badge>
                    )} */}
                  </div>

                  <div className="flex items-center space-x-4 text-xs text-muted-foreground mb-2">
                    <span>{formatFileSize(file.size)}</span>
                    <span>
                      {file.isUploading
                        ? "Uploading..."
                        : `Uploaded ${file.uploadedAt.toLocaleDateString()}`}
                    </span>
                  </div>

                  {file.isUploading &&
                    typeof file.uploadProgress === "number" && (
                      <div className="space-y-1">
                        <Progress value={file.uploadProgress} className="h-2" />
                        <p className="text-xs text-muted-foreground">
                          {file.uploadProgress}% uploaded
                        </p>
                      </div>
                    )}
                </div>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onRemove(file.id);
                }}
                className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 ml-4"
                disabled={file.isUploading || file.isDeleting}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        );

        // Only wrap in link if file has a public URL and is not uploading
        if (file.public_url && !file.isUploading) {
          return (
            <a key={file.id} target="_blank" href={file.public_url} rel="noopener noreferrer">
              {fileContent}
            </a>
          );
        }

        return <div key={file.id}>{fileContent}</div>;
      })}
    </div>
  );
};
