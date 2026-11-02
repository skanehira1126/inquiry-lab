# inquiry-lab

分析の問い、試行結果、統合レポートのテンプレートを展開するCLIです。
Pythonスクリプト、SQL、Notebookなど、分析の実行手段は自由に選べます。

## 使い方

Python 3.12以降を使用します。リポジトリ内では次のコマンドで実行できます。

```bash
uv run inquiry-lab init analyses/sales-change --title "売上変化の分析"
```

CLIだけをインストールする場合は、リポジトリのルートで`uv tool install .`を実行します。
以降は`inquiry-lab init <directory> --title "分析タイトル"`で利用できます。

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

`requests/001-initial.md`に問いを記入し、必要な方法で分析します。
使用したコード・入力・パラメータ・実行環境・出力への参照を`runs/001/result.md`に記録し、
現在の答えを`output.md`へまとめます。テンプレート本文は英語ですが、記入する言語は自由です。
コードや実行結果の配置は強制しません。NotebookやPythonスクリプトは自動生成しません。

展開先は存在しないディレクトリを指定してください。親ディレクトリは必要に応じて作成します。
空のディレクトリ、既存ファイル、シンボリックリンクを含め、既存の展開先は変更せずに拒否します。
タイトルは空でない1行を指定します。成功時は作成先の絶対パスを標準出力へ返します。
展開エラーは終了コード1、引数エラーは終了コード2で標準エラー出力へ報告します。

初版はテンプレート展開だけを提供します。実行、検証・採用、完了状態、IDの自動採番は管理しません。
`req-001`と`run-001`は初期文書を対応させるラベルです。追加の試行や依頼を手作業で作成する場合は、
番号と参照先も合わせて更新してください。`analysis.yaml`と`run.yaml`は生成しません。

## 開発

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

CLIはargparseの`set_defaults(func=...)`でハンドラーを登録し、`func(**args)`で呼び出します。
実行時の外部Python依存はありません。文章テンプレートは配布パッケージに同梱しています。

## テンプレートの由来

文章テンプレートはNotebook Workbenchの`analysis_templates`を基にしています
（commit `1b2fb66572a1e55fd504b6161a1cf156d09c70e9`、Apache-2.0）。
元の問い・結果・統合レポートの構成を保ち、Notebook固有の参照、実行状態への依存、
未実装の必須項目検査を示すmarkerを除去しています。
