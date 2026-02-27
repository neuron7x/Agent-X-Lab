import { useQuery } from '@tanstack/react-query';
import type { GitHubSettings } from '@/lib/types';
import { fetchArsenalIndex } from '@/lib/github';
import { MOCK_ARSENAL } from '@/lib/mockData';

export function useArsenal(settings: GitHubSettings, isConfigured: boolean, demoMode: boolean) {
  const query = useQuery({
    queryKey: ['arsenal', settings.owner, settings.repo],
    queryFn: () => fetchArsenalIndex(settings),
    enabled: isConfigured && !demoMode,
    staleTime: 10 * 60 * 1000, // 10 min
    retry: 1,
  });

  if (demoMode) {
    return {
      prompts: MOCK_ARSENAL,
      isLoading: false,
      error: null,
    };
  }

  return {
    prompts: query.data || [],
    isLoading: query.isLoading,
    error: query.error ? (query.error as Error).message : null,
  };
}
