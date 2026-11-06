# inquiry-lab 開発ガイド

レビューで発見した問題のレポートは必ず日本語で記載する。

## 目的と現在の範囲

inquiry-labは、分析の進行を支援するCodexプラグインと、分析の問い・試行結果・統合レポートを
記録するワークスペースのテンプレートを展開するPython CLI。
分析にはPython、SQL、Notebookなど任意の実行手段を使える。
コマンドは `inquiry-lab init`、`inquiry-lab run new`、`inquiry-lab history record`、`inquiry-lab history render`、`inquiry-lab data inspect`、`inquiry-lab data values`、`inquiry-lab json inspect`。
利用方法と生成物の構成は [README.md](README.md) を参照する。

現行CLIはテンプレート展開、runの自動採番、試行・判断のJSON記録、作業履歴のMarkdown出力を扱う。分析の実行、結果の採用、完了状態、履歴sequenceの自動採番は管理しない。
`data` はCSV・TSV・Parquetの読み取り専用の基本確認を扱い、EDAの観測範囲・欠損定義・省略の契約を揃える。
`json inspect` はJSONの指定階層の直下を表示する。`--key` はドット区切りと繰り返し指定に対応し、ネストした値は型と件数だけを示す。
Notebook Workbenchにも同等CLIを残せるが、inquiry-labは実行時に依存しない。
`visualize` はPython APIとして、見た目を固定した分析用グラフの描画・保存を扱う。
`visualize.ml.classifier.plot_roc_curve` は2値分類のROC曲線とAUCを保存する。
`visualize.common.plot_histogram` は一般の数値列の分布を保存し、任意の `hue` 列で色分けする。
`plot_calibration_curve` は確率の較正曲線と、同じビンのサンプル数を重ねて保存する。
`skills/analyze/` が分析の進行・記録・最終レポートを扱う。
`skills/eda/` は1shotの探索を担い、表形式・イベントと反復観測・予測準備の参照を組み合わせ、一括で観察・報告する。
`skills/eda-loop/` は各回のEDAを独立したサブエージェントへ委任し、親が次の依頼・方向転換・停止を判断する。
新しい子コンテキストを作れる環境を前提とし、同一エージェントでの反復へは切り替えない。`eda` 単独の1shot利用は可能。
`skills/parameter-tuning/`、`skills/feature-design/`、`skills/error-analysis/` は、
設定の比較・選定、特徴量の選択・設計、モデルの誤差診断をそれぞれ扱う。
各Skillの基本手順と終了条件は `SKILL.md`、詳細は `references/`、レポート雛形は `assets/` に置く。
分析の入口はanalyzeに揃え、EDAを含む専門Skillの自動選択は無効にする。
`skills/inquiry-lab-api/` は実装時の公開関数の選択・入力条件・呼び出し方を扱い、自動選択を有効にする。
分析方法・終了判断は分析側に残し、APIの詳細と使用例はこのSkillの `references/` に集約する。
プラグインmanifestとリポジトリ用marketplaceで、このSkillを提供する。
段階別Skill、分析レポート自動生成、MCPサーバー、
独自モデルループは未実装。
過去の引き継ぎにある構想を、実装済みの機能や確定した仕様として扱わない。

## 実装の入口と開発方針

- `.codex-plugin/plugin.json`：リポジトリ直下をプラグインとし、`./skills/` を参照する。
- `.agents/skills/create-analysis-template/SKILL.md`：分析テンプレートを作成・改訂するリポジトリ開発用Skill。
  `skills/<テーマ名>/` に独立したSkillと雛形を追加し、analyzeの選択表を更新する。
- `.agents/plugins/marketplace.json`：`source.path: "./"` で同プラグインを公開する。
  プラグインの導入とPython CLIの導入を区別し、不要なMCPやhookを追加しない。
- `src/inquiry_lab/cli.py`：引数解析とCLIハンドラー。
  `argparse` の `set_defaults(func=...)` で登録し、`func(**args)` で呼び出す構成を保つ。
- `src/inquiry_lab/history.py`：履歴JSONの検査・保存と、短い `作業履歴.md`・各ループの詳細 `history/NNNNNN.md` の生成。
- `src/inquiry_lab/data.py`：単一ファイルの基本確認と値の全件集計。PyArrowでParquetを読み、CSV/TSVの文字列を保持する。
  `skills/eda/references/data-inspection.md` に結果の読み方と範囲を集約する。
  表示上限と走査範囲を区別し、未集計の欠損をゼロと扱わない。テストは `tests/test_data.py`。
- `src/inquiry_lab/json_inspection.py`：JSONの読み取り専用の階層参照と表示。
  キー名にドットを含むJSONと重複キーを拒否する。全体を読み込み、表示項目数と長い値を制限して省略を明示する。
  テストは `tests/test_json_inspection.py`。
- `src/inquiry_lab/workspace.py`：テンプレート読込と展開。
  テンプレートは `importlib.resources` から読み、インストール先や実行時のcwdに依存させない。
- `src/inquiry_lab/visualize/common.py`：MLに限らない汎用の描画・保存。
  `plot_histogram` はPolars DataFrameと対象列 `column`、任意の色分け列 `hue` を受け取る。
  対象列全体からNumPyの `auto` でビンを決め、群間で共有する。
  縦軸は件数で、`hue` のカテゴリは最大20群。テストは `tests/test_visualize_common.py`。
- `src/inquiry_lab/visualize/ml/classifier.py`：分類モデル向けのROC曲線・較正曲線の描画と保存。
  配色・レイアウトを固定し、Figure・Axesや任意の描画オプションを公開しない。
  Polars DataFrameと列名を受け取り、既定の列名は `label` と `score`。
  較正曲線は0〜1の10等分で、左軸に陽性率、右軸に同じビンの件数を示す。
  空のビンは曲線を切り、陽性率0にしない。入力確率は0〜1で両クラスを必須とする。
  テストは `tests/test_classifier.py`。描画依存は `visualize` extraに分離する。
- `src/inquiry_lab/templates/`：依頼、試行結果、統合レポートのMarkdownテンプレート。
  汎用雛形は英語、EDA用run雛形は日本語で、利用者が記入する言語は自由。
  EDAの正本は `skills/eda/assets/result.md` とし、変更時は同じ内容を `templates/eda-result.md` へコピーして一致を検証する。
- `tests/test_cli.py`：CLIの公開挙動、生成物、既存データの保護、展開失敗時の後始末を検証する。
- `skills/analyze/SKILL.md`：目的・判断基準の整理と、結果に応じた分析の進行判断。
  再開に必要な情報と作業履歴の共通構成を扱う。CLIでJSONを記録してMarkdownを生成できる。
  案件別の定量指標や未実装の段階別Skill・CLIを前提にしない。
- `skills/eda/SKILL.md`：データを説明するための暫定的な質問を立て、1shotで確認・評価・報告するEDAの入口。全体像の把握では広い視点を検討し、データの形・観測の構造・利用目的に応じて
  `references/` の見方を組み合わせる。利用予定のデータセット固有の列名や規則を共通の前提にしない。
  EDAの見方を追加する場合はここを改訂する。依頼・実行記録はanalyzeの共通手順を使い、結果からの追加探索は行わない。
  `references/request.md` が呼出元との依頼・返却の共通契約。直接実行でも出力はrunで、`output.md` の執筆・更新はしない。
  `assets/result.md` で観察の位置づけ・対象と方法・結果と読み取り・言えることと限界・再現情報の本文5章を作る。質問別の回答・次の候補は付録に残す。
- `skills/eda-loop/SKILL.md`：1shotのEDAを毎回新しい子へ委任する外側の探索ループ。必要な調査済み範囲と根拠を渡し、
  質問の見直し、次の依頼・継続・停止と知見の統合を担当する。観察手法と依頼契約は `eda` を使い、`assets/report.md` で `output.md` を作る。
  想定質問と回答はrunに残す。統合レポートは全体の総括と、各観点の知見・探索経緯・未確認の範囲を示し、詳細を各runへつなぐ。
- `skills/parameter-tuning/SKILL.md`：設定の探索・比較と最終評価の終了条件。
- `skills/feature-design/SKILL.md`：特徴量の削減・追加・変換を再学習で比較する手順と終了条件。
- `skills/error-analysis/SKILL.md`：計画した範囲の誤差を一括診断し、報告して終了する手順。
  各Skillはanalyzeの共通記録を使い、テーマ追加では独立したSkill・雛形とanalyzeの選択表を更新する。
- `pyproject.toml`：Python 3.12以降、Flitによる配布、pytestとRuffによる検証を定義する。
  基本の実行時依存はParquet対応のPyArrow。可視化用extraはmatplotlib・NumPy・Polars・scikit-learn。
  開発環境ではextraも導入する。依存を追加する場合は必要性と配布への影響を確認する。

## 変更時に守る契約

- 展開先は新規ディレクトリに限定する。空ディレクトリ、既存ファイル、シンボリックリンク
  （リンク先が存在しないものを含む）は拒否し、既存内容を変更しない。
  `run new` は既存の分析先の `runs/` に最大番号＋1のrunを追加する。数字だけの名前のファイル・リンクも採番対象とし、欠番は埋めない。
  数字の名前がなければ001から始める。mkdirで番号を確保し、並行実行の衝突は次の番号で再試行する。
  `runs/` のシンボリックリンクと、存在しない依頼文書を拒否する。依頼の相対パスは分析先基準で解決する。
- タイトルは前後の空白を除いて空でない1行とする。検証に失敗したらディレクトリを作成しない。
  展開中の書込失敗では、initは今回作ったワークスペース、run newは今回作ったrunだけを除去する。
- 成功時は作成先の絶対パスを標準出力へ返す。展開エラーは終了コード1、
  引数エラーは終了コード2で標準エラー出力へ報告する。
- 生成する文書は `requests/001-initial.md`、`runs/001/result.md`、`output.md`。
  成果物用に `runs/001/artifacts/` と `report/` を作る。
  `req-001` と `run-001` は文書を対応させるラベルであり、分析状態ではない。runの番号と履歴sequenceは別物として扱う。
  `init` と `run new` の `--template eda` はEDA用のresult.mdを展開する。依頼文書とoutput.mdは共通雛形を使う。
- Notebook、実行スクリプト、`analysis.yaml`、`run.yaml` は生成しない。
  未実装の検証markerや採用・完了状態を、テンプレートだけで利用者に要求しない。
- テンプレート変更では、問いから結果・根拠・統合レポートへの参照を保つ。
  入力の版、手順、パラメータ、環境、保存した出力を記録できることを確認する。
  Notebook Workbench由来の内容を変更・移植するときは、READMEの由来とライセンス表記も確認する。

## 検証

開発環境は `uv sync` で用意する。コードやテンプレートを変更した場合は、次を実行する。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

配布設定やテンプレート同梱を変更した場合は、ビルドしたwheelを別環境へ導入し、
リポジトリ外のcwdから `init` を実行して生成物を確認する。
文書だけの変更では、参照先・現行実装との整合性と `git diff --check` を確認する。
プラグイン定義を変更した場合は、JSON、Skillへの参照、marketplaceからの読込を確認する。

## 将来の拡張を検討するとき

引き継ぎでは、Codex上で分析の問い・手法選択・反復探索・解釈・報告を支援する方向性が
示されている。状況に応じた判断をSkill、機械的な整合性保証をCLIに置く案があるが、
具体的な責務分担は拡張時の要件と現行コードに照らして決める。
MCPの追加や独自モデルループを、初版の前提として先行実装しない。

Notebook Workbenchの分析Skill、analysis CLI、Notebook実行基盤はそれぞれ分けて移行要否を検討する。
現在のinquiry-labにNotebook Workbenchへの実行時依存はない。
移行元の未コミット変更を含む現物を確認し、コマンド名や過去の計画だけで一括移植しない。

<!-- knowledge-refinery:agents:start lang=jp -->
## Knowledge Refinery

このblockは、開発中に得た再利用可能な経験についてKnowledge Refineryの自動運用を許可する。
Refineryを操作するときは該当するPlugin Skillを読み、共通運用ルールと必要な参照先に従う。
handoffはこの自動運用に含めず、`$refinery-handoff`の明示呼び出しでだけ作成・再開・整理する。

- 設計判断、原因調査、手法比較、既知の制約などに過去の知識が役立つ場合は、`refinery-experience`で検索する。明示された検索依頼も対象とする。単純なtypo・書式変更など、過去の知識が判断に影響しない作業では省略し、同じ問いと根拠の検索結果は再利用する。
- 将来の選択、回避、検証、診断を変える試行・比較・不採用理由・有用な失敗は、`refinery-experience`で記録する。採用しなかった実装やuntracked evidenceも対象にし、定型的な完了logや新しい根拠のない反復は記録しない。
- 複数experienceから繰り返し使える原則が得られたら、`refinery-memory`でproject memoryへまとめる。shared memoryへの作成・昇格とmemoryの大幅な書き換えは、具体的な候補と根拠への明示承認を必要とする。
- projectの名前、概要、検索用tag、主要技術が変わった場合は、`refinery-project`でmetadataを更新する。導入・設定変更・状態確認・診断も同Skillを使う。
- 定期棚卸しや依頼されたvault監査・ナレッジ修復は、`refinery-maintenance`を使う。通常の開発作業や単発の保存確認を理由に全体保守を始めない。
- 利用者の明示要件と実行環境の権限・必須承認を守る。検索・診断・提案のみの依頼では、この自動運用の許可があってもvaultへ書き込まない。knowledgeの削除にも具体的な対象への明示承認を必要とする。
- disabled・未準備・vault不一致ならrefinery操作だけを止め、依存しない依頼作業は続ける。設定修復は`refinery-project`で扱い、検索や記録の依頼だけを理由に再有効化しない。
- 許可済みの記録は保存結果の確認まで完了する。記録価値はagent自身で判断し、毎回の確認質問にしない。同じ候補・影響への既存承認は再利用し、承認待ちでも独立した作業を続ける。
<!-- knowledge-refinery:agents:end -->
