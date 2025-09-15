import { useState, useCallback, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';
import { fileApi } from '@/lib/api';

export interface UploadedFile {
  id: string;
  file?: File;
  name: string;
  type?: string;
  size: number;
  uploadedAt: Date;
  isUploading?: boolean;
  uploadProgress?: number;
  isFromServer?: boolean;
  public_url?: string;
}

const ALLOWED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/markdown'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

export const useFileUpload = () => {
  const [localFiles, setLocalFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const queryClient = useQueryClient();

  // Fetch uploaded files from server
  const { data: serverFiles = [], isLoading: isLoadingFiles } = useQuery({
    queryKey: ['uploadedFiles'],
    queryFn: fileApi.getFiles,
    select: (files) => files.map((file): UploadedFile => ({
      id: crypto.randomUUID(),
      name: file.filename,
      size: file.size_bytes,
      uploadedAt: new Date(file.last_modified),
      isFromServer: true,
      public_url: file.permanent_url
    })),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress: (progress: number) => void }) =>
      fileApi.uploadFile(file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploadedFiles'] });
      toast({
        title: "File uploaded",
        description: "File uploaded successfully to server",
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      toast({
        title: "Upload failed",
        description: error.response?.data?.message || "Failed to upload file",
        variant: "destructive",
      });
    },
  });

  // Combine local and server files
  const uploadedFiles = useMemo(() => {
    return [...localFiles, ...(serverFiles || [])]
  }, [localFiles, serverFiles])

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.endsWith('.md')) {
      return 'Only PDF, DOCX, and MD files are allowed';
    }
    if (file.size > MAX_SIZE) {
      return 'File size must be less than 5MB';
    }
    return null;
  }, []);

  const addFile = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      toast({
        title: "Upload Error",
        description: error,
        variant: "destructive",
      });
      return false;
    }

    const tempId = crypto.randomUUID();
    const newFile: UploadedFile = {
      id: tempId,
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date(),
      isUploading: true,
      uploadProgress: 0,
    };

    // Add file to local state immediately for UI feedback
    setLocalFiles(prev => [...prev, newFile]);

    // Start upload
    uploadMutation.mutate({
      file,
      onProgress: (progress) => {
        setLocalFiles(prev => prev.map(f => 
          f.id === tempId 
            ? { ...f, uploadProgress: progress }
            : f
        ));
      }
    }, {
      onSuccess: () => {
        // Remove from local files as it will come from server files
        setLocalFiles(prev => prev.filter(f => f.id !== tempId));
      },
      onError: () => {
        // Remove failed upload from local files
        setLocalFiles(prev => prev.filter(f => f.id !== tempId));
      }
    });

    return true;
  }, [validateFile, uploadMutation]);

  const removeFile = useCallback((id: string) => {
    const file = uploadedFiles.find(f => f.id === id);
    
    if (file?.isFromServer) {
      // TODO: Add API call to delete server file when endpoint is available
      toast({
        title: "Cannot remove",
        description: "Server file removal not yet implemented",
        variant: "destructive",
      });
      return;
    }
    
    // Remove local file
    setLocalFiles(prev => prev.filter(file => file.id !== id));
    toast({
      title: "File removed",
      description: "File removed successfully",
    });
  }, [uploadedFiles]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    files.forEach(addFile);
  }, [addFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(addFile);
    e.target.value = '';
  }, [addFile]);

  return {
    uploadedFiles,
    isDragOver,
    isLoadingFiles,
    addFile,
    removeFile,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleFileInput,
  };
};