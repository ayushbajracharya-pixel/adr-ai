import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import FileUpload from "./pages/FileUpload";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import { uiRoutes } from "./constants/uiRoutes";
import { SidebarProvider } from "./components/ui/sidebar";

const queryClient = new QueryClient();

const App = () => (
  <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <TooltipProvider>
            <SidebarProvider>
              <Toaster />
              <Sonner />
              <Routes>
                <Route path={uiRoutes.login} element={<Login />} />
                <Route path={uiRoutes.authCallback} element={<AuthCallback />} />
                <Route
                  path={uiRoutes.index}
                  element={
                    <ProtectedRoute>
                      <Index />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path={uiRoutes.files}
                  element={
                    <ProtectedRoute>
                      <FileUpload />
                    </ProtectedRoute>
                  }
                />

                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </SidebarProvider>
          </TooltipProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
