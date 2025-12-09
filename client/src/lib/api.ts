import { apiRoutes } from "@/constants/apiRoutes";
import { envConstants } from "@/constants/env-contants";
import axios from "axios";

const api = axios.create({
  baseURL: envConstants.API_BASE_URL,
  timeout: 30000,
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid, clear it and redirect to login
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

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

export interface User {
  email: string;
  name: string;
  picture?: string;
}

export interface Conversation {
  id: string;
  user_email: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  references?: Reference[] | null;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ConversationCreate {
  title?: string | null;
}

export interface ConversationUpdate {
  title: string;
}

export const authApi = {
  getMe: async (token?: string): Promise<User> => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const response = await api.get<User>(apiRoutes.auth.me, { headers });
    return response.data;
  },
  logout: async (): Promise<void> => {
    await api.post(apiRoutes.auth.logout);
  },
};

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
    formData.append("file", file);

    const response = await api.post<UploadedFileResponse>(
      apiRoutes.uploadFile,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(progress);
          }
        },
      }
    );
    return response.data;
  },

  getFiles: async (): Promise<UploadedFileResponse[]> => {
    const response = await api.get<UploadedFileResponse[]>(apiRoutes.listFiles);
    return response.data;
  },

  deleteFile: async (object_key): Promise<DeletedFileResponse[]> => {
    const response = await api.delete<DeletedFileResponse[]>(
      apiRoutes.deleteFile.replace(":objectKey", object_key)
    );
    return response.data;
  },
};

export const conversationApi = {
  list: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>(
      apiRoutes.conversations.list
    );
    return response.data;
  },

  create: async (data: ConversationCreate): Promise<Conversation> => {
    const response = await api.post<Conversation>(
      apiRoutes.conversations.create,
      data
    );
    return response.data;
  },

  get: async (conversationId: string): Promise<ConversationWithMessages> => {
    const response = await api.get<ConversationWithMessages>(
      apiRoutes.conversations.get.replace(":conversationId", conversationId)
    );
    return response.data;
  },

  update: async (
    conversationId: string,
    data: ConversationUpdate
  ): Promise<Conversation> => {
    const response = await api.patch<Conversation>(
      apiRoutes.conversations.update.replace(":conversationId", conversationId),
      data
    );
    return response.data;
  },

  delete: async (conversationId: string): Promise<void> => {
    await api.delete(
      apiRoutes.conversations.delete.replace(":conversationId", conversationId)
    );
  },

  sendMessage: async (
    conversationId: string,
    request: QueryRequest
  ): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>(
      apiRoutes.conversations.sendMessage.replace(
        ":conversationId",
        conversationId
      ),
      request
    );
    return response.data;
  },
};
