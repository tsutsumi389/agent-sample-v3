// ノード / エージェントの表示名(稼働パネルと思考ログで共用)
export const NODE_LABELS: Record<string, string> = {
  orchestrator: "オーケストレータ",
  memory: "記憶想起",
  recall_memory: "記憶想起",
  planner: "プランナー",
  executor: "エグゼキューター",
  evaluator: "エヴァリュエーター",
  finalize: "最終統合",
};

// 処理フローの可視化用ステップ定義(稼働パネルのパイプライン表示)
// keys: その工程に対応するノード名(バックエンドの status イベントの node)
export interface PipelineStep {
  keys: string[];
  label: string;
  icon: string;
}

export const PIPELINE_STEPS: PipelineStep[] = [
  { keys: ["memory", "recall_memory"], label: "記憶", icon: "🧠" },
  { keys: ["planner"], label: "計画", icon: "📋" },
  { keys: ["executor"], label: "実行", icon: "⚡" },
  { keys: ["evaluator"], label: "評価", icon: "🔍" },
  { keys: ["finalize"], label: "回答", icon: "💬" },
];
