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
}

export interface QueryResponse {
  query: string;
  response: string;
  references: Reference[];
}

export const chatApi = {
  sendQuery: async (request: QueryRequest): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>('/query', request);
    return response.data;
  },
};