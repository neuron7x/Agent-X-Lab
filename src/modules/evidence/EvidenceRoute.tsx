import { EvidenceScreen } from '@/components/axl/EvidenceScreen';
import { useAppState } from '@/state/AppStateProvider';

export function EvidenceRoute() {
  const { githubState } = useAppState();

  return (
    <EvidenceScreen
      entries={githubState.evidence}
      prs={githubState.prs}
      parseFailures={githubState.parseFailures}
    />
  );
}
