/**
 * src/components/axl/ArsenalSearchBar.tsx
 * Phase 4.2: Arsenal search + role/category filter UI.
 * I5: keyboard accessible, aria-labels on all controls.
 */
import type { ArsenalFilters } from '@/lib/useArsenalSearch';

interface Props {
  filters: ArsenalFilters;
  onChange: (f: ArsenalFilters) => void;
  roles: string[];
  categories: string[];
  totalCount: number;
  shownCount: number;
  lang?: 'ua' | 'en';
}

export function ArsenalSearchBar({ filters, onChange, roles, categories, totalCount, shownCount, lang = 'en' }: Props) {
  return (
    <div
      role="search"
      aria-label={lang === 'ua' ? 'Пошук промптів' : 'Arsenal search'}
      style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12, alignItems: 'center' }}
    >
      {/* Text search */}
      <input
        type="search"
        aria-label={lang === 'ua' ? 'Пошук промптів' : 'Search prompts'}
        placeholder={lang === 'ua' ? 'Пошук: назва, роль, теги…' : 'Search: title, role, tags…'}
        value={filters.search}
        onChange={e => onChange({ ...filters, search: e.target.value })}
        style={{
          flex: '1 1 160px', minWidth: 140,
          fontSize: 12, fontFamily: 'monospace',
          background: 'var(--bg-tertiary,#111)',
          color: 'var(--text-primary,#fff)',
          border: '1px solid var(--border-dim,#333)',
          borderRadius: 4, padding: '4px 8px', outline: 'none',
        }}
      />

      {/* Role filter */}
      {roles.length > 0 && (
        <select
          aria-label={lang === 'ua' ? 'Роль' : 'Role filter'}
          value={filters.role}
          onChange={e => onChange({ ...filters, role: e.target.value })}
          style={{
            fontSize: 11, fontFamily: 'monospace',
            background: 'var(--bg-tertiary,#111)',
            color: filters.role ? 'var(--text-primary,#fff)' : 'var(--text-tertiary,#555)',
            border: '1px solid var(--border-dim,#333)',
            borderRadius: 4, padding: '4px 6px', outline: 'none',
          }}
        >
          <option value="">{lang === 'ua' ? 'Всі ролі' : 'All roles'}</option>
          {roles.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      )}

      {/* Category filter */}
      {categories.length > 0 && (
        <select
          aria-label={lang === 'ua' ? 'Категорія' : 'Category filter'}
          value={filters.category}
          onChange={e => onChange({ ...filters, category: e.target.value })}
          style={{
            fontSize: 11, fontFamily: 'monospace',
            background: 'var(--bg-tertiary,#111)',
            color: filters.category ? 'var(--text-primary,#fff)' : 'var(--text-tertiary,#555)',
            border: '1px solid var(--border-dim,#333)',
            borderRadius: 4, padding: '4px 6px', outline: 'none',
          }}
        >
          <option value="">{lang === 'ua' ? 'Всі категорії' : 'All categories'}</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      )}

      {/* Clear */}
      {(filters.search || filters.role || filters.category) && (
        <button
          onClick={() => onChange({ search: '', role: '', category: '' })}
          aria-label={lang === 'ua' ? 'Очистити фільтри' : 'Clear filters'}
          style={{
            fontSize: 11, color: 'var(--signal-fail,#ff3b30)',
            background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px 6px',
          }}
        >
          ✕ {lang === 'ua' ? 'очистити' : 'clear'}
        </button>
      )}

      {/* Count */}
      <span style={{ fontSize: 11, color: 'var(--text-tertiary,#555)', fontFamily: 'monospace' }}>
        {shownCount}/{totalCount}
      </span>
    </div>
  );
}
