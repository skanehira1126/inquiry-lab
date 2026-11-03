# inquiry-lab

分析の進行を支援するCodexプラグインと、分析ワークスペースを作るPython CLIです。
プラグインには、目的と判断基準を整理し、試行結果に応じて次の作業を選ぶ
`analysis-framework` Skillを同梱しています。

CLIは `init` による文章テンプレートの展開を提供します。
Pythonスクリプト、SQL、Notebookなど任意の方法で分析し、問いと根拠、現在の結論を
Markdownでつなげて残せます。CLIは分析の実行、結果の検証・採用、完了状態、IDの自動採番を
管理しません。段階別Skill、構造化データ管理、レポート自動生成、MCPサーバー、
独自モデルループは未実装です。

## プラグインの導入

チェックアウトしたリポジトリのルートで、ローカルのmarketplaceを登録してインストールします。

```bash
codex plugin marketplace add .
codex plugin add inquiry-lab@inquiry-lab
```

導入後は新しいタスクまたはセッションで利用します。
プラグインとPython CLIは別々に導入します。プラグインはスキルを提供し、
Pythonパッケージのインストールは行いません。
現在のframeworkスキルは、特定のCLIや保存方式を利用の前提にしていません。

リポジトリ全体が一つのプラグインです。Notebook Workbenchと同じ、Codexで対応している
`.codex-plugin/plugin.json` 形式を使用しています。
配置仕様は[公式のプラグイン作成ガイド](https://developers.openai.com/plugins/build/plugins)を参照してください。

```text
inquiry-lab/
├── .codex-plugin/plugin.json       # プラグインの情報とSkillの参照
├── .agents/plugins/marketplace.json # リポジトリ直下のプラグインを公開する一覧
├── skills/
│   └── analysis-framework/
│       ├── SKILL.md
│       └── agents/openai.yaml
├── src/inquiry_lab/                # Python CLIと文章テンプレート
├── tests/
└── pyproject.toml
```

marketplaceの `source.path` は `./` で、このリポジトリのルートを参照します。
新しいSkillは `skills/` 配下へ追加します。

## 分析frameworkの試作Skill

[analysis-framework](skills/analysis-framework/SKILL.md) は、分析目的を受け取り、対話で問いと判断基準を詰め、
試行と評価を繰り返し、総評をまとめるSkillです。目的と入力に合うテーマ別スキルが利用できれば参照し、
該当するスキルがなければ最初の試行に必要な情報から整理します。

プラグイン導入後は、たとえば「`$inquiry-lab:analysis-framework` を使って、
分析の目的と判断基準を整理し、必要な試行を進めて」と依頼します。
計画だけの依頼にも対応します。導入前に試す場合は、このリポジトリの
`skills/analysis-framework/SKILL.md` を指定できます。
`uv tool install .` によるCLI導入ではプラグインは登録されません。

このSkillは分析の進行判断と、再開に必要な情報を残す方針を扱います。
具体的な保存形式や記録の操作手順は、今後のデータ管理の設計で決めます。

## CLIの導入と実行

Python 3.12以降が必要です。以下はuvを使う例です。
リポジトリのルートから、まだ存在しないディレクトリを指定して実行します。

```bash
uv run inquiry-lab init analyses/sales-change --title "売上変化の分析"
```

CLIをインストールして利用する場合は、リポジトリのルートで次を実行します。

```bash
uv tool install .
```

インストール後は、任意の作業ディレクトリから
`inquiry-lab init <directory> --title "分析タイトル"` で利用できます。
実行時の外部Python依存はなく、Notebook Workbenchのインストールも不要です。

## 生成されるワークスペース

```text
analyses/sales-change/
├── requests/
│   └── 001-initial.md    # 問い、対象範囲、入力、制約、受入基準
├── runs/
│   └── 001/
│       ├── result.md    # 手法、結果、根拠、限界
│       └── artifacts/   # この試行の成果物
├── report/             # 読者に渡す図表など
└── output.md           # 現時点の答えと統合レポート
```

テンプレート本文は英語ですが、記入する言語は自由です。
Notebook、Pythonスクリプト、`analysis.yaml`、`run.yaml` は生成しません。

## 分析の進め方

1. `requests/001-initial.md` に問い、対象範囲、利用可能な入力、制約、受入基準を記入します。
2. 必要な方法で分析し、`runs/001/result.md` に手法、結果、データ品質の確認、限界を記録します。
   使用した入力の版や取得日、コード・コマンド・クエリ、パラメータ、実行環境、保存した出力への
   参照を残し、結果を追跡できるようにします。
3. `output.md` に問いへの現在の答えをまとめ、根拠となる試行結果へリンクします。
   読者が参照する図表は `report/` に置き、個々の試行の詳細な成果物と区別できます。

コードや実行結果の配置は強制しません。`runs/001/artifacts/` は試行の成果物置き場として使えます。
結論を更新するときは、試行結果に既存の結論への影響を記録し、`output.md` の答え・限界・更新履歴も
合わせて更新します。

追加の依頼や試行は手作業で作成します。たとえば `runs/002/result.md` を追加する場合は、
文書内のRunラベルを `run-002` にし、対応する依頼への参照も確認してください。
`req-001` と `run-001` は文書を対応させるラベルであり、CLIが管理する状態ではありません。

## CLIの動作

展開先は存在しないディレクトリを指定してください。親ディレクトリは必要に応じて作成します。
空のディレクトリ、既存ファイル、シンボリックリンクを含め、既存の展開先は変更せずに拒否します。
タイトルは前後の空白を除いて空でない1行を指定します。成功時は作成先の絶対パスを標準出力へ返します。
展開エラーは終了コード1、引数エラーは終了コード2で標準エラー出力へ報告します。
展開中の書込失敗では、作成途中のワークスペースを除去します。

## 開発

このリポジトリで「モデル評価用の分析テンプレートを作りたい」などと依頼すると、開発用の
[create-analysis-template](.agents/skills/create-analysis-template/SKILL.md) が自動選択の対象になります。
作成先は `skills/<テーマ名>/` です。目的、評価基準と判断者、制限・禁止事項を整理し、
繰り返し使う計算があれば、そのテーマの `scripts/` に同梱します。

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

CLIは `src/inquiry_lab/cli.py`、展開処理は `src/inquiry_lab/workspace.py` にあります。
文章テンプレートは `src/inquiry_lab/templates/` に置き、配布パッケージに同梱しています。
開発方針、変更時に守る契約、配布物の確認方法は [AGENTS.md](AGENTS.md) を参照してください。

## テンプレートとSkillの由来

文章テンプレートはNotebook Workbenchの`analysis_templates`を基にしています
（commit `1b2fb66572a1e55fd504b6161a1cf156d09c70e9`、Apache-2.0）。
元の問い・結果・統合レポートの構成を保ち、Notebook固有の参照、実行状態への依存、
未実装の必須項目検査を示すmarkerを除去しています。

`analysis-framework` はNotebook Workbenchの分析Skillと反復分析の設計を基にしています
（Apache-2.0、ベースcommit `a2ad2658e29034acfd15e51b8ee81df00f6a7cf7`）。
2026-11-03時点のローカル作業ツリーにある、未コミットの `SKILL.md` の変更と
未追跡の `references/iterative-analysis.md` も参照しました。
Notebook固有の実行・状態管理を切り離し、問いの整理、判断基準、結果に応じた進行を扱う形へ
変更しています。具体的な保存形式や記録の操作手順は含めていません。

対話の進め方は、Matt Pocockの
[grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md)
の意思決定の依存関係、推奨案を伴う質問、調査可能な事実と利用者の判断の分離を参考にしています。
全分岐の解決を開始条件にせず、分析を始めるために必要な合意を作り、結果に応じて問い直します。
