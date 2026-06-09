# LangGraph オーケストレータ エージェント

ローカル Ollama (gpt-oss) 上で動く、**オーケストレータ + プランナー / エグゼキューター(並列) / エヴァリュエーター** 構成の AI エージェント。
フロントのチャット画面に「今どのエージェントが動いていて、何を考えているか」をリアルタイム表示する。

## アーキテクチャ

```
ユーザー
  │  (React + SSE)
  ▼
FastAPI  /chat/stream
  │
  ▼  LangGraph 親グラフ(オーケストレータ)
START → recall_memory ─→ planner ─┬─[Send 並列]→ executor(t1)
                                   ├──────────────→ executor(t2)   ← 並列実行
                                   └──────────────→ executor(t3)
                                          │ (fan-in)
                                          ▼
                                      evaluator ──┬─ 合格/上限 → finalize → END
                                                  └─ 不合格      → planner(再計画)
        │
        ▼ 背景で記憶化 (LangMem)
   PostgreSQL + pgvector + nomic-embed-text(768次元)
```

### コンテキスト分離(重要)
各エージェント(Planner / Executor / Evaluator)は**独立してコンパイルされた StateGraph**で、
親グラフと State キーを一切共有しない。オーケストレータはブリッジノードから
**明示的な指示文だけ**を渡し、戻り値の必要なキーだけを読み戻す。
→ 会話履歴は引き継がれず、各エージェントは毎回まっさらなコンテキストで起動する。

### 並列実行
Planner が出力したタスクを、オーケストレータが **Send API** で並列ファンアウトする。
複数 Executor の結果は `Annotated[list, operator.add]` のリデューサで安全にマージ。

### リアルタイム表示
各ノードが `get_stream_writer()` で `status / thinking / plan / task_update / token / evaluation` を発行 →
FastAPI が `astream(stream_mode=["custom","updates"], subgraphs=True)` を **SSE** に変換 →
React の `useAgentStream` フックがチャットと「稼働パネル」を同時更新。

gpt-oss の思考(reasoning)は `reasoning="medium"` で `reasoning_content` に分離され、思考ログに流れる。

## 必要環境
- Ollama 起動済み + モデル取得済み: `ollama pull gpt-oss:20b` / `ollama pull nomic-embed-text`
- Python 3.11 + [uv](https://docs.astral.sh/uv/)
- Node.js 20.19+ / 22.12+
- Docker / Docker Compose(長期記憶の PostgreSQL 用)

## 起動

### データベース(PostgreSQL + pgvector)
長期記憶(LangMem)を永続化する。最初に起動しておく。
```bash
docker compose up -d           # localhost:5432 で起動(初回はテーブルを自動作成)
```
接続先は `backend/.env` の `DATABASE_URL`(既定 `postgresql://agent:agent@localhost:5432/agent`)。

### バックエンド
```bash
cd backend
cp .env.example .env          # 必要に応じて編集
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### フロントエンド
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

## テスト
```bash
docker compose up -d           # 記憶テストは PostgreSQL を使う
cd backend && uv run pytest    # ※ 実 Ollama / PostgreSQL を使う統合テストを含む
```

## 設定 (`backend/.env`)
| 変数 | 既定 | 説明 |
|---|---|---|
| `CHAT_MODEL` | `gpt-oss:20b` | 言語モデル |
| `EMBED_MODEL` | `nomic-embed-text` | 埋め込みモデル(768次元固定) |
| `REASONING_EFFORT` | `medium` | gpt-oss の思考レベル low/medium/high |
| `NUM_CTX` | `8192` | コンテキスト長(明示必須) |
| `MAX_ITERATIONS` | `2` | 評価→再計画ループの上限 |
| `DATABASE_URL` | `postgresql://agent:agent@localhost:5432/agent` | 長期記憶を永続化する PostgreSQL(pgvector) |

## 既知の制約
- 記憶は `AsyncPostgresStore`(PostgreSQL + pgvector)に永続化。プロセス再起動後も残る。DB が未起動だと記憶検索/保存はスキップされる(チャット自体は動作)。
- 単一 Ollama インスタンスへの並列 Executor は、`OLLAMA_NUM_PARALLEL` 次第でモデルサーバ側で直列化されうる。
- gpt-oss の structured output は不安定なため、Planner/Evaluator は寛容な JSON 抽出 + フォールバックで対処。
