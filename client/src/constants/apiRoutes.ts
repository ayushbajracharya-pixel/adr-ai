export const apiRoutes = {
    query: '/query',
    listFiles: '/files',
    uploadFile: '/upload',
    deleteFile: '/files/:objectKey',
    auth: {
        googleLogin: '/auth/google/login',
        me: '/auth/me',
        logout: '/auth/logout',
    }
}