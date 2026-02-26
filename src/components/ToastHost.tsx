import { useEffect, useState } from "react";
import { toast, type ToastNotice } from "@/lib/toast";

type ToastEntry = ToastNotice & { id: string };

export const ToastHost = (): JSX.Element => {
  const [items, setItems] = useState<ToastEntry[]>([]);

  useEffect(() => {
    return toast.subscribe((notice) => {
      const id = crypto.randomUUID();
      setItems((prev) => [...prev, { ...notice, id }]);
      setTimeout(() => {
        setItems((prev) => prev.filter((item) => item.id !== id));
      }, 5000);
    });
  }, []);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[200] flex w-[320px] flex-col gap-2">
      {items.map((item) => (
        <div
          key={item.id}
          className={`pointer-events-auto rounded border px-3 py-2 text-sm shadow ${
            item.kind === "error" ? "border-red-400 bg-red-50 text-red-900" : "border-blue-400 bg-blue-50 text-blue-900"
          }`}
        >
          <p className="font-semibold">{item.title}</p>
          {item.detail ? <p>{item.detail}</p> : null}
          {item.requestId ? <p className="text-xs opacity-80">request: {item.requestId}</p> : null}
        </div>
      ))}
    </div>
  );
};
