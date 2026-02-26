import { z } from "zod";

export const whoamiSchema = z
  .object({
    ok: z.boolean().optional(),
    user: z
      .object({
        email: z.string().optional(),
      })
      .passthrough()
      .optional(),
  })
  .passthrough();

export const dispatchResponseSchema = z
  .object({
    ok: z.boolean().optional(),
    dispatched: z.string().optional(),
    ts: z.string().optional(),
  })
  .passthrough();
