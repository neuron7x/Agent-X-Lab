export type Lang = 'ua' | 'en';

export const translations = {
  // TopBar
  demo: { ua: 'ДЕМО', en: 'DEMO' },
  demoMode: { ua: 'ДЕМО РЕЖИМ', en: 'DEMO MODE' },

  // Home
  vrStatus: { ua: 'СТАТУС ВР', en: 'VR STATUS' },
  passRate: { ua: 'ВІДСОТОК УСПІХУ', en: 'PASS RATE' },
  blockers: { ua: 'БЛОКЕРИ', en: 'BLOCKERS' },
  gates: { ua: 'ШЛЮЗИ', en: 'GATES' },
  viewPipeline: { ua: 'ПЕРЕВІРИТИ СИСТЕМУ →', en: 'VIEW PIPELINE →' },
  assumedSingleRun: { ua: '⚠ ДЕТЕРМІНІЗМ НЕ ПІДТВЕРДЖЕНО', en: '⚠ DETERMINISM NOT VERIFIED' },
  clickToArsenal: { ua: 'ВІДКРИТИ АРСЕНАЛ', en: 'OPEN ARSENAL' },

  // Tabs
  tabStatus: { ua: 'СТАН СИСТЕМИ', en: 'STATUS' },
  tabPipeline: { ua: 'ПЕРЕВІРКА', en: 'PIPELINE' },
  tabEvidence: { ua: 'АРТЕФАКТИ', en: 'EVIDENCE' },
  tabSettings: { ua: 'КОНФІГУРАЦІЯ', en: 'SETTINGS' },
  tabArsenal: { ua: 'ПРОМПТ', en: 'PROMPT' },
  tabForge: { ua: 'КУЗНЯ', en: 'FORGE' },

  // Arsenal
  arsenalTitle: { ua: 'БІБЛІОТЕКА АГЕНТІВ', en: 'AGENT LIBRARY' },
  arsenalEmpty: { ua: 'ОБЕРІТЬ ПРОТОКОЛ', en: 'SELECT PROTOCOL' },
  arsenalCopy: { ua: 'СКОПІЮВАТИ', en: 'COPY' },
  arsenalCopied: { ua: 'СКОПІЙОВАНО', en: 'COPIED' },
  arsenalNoData: { ua: 'ПРОТОКОЛІВ НЕ ЗНАЙДЕНО', en: 'NO PROTOCOLS FOUND' },
  arsenalBack: { ua: '← НАЗАД', en: '← BACK' },
  arsenalProtocols: { ua: 'ПРОТОКОЛІВ', en: 'PROTOCOLS' },
  arsenalSelectPlat: { ua: 'ОБЕРІТЬ ПЛАТФОРМУ', en: 'SELECT PLATFORM' },

  // Pipeline
  araLoop: { ua: 'АРА-ЦИКЛ', en: 'ARA-LOOP' },
  phase: { ua: 'ФАЗА', en: 'PHASE' },
  gate: { ua: 'ШЛЮЗ', en: 'GATE' },
  status: { ua: 'СТАТУС', en: 'STATUS' },
  tool: { ua: 'ІНСТРУМЕНТ', en: 'TOOL' },
  time: { ua: 'ЧАС', en: 'TIME' },

  // Pipeline phases
  phaseBaseline: { ua: 'БАЗОВИЙ', en: 'BASELINE' },
  phaseSecurity: { ua: 'БЕЗПЕКА', en: 'SECURITY' },
  phaseRelease: { ua: 'РЕЛІЗ', en: 'RELEASE' },
  phaseOps: { ua: 'OPS', en: 'OPS' },
  phaseCanary: { ua: 'CANARY', en: 'CANARY' },
  phaseLaunch: { ua: 'ЗАПУСК', en: 'LAUNCH' },

  // ARA-Loop nodes
  nodePreLogic: { ua: 'МЕТА-ЛОГІКА', en: 'PRE-LOGIC' },
  nodeExecutor: { ua: 'ВИКОНАВЕЦЬ', en: 'EXECUTOR' },
  nodeAraLoop: { ua: 'ПЕРЕВІРКА ВИКОНАННЯ', en: 'RUN VALIDATION' },
  nodeAuditor: { ua: 'АУДИТОР', en: 'AUDITOR' },
  labelThinking: { ua: 'МИСЛЕННЯ', en: 'THINKING' },
  labelCodex: { ua: 'КОДЕКС', en: 'CODEX' },
  labelCiLogs: { ua: 'ТРАСУВАННЯ ВИКОНАННЯ', en: 'EXECUTION TRACE' },
  labelPostAudit: { ua: 'ПОСТ-АУДИТ', en: 'POST-AUDIT' },

  // Evidence
  evidence: { ua: 'ДОКАЗИ', en: 'EVIDENCE' },
  pullRequests: { ua: 'PULL-ЗАПИТИ', en: 'PULL REQUESTS' },
  noData: { ua: 'НЕМАЄ ДАНИХ', en: 'NO DATA' },

  // Status labels
  statusPass: { ua: 'УСПІХ', en: 'PASS' },
  statusFail: { ua: 'ЗБІЙ', en: 'FAIL' },
  statusAssumed: { ua: 'ПРИПУЩЕНО', en: 'ASSUMED' },
  statusRunning: { ua: 'ВИКОНУЄТЬСЯ', en: 'RUNNING' },
  statusPending: { ua: 'ОЧІКУВАННЯ', en: 'PENDING' },
  statusBlocked: { ua: 'ЗАБЛОКОВАНО', en: 'BLOCKED' },

  // Settings
  settings: { ua: 'НАЛАШТУВАННЯ', en: 'SETTINGS' },
  language: { ua: 'МОВА', en: 'LANGUAGE' },
  github: { ua: 'GITHUB', en: 'GITHUB' },
  token: { ua: 'ТОКЕН', en: 'TOKEN' },
  owner: { ua: 'ВЛАСНИК', en: 'OWNER' },
  repository: { ua: 'РЕПОЗИТОРІЙ', en: 'REPOSITORY' },
  pollInterval: { ua: 'ІНТЕРВАЛ ОПИТУВАННЯ', en: 'POLL INTERVAL' },
  save: { ua: 'ЗБЕРЕГТИ', en: 'SAVE' },
  test: { ua: 'ТЕСТ', en: 'TEST' },
  testing: { ua: 'ТЕСТУВАННЯ...', en: 'TESTING...' },
  testOk: { ua: '● ОК', en: '● OK' },
  testFailed: { ua: '✕ ЗБІЙ', en: '✕ FAILED' },
  disconnect: { ua: "ВІД'ЄДНАТИ", en: 'DISCONNECT' },
  exitDemo: { ua: 'ВИЙТИ З ДЕМО', en: 'EXIT DEMO' },
  viewingMockData: { ua: 'Перегляд демо-даних.', en: 'Viewing mock data.' },
  lastVerified: { ua: 'Останній:', en: 'Last:' },

  // Connect
  connectRepo: { ua: 'ПІДКЛЮЧИТИ РЕПОЗИТОРІЙ', en: 'CONNECT REPOSITORY' },
  connectToAgentXLab: { ua: "Підключитися до Agent-X-Lab", en: 'Connect to Agent-X-Lab' },
  connect: { ua: "ПІДКЛЮЧИТИ", en: 'CONNECT' },
  previewDemo: { ua: 'ПЕРЕГЛЯНУТИ ДЕМО', en: 'PREVIEW DEMO' },

  // Cycle phases (BottomBar)
  cycleObserve: { ua: 'СПОСТЕРІГАТИ', en: 'OBSERVE' },
  cycleSpecify: { ua: 'СПЕЦИФІКУВАТИ', en: 'SPECIFY' },
  cycleExecute: { ua: 'ВИКОНАТИ', en: 'EXECUTE' },
  cycleProve: { ua: 'ДОВЕСТИ', en: 'PROVE' },

  // Connection statuses
  connLive: { ua: 'ПІДКЛЮЧЕНО', en: 'CONNECTED' },
  connPolling: { ua: 'ОПИТУВАННЯ', en: 'POLLING' },
  connOffline: { ua: 'ВІДКЛЮЧЕНО', en: 'DISCONNECTED' },
  connError: { ua: 'ПОМИЛКА', en: 'ERROR' },
  connRateLimited: { ua: 'ЛІМІТ', en: 'RATE LIMITED' },

  // SystemState panel
  systemState: { ua: 'СТАН СИСТЕМИ', en: 'SYSTEM STATE' },
  workId: { ua: 'ID РОБОТИ', en: 'WORK ID' },
  utc: { ua: 'UTC', en: 'UTC' },
  determinism: { ua: 'ДЕТЕРМІНІЗМ', en: 'DETERMINISM' },
  assumed: { ua: 'ПРИПУЩЕНО', en: 'ASSUMED' },
  metrics: { ua: 'МЕТРИКИ', en: 'METRICS' },
  baselinePass: { ua: 'базовий_прохід', en: 'baseline_pass' },
  catalogOk: { ua: 'каталог_ок', en: 'catalog_ok' },
  evidenceEntries: { ua: 'записи_доказів', en: 'evidence_entries' },
  noLogAvailable: { ua: 'Лог відсутній', en: 'No log available' },

  // ErrorBoundary
  error: { ua: 'ПОМИЛКА', en: 'ERROR' },
  reload: { ua: 'ПЕРЕЗАВАНТАЖИТИ', en: 'RELOAD' },

  // ErrorBanner
  rateLimitedResets: { ua: 'ЛІМІТ — скидання о', en: 'RATE LIMITED — resets at' },
  errorDash: { ua: 'ПОМИЛКА —', en: 'ERROR —' },
  failDash: { ua: 'ЗБІЙ —', en: 'FAIL —' },
  statusColon: { ua: 'СТАТУС:', en: 'STATUS:' },
  blockersColon: { ua: 'блокери:', en: 'blockers:' },

  // SettingsPanel (legacy)
  githubIntegration: { ua: 'ІНТЕГРАЦІЯ GITHUB', en: 'GITHUB INTEGRATION' },
  personalAccessToken: { ua: 'ТОКЕН ДОСТУПУ', en: 'PERSONAL ACCESS TOKEN' },
  connectionOk: { ua: '● З\'ЄДНАННЯ ОК', en: '● CONNECTION OK' },
  connectionFailed: { ua: '✕ З\'ЄДНАННЯ ЗБІЙ', en: '✕ CONNECTION FAILED' },


  // App shell
  skipToMain: { ua: 'Перейти до головного контенту', en: 'Skip to main content' },
  mainNavigation: { ua: 'Головна навігація', en: 'Main navigation' },
  connectionLabel: { ua: "З'єднання", en: 'Connection' },

  // BottomBar
  iter: { ua: 'ітер', en: 'iter' },
} as const;

export type TranslationKey = keyof typeof translations;

export function t(key: TranslationKey, lang: Lang): string {
  return translations[key][lang];
}
