/**
 * src/hooks/useVirtualList.ts
 * Phase 6: Windowed rendering for large lists (≥ 50 items).
 * Uses @tanstack/react-virtual — already in deps.
 * Target: scroll performance ≥ 60fps on mid-range device.
 *
 * Usage:
 *   const { parentRef, virtualizer } = useVirtualList({ count: items.length, estimateSize: () => 48 });
 *   <div ref={parentRef} style={{ height: 400, overflow: 'auto' }}>
 *     <div style={{ height: virtualizer.getTotalSize() + 'px', position: 'relative' }}>
 *       {virtualizer.getVirtualItems().map(row => (
 *         <div key={row.key} style={{ position: 'absolute', top: row.start, width: '100%' }}>
 *           {items[row.index]}
 *         </div>
 *       ))}
 *     </div>
 *   </div>
 */
import { useRef } from 'react';
import { useVirtualizer, type VirtualizerOptions } from '@tanstack/react-virtual';

type VirtualListOptions = Pick<
  VirtualizerOptions<HTMLDivElement, Element>,
  'count' | 'estimateSize' | 'overscan' | 'paddingStart' | 'paddingEnd'
>;

/**
 * Only activates windowing if count >= threshold (default 50).
 * Below threshold: returns null virtualizer → render all items normally.
 */
export function useVirtualList(opts: VirtualListOptions & { threshold?: number }) {
  const { threshold = 50, ...virtualizerOpts } = opts;
  const parentRef = useRef<HTMLDivElement>(null);

  const shouldVirtualize = opts.count >= threshold;

  // Always call the hook (hooks rules), but only use result when above threshold
  const virtualizer = useVirtualizer({
    ...virtualizerOpts,
    getScrollElement: () => parentRef.current,
    overscan: opts.overscan ?? 5,
  });

  return {
    parentRef,
    virtualizer: shouldVirtualize ? virtualizer : null,
    shouldVirtualize,
  };
}
