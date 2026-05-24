import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { useState } from "react";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import StartupSplash from "@/components/StartupSplash";
import Index from "./pages/Index.tsx";
import WalletPage from "./pages/WalletPage.tsx";
import TokenPage from "./pages/TokenPage.tsx";
import AlphaIntelPage from "./pages/AlphaIntelPage.tsx";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => {
  const [booted, setBooted] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        {!booted && <StartupSplash onDone={() => setBooted(true)} />}
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/alpha-intel" element={<AlphaIntelPage />} />
            <Route path="/wallet/:address" element={<WalletPage />} />
            <Route path="/token/:ticker" element={<TokenPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
