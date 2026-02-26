/**
 * src/lib/useArsenalSearch.ts
 * Phase 4.2: Arsenal search + filter logic (extracted for testability).
 * Searches title, role, target, tags; filters by role/category.
 */
import { useMemo, useState } from 'react';
import type { ArsenalItem } from '@/lib/schemas';

export interface ArsenalFilters {
  search: string;
  role: string;      // '' = all
  category: string;  // '' = all
}

export const DEFAULT_ARSENAL_FILTERS: ArsenalFilters = {
  search: '',
  role: '',
  category: '',
};

export function useArsenalSearch(items: ArsenalItem[]) {
  const [filters, setFilters] = useState<ArsenalFilters>(DEFAULT_ARSENAL_FILTERS);

  const filtered = useMemo(() => {
    let result = items;

    if (filters.role) {
      result = result.filter(item => item.role === filters.role);
    }

    if (filters.category) {
      result = result.filter(item => item.category === filters.category);
    }

    if (filters.search.trim()) {
      const q = filters.search.trim().toLowerCase();
      result = result.filter(item => {
        const fields = [item.title, item.role, item.target, ...(item.tags ?? [])]
          .filter(Boolean)
          .map(s => s!.toLowerCase());
        return fields.some(f => f.includes(q));
      });
    }

    return result;
  }, [items, filters]);

  // Unique roles and categories for filter dropdowns
  const roles = useMemo(() => [...new Set(items.map(i => i.role).filter(Boolean))].sort() as string[], [items]);
  const categories = useMemo(() => [...new Set(items.map(i => i.category).filter(Boolean))].sort() as string[], [items]);

  return { filters, setFilters, filtered, roles, categories };
}
