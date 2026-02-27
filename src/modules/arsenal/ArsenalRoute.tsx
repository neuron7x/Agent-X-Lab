import { ArsenalScreen } from '@/components/axl/ArsenalScreen';
import { useAppState } from '@/state/AppStateProvider';

export function ArsenalRoute() {
  const { arsenalState } = useAppState();

  return <ArsenalScreen prompts={arsenalState.prompts} isLoading={arsenalState.isLoading} />;
}
