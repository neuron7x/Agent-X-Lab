import { PipelineScreen } from '@/components/axl/PipelineScreen';
import { useAppState } from '@/state/AppStateProvider';

export function PipelineRoute() {
  const { githubState } = useAppState();

  return <PipelineScreen gates={githubState.gates} contractError={githubState.contractError} />;
}
