import { toast } from "sonner";

export type NotifyPayload = {
  kind: "error" | "info";
  title: string;
  detail?: string;
  requestId?: string;
};

export const notify = ({ kind, title, detail, requestId }: NotifyPayload): void => {
  const description = [detail, requestId ? `request: ${requestId}` : undefined].filter(Boolean).join("\n");
  if (kind === "error") {
    toast.error(title, { description });
    return;
  }
  toast(title, { description });
};
