# AXL — One Integrated System Pack

Це **єдина інтегрована, конфігурована** збірка, яка **нічого не ламає** і **не втрачає дані**.
Вона зберігає всі джерела як snapshots та додає Control Plane шар, який описує «як це все зшито».

## Структура
- `workspace/full_repo/axl_qa8/` — повний репозиторій (dev + engine + udgs_core + workers)
- `workspace/axl_final/axl_final/` — мінімальний “final” пакет (dist + lockfiles)
- `release/promoted_bundle_2026-02-26/` — promotion bundle (artifacts + gate checker)
- `release/promoted_artifacts_2026-02-26/` — маленький пакет артефактів (якщо використовується)
- `docs/` — IAS та дизайн-документи
- `cp/` — Control Plane manifest/locks (джерело істини для інтеграції)
- `source_snapshots/` — оригінальні ZIP як immutable input

## Як читати цю систему
1) **Control Plane**: `cp/AXL_CP_LOCK.json` + `cp/AXL_INTEGRATION_MAP.yaml`
2) **Evidence / реліз**: `release/promoted_bundle_2026-02-26/artifacts/`
3) **Код**: `workspace/full_repo/axl_qa8/`

