export type ChatSession = {
  id: string;
  title: string;
  updatedAt: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  error?: boolean;
};

export type UploadedAttachment = {
  id: string;
  name: string;
  status: "uploading" | "processing" | "completed" | "failed" | "unsupported";
  content?: string;
};
