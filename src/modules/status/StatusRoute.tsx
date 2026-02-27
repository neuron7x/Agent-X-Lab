import { useNavigate } from 'react-router-dom';
import { HomeScreen } from '@/components/axl/HomeScreen';
import { useAppState } from '@/state/AppStateProvider';

export function StatusRoute() {
  const navigate = useNavigate();
  const { githubState } = useAppState();

  return (
    <HomeScreen
      vrData={githubState.vrData}
      gates={githubState.gates}
      onViewPipeline={() => navigate('/pipeline')}
      onNavigateToArsenal={() => navigate('/arsenal')}
      contractError={githubState.contractError}
    />
  );
}
