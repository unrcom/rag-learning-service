export const API_CONFIG = {
  v1: {
    baseUrl: "", // 既存のNext.js API Routes
    chatEndpoint: "/api/chat",
  },
  v2: {
    baseUrl: "http://localhost:8000", // FastAPI
    chatEndpoint: "/api/v2/chat",
  },
};

export const getCurrentAPI = () => {
  // 環境変数でAPIバージョンを切り替え
  const useV2 = process.env.NEXT_PUBLIC_USE_API_V2 === "true";
  console.log(`🔧 Using API: ${useV2 ? "v2 (FastAPI)" : "v1 (Next.js)"}`);
  return useV2 ? API_CONFIG.v2 : API_CONFIG.v1;
};
