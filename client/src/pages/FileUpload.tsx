import { Link } from "react-router-dom";
import { MessageCircle, Upload, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileDropzone } from "@/components/FileDropzone";
import { FileList } from "@/components/FileList";
import { useFileUpload } from "@/hooks/useFileUpload";
import { useAuth } from "@/contexts/AuthContext";
import { uiRoutes } from "@/constants/uiRoutes";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/ThemeToggle";

const FileUpload = () => {
  const {
    uploadedFiles,
    isDragOver,
    isLoadingFiles,
    removeFile,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleFileInput,
  } = useFileUpload();
  const { user, logout } = useAuth();

  const getInitials = (name?: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="min-h-screen w-full bg-gradient-chat">
      <div className="container mx-auto px-4 py-8 w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Document Upload
            </h1>
            <p className="text-muted-foreground">
              Upload your documents to get started with AI-powered insights
            </p>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to={uiRoutes.index}>
              <Button variant="outline" className="gap-2">
                <MessageCircle className="h-4 w-4" />
                Go to Chat
              </Button>
            </Link>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback>{getInitials(user?.name)}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user?.name || "User"}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="cursor-pointer">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Upload Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Files
              </h2>

              <FileDropzone
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onFileInput={handleFileInput}
                isDragOver={isDragOver}
              />
            </div>

            {/* File Types Info */}
            <div className="bg-card rounded-lg p-4 border">
              <h4 className="font-medium text-foreground mb-2">
                Supported File Types
              </h4>
              <div className="space-y-1 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-primary rounded-full"></span>
                  PDF documents (.pdf)
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-primary rounded-full"></span>
                  Word documents (.docx)
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-primary rounded-full"></span>
                  Markdown files (.md)
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Maximum file size: 5MB per file
              </p>
            </div>
          </div>

          {/* File List Section */}
          <div>
            <FileList
              files={uploadedFiles}
              onRemove={removeFile}
              isLoading={isLoadingFiles}
            />
          </div>
        </div>

        {/* Action Section */}
        {uploadedFiles.length > 0 && (
          <div className="mt-12 text-center">
            <div className="bg-card rounded-lg p-6 border">
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Ready to start chatting?
              </h3>
              <p className="text-muted-foreground mb-4">
                Your documents are uploaded and ready. Start a conversation to
                get insights from your files.
              </p>
              <Link to={uiRoutes.index}>
                <Button className="gap-2">
                  <MessageCircle className="h-4 w-4" />
                  Start Chatting
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
