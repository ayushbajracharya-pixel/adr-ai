import { useState, useCallback, useMemo, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';
import { fileApi, UploadedFileResponse } from '@/lib/api';

export interface UploadedFile {
  id: string;
  file?: File;
  name: string;
  type?: string;
  size: number;
  uploadedAt: Date;
  isUploading?: boolean;
  isDeleting?: boolean;
  uploadProgress?: number;
  isFromServer?: boolean;
  public_url?: string;
  object_key?: string;
}

const ALLOWED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/markdown'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

export const useFileUpload = () => {
  const [localFiles, setLocalFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [deletingFileObjectKey, setDeletingFileObjectKey] = useState('');
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
      public_url: file.permanent_url,
      object_key: file.object_key
    })),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress: (progress: number) => void }) =>
      fileApi.uploadFile(file, onProgress),
    onSuccess: (response) => {
      // Optimistically update the query cache with the new file (in raw API response format, before select)
      queryClient.setQueryData<UploadedFileResponse[]>(['uploadedFiles'], (oldFiles = []) => {
        // Check if file already exists to avoid duplicates
        const exists = oldFiles.some(f => f.object_key === response.object_key || f.filename === response.filename);
        if (exists) {
          return oldFiles;
        }
        return [...oldFiles, response];
      });
      
      // Then invalidate to refetch and confirm
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

  const deleteMutation = useMutation({
    mutationFn: ({ objectKey }: { objectKey: string}) =>
      fileApi.deleteFile(objectKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploadedFiles'] });
      toast({
        title: "File Deleted",
        description: "File deleted successfully from server",
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      toast({
        title: "Delete failed",
        description: error.response?.data?.message || "Failed to delete file",
        variant: "destructive",
      });
    },
  });

  // Remove local files that have appeared in serverFiles
  useEffect(() => {
    if (serverFiles.length > 0 && localFiles.length > 0) {
      setLocalFiles(prev => {
        const serverFileNames = new Set(serverFiles.map(f => f.name));
        return prev.filter(localFile => {
          // Keep if still uploading, otherwise remove if it's in serverFiles
          return localFile.isUploading || !serverFileNames.has(localFile.name);
        });
      });
    }
  }, [serverFiles]);

  // Combine local and server files, avoiding duplicates
  const uploadedFiles = useMemo(() => {
    const serverFileNames = new Set(serverFiles.map(f => f.name));
    
    // Only show local files that don't exist in serverFiles yet
    const activeLocalFiles = localFiles.filter(localFile => {
      return !serverFileNames.has(localFile.name);
    });
    
    // Combine with server files, marking deleting ones
    const processedServerFiles = serverFiles.map(item => 
      item.object_key === deletingFileObjectKey 
        ? {...item, isDeleting: true} 
        : item
    );
    
    return [...activeLocalFiles, ...processedServerFiles];
  }, [localFiles, serverFiles, deletingFileObjectKey])

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
      onSuccess: (response) => {
        // Mark as not uploading but keep in localFiles until it appears in serverFiles
        setLocalFiles(prev => prev.map(f => 
          f.id === tempId 
            ? { ...f, isUploading: false, uploadProgress: 100 }
            : f
        ));
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

    setDeletingFileObjectKey(file.object_key);

    deleteMutation.mutate({
      objectKey: file.object_key,
    }, {
      onSettled: () => {
        setDeletingFileObjectKey("");
      }
    });

    // if (file?.isFromServer) {
    //   // TODO: Add API call to delete server file when endpoint is available
    //   toast({
    //     title: "Cannot remove",
    //     description: "Server file removal not yet implemented",
    //     variant: "destructive",
    //   });
    //   return;
    // }
    
    // // Remove local file
    // setLocalFiles(prev => prev.filter(file => file.id !== id));
    // toast({
    //   title: "File removed",
    //   description: "File removed successfully",
    // });
  }, [uploadedFiles, deleteMutation]);

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