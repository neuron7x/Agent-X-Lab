/**
 * src/modules/index.ts
 * Lazy route components for code-splitting.
 * Each module loaded independently → smaller initial bundle.
 */
import { lazy } from 'react';

export const StatusRoute   = lazy(() => import('./status/StatusRoute').then(m => ({ default: m.StatusRoute })));
export const PipelineRoute = lazy(() => import('./pipeline/PipelineRoute').then(m => ({ default: m.PipelineRoute })));
export const EvidenceRoute = lazy(() => import('./evidence/EvidenceRoute').then(m => ({ default: m.EvidenceRoute })));
export const ArsenalRoute  = lazy(() => import('./arsenal/ArsenalRoute').then(m => ({ default: m.ArsenalRoute })));
export const ForgeRoute    = lazy(() => import('./forge/ForgeRoute').then(m => ({ default: m.ForgeRoute })));
export const SettingsRoute = lazy(() => import('./settings/SettingsRoute').then(m => ({ default: m.SettingsRoute })));
