export const apiRoutes = {
  query: "/query",
  listFiles: "/files",
  uploadFile: "/upload",
  deleteFile: "/files/:objectKey",
  auth: {
    googleLogin: "/auth/google/login",
    me: "/auth/me",
    logout: "/auth/logout",
  },
  conversations: {
    list: "/conversations",
    create: "/conversations",
    get: "/conversations/:conversationId",
    update: "/conversations/:conversationId",
    delete: "/conversations/:conversationId",
    sendMessage: "/conversations/:conversationId/messages",
  },
};
