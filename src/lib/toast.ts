export type ToastNotice = {
  kind: "error" | "info";
  title: string;
  detail?: string;
  requestId?: string;
};

type ToastSubscriber = (notice: ToastNotice) => void;

const subscribers = new Set<ToastSubscriber>();

export const toast = {
  notify(notice: ToastNotice): void {
    subscribers.forEach((subscriber) => subscriber(notice));
  },
  subscribe(subscriber: ToastSubscriber): () => void {
    subscribers.add(subscriber);
    return () => subscribers.delete(subscriber);
  },
};
