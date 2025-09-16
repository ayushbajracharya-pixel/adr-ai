import { apiRoutes } from '@/constants/apiRoutes';
import { envConstants } from '@/constants/env-contants';
import axios from 'axios';

const api = axios.create({
  baseURL: envConstants.API_BASE_URL,
  timeout: 30000,
});

export interface QueryRequest {
  query: string;
}

export interface Reference {
  filename: string;
  adr_number: string;
  title: string;
  status: string;
  author: string;
  date: string;
  source: string;
  public_url: string;
  s3_uri: string;
}

export interface QueryResponse {
  query: string;
  response: string;
  references: Reference[];
}

export interface UploadedFileResponse {
  object_key: string;
  filename: string;
  size_bytes: number;
  last_modified: string;
  permanent_url: string;
}

export interface DeletedFileResponse {
  object_key: string;
}


export const chatApi = {
  sendQuery: async (request: QueryRequest): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>(apiRoutes.query, request);
    return response.data;
  },
};

export const fileApi = {
  uploadFile: async (
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<UploadedFileResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadedFileResponse>(apiRoutes.uploadFile, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  getFiles: async (): Promise<UploadedFileResponse[]> => {
    const response = await api.get<UploadedFileResponse[]>(apiRoutes.listFiles);
    return response.data;
  },

  deleteFile: async (object_key): Promise<DeletedFileResponse[]> => {
    const response = await api.delete<DeletedFileResponse[]>(apiRoutes.deleteFile.replace(":objectKey", object_key));
    return response.data;
  }
};