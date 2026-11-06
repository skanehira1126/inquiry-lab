# inquiry-lab

分析の進行を支援するCodexプラグインと、分析ワークスペースを作るPython CLIです。
プラグインには、目的と判断基準を整理し、試行結果に応じて次の作業を選ぶ
`analyze`、一括で観察する `eda`、探索を繰り返す `eda-loop`、`parameter-tuning`、`feature-design`、`error-analysis` を同梱しています。
コードの実装には `inquiry-lab-api` が公開関数の選択・入力条件・呼び出し方を案内します。
EDAは表形式・イベントと反復観測・予測準備の参照を組み合わせて使います。
テンプレート集はモデルのパラメータチューニング、特徴量選択・エンジニアリング、誤差分析を提供しています。

CLIは `init` で分析先と最初のrun、`run new` で追加runのテンプレートを展開し、
`history` で作業履歴の記録とMarkdown出力を行います。
`state update / show / context` は分析全体の現在状態を保存・表示し、SessionStart hookへ復元用の文脈を渡します。
`data inspect / values` はCSV・TSV・Parquetの基本確認を行い、EDAで読む範囲・欠損・表示の省略を揃えます。
`json inspect` はJSONの指定階層の直下を表示し、設定や分析結果を確認します。
Python APIの `visualize` は、固定した見た目で分析用の図を描画・保存します。
Pythonスクリプト、SQL、Notebookなど任意の方法で分析し、問いと根拠、現在の結論を
Markdownでつなげて残せます。CLIはエージェントが判断した状態を保存しますが、分析の実行、結果の検証・採用、完了を
自動判定しません。段階別Skill、分析レポートの自動生成、MCPサーバー、
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
現在のanalyzeスキルは、特定のCLIや保存方式を利用の前提にしていません。

リポジトリ全体が一つのプラグインです。Notebook Workbenchと同じ、Codexで対応している
`.codex-plugin/plugin.json` 形式を使用しています。
配置仕様は[公式のプラグイン作成ガイド](https://developers.openai.com/plugins/build/plugins)を参照してください。

```text
inquiry-lab/
├── .codex-plugin/plugin.json       # プラグインの情報とSkillの参照
├── .agents/plugins/marketplace.json # リポジトリ直下のプラグインを公開する一覧
├── skills/
│   ├── analyze/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── inquiry-lab-api/
│   │   ├── SKILL.md                # 実装時の公開関数の選択と利用条件
│   │   ├── agents/openai.yaml
│   │   └── references/            # 用途別のAPI契約と使用例
│   ├── eda/
│   │   ├── SKILL.md                # データと目的に応じて見方を組み合わせる
│   │   ├── agents/openai.yaml
│   │   ├── assets/result.md       # 単発EDAの本文と作業記録
│   │   └── references/
│   │       ├── tabular.md
│   │       ├── data-inspection.md # CLIによる基本確認と結果の読み方
│   │       ├── events.md
│   │       ├── prediction.md
│   │       └── request.md         # 呼出元との依頼・返却の契約
│   ├── eda-loop/
│   │   ├── SKILL.md                # EDAを繰り返し、次の依頼・継続・停止を判断する
│   │   ├── agents/openai.yaml
│   │   └── assets/report.md
│   ├── parameter-tuning/
│   │   ├── SKILL.md                # 設定の比較・選定
│   │   ├── agents/openai.yaml     # 自動選択を無効化
│   │   ├── references/            # 分割・指標・不確実性の評価
│   │   └── assets/report.md
│   ├── feature-design/
│   │   ├── SKILL.md                # 特徴量の削減・追加・変換
│   │   ├── agents/openai.yaml
│   │   ├── references/            # 比較設計・重要度の読み方
│   │   └── assets/report.md
│   └── error-analysis/
│       ├── SKILL.md                # 計画した誤差診断を一括実施
│       ├── agents/openai.yaml
│       ├── references/diagnostics.md
│       └── assets/report.md
├── src/inquiry_lab/                # Python CLI・可視化API・文章テンプレート
├── tests/
└── pyproject.toml
```

marketplaceの `source.path` は `./` で、このリポジトリのルートを参照します。
新しい分析テーマは `skills/<テーマ名>/` に独立したSkillと雛形を置き、analyzeの選択表へ追加します。
EDAで使う見方の追加は、`eda` の参照文書と選択条件を改訂します。

## 分析の入口：analyze

[analyze](skills/analyze/SKILL.md) は、分析目的を受け取り、対話で問いと判断基準を詰め、
試行と評価を繰り返し、総評をまとめるSkillです。一括のEDAには `eda`、反復探索には `eda-loop` を使い、モデルの比較・診断には
`parameter-tuning`、`feature-design`、`error-analysis` から目的と入力に合うSkillを選びます。該当するものがなければ最初の試行に必要な情報から整理します。

プラグイン導入後は、たとえば「`$inquiry-lab:analyze` を使って、
分析の目的と判断基準を整理し、必要な試行を進めて」と依頼します。
計画だけの依頼にも対応します。導入前に試す場合は、このリポジトリの
`skills/analyze/SKILL.md` を指定できます。
`uv tool install .` によるCLI導入ではプラグインは登録されません。

分析の入口は `analyze` です。各専門Skillの `allow_implicit_invocation: false` により、
`eda`・`eda-loop` を含めて自動選択を無効にしています。
analyzeの選択表から必要なSkillを読む構成で、利用者が個別に呼ぶ必要はありません。
明示的なSkill指定は引き続き利用できます。

Python APIの利用は [inquiry-lab-api](skills/inquiry-lab-api/SKILL.md) が担当し、コードの実装や
利用できる関数の確認で自動選択されます。分析の目的・方法・終了条件は分析側のSkillが扱い、
API Skillはその方法に使える関数と入力条件を確認します。各分析Skillからも実装時に参照します。

成果物は、判断する人が読む分析レポートと、試行・根拠・次の判断を作業順に辿るhistoryです。
historyは全テーマで共通とし、最終レポートは各Skillの雛形を使います。
大章はテーマ内で固定し、小見出しと段落を案件の判断に合わせて組み立てます。
MLflowやローカルに保存した結果は原本を参照し、判断に必要な値・表・図を本文にも載せます。
[共通フォーマット](skills/analyze/references/deliverables.md)を参照してください。
試行と判断の正本はJSONで記録できます。分析レポートの自動生成は今後の設計対象です。
最終レポートは、知見を伝えるとともに、結論から主要な判断・証拠・評価の前提まで辿れるようにします。
[チューニング用の雛形](skills/parameter-tuning/assets/report.md)で、結論をレビューする読み順を確認できます。

チューニングのレポートは「結論」「モデルの性能と診断」「調整方針と検証」「適用範囲と残る課題」
「参考」の5章を使います。調整ごとに、観測・意図・比較結果・判断をつなぎ、小見出しは案件に合わせます。
共通Skillは分析先の準備、試行と判断の記録、再開、総評を担当します。
[記録手順](skills/analyze/references/history-recording.md)にJSONの項目とCLI操作をまとめています。
[チューニング・EDAの履歴記入例](docs/examples/analysis-deliverables.md)では、各試行の記録内容を確認できます。

テーマ固有のデータ利用制約と停止条件はテンプレート側で定め、analyzeはその条件を確認して進行・終了を判断します。
チューニング・特徴量設計のテンプレートでは、最初に改善に使えるデータの範囲と最終評価用ホールドアウトの分割ルールを決めます。
開発データ内では目的に応じて分割を変え、候補を支持する根拠が得られたときだけ最終評価へ進みます。
候補を見送るときはホールドアウトを未使用のまま報告します。最終評価へ進んだ場合は、
評価した時点で改善を終了し、事前に決めた指標と限界を総評にまとめます。

モデルのパラメータを調整する案件では、analyzeが[チューニングSkill](skills/parameter-tuning/SKILL.md)を読みます。
分類・回帰・ランキングの標準指標と独自指標から目的に合う基準を選び、候補間の比較と採用判断を進めます。

特徴量の削減・追加・変換を扱う案件では、[特徴量設計Skill](skills/feature-design/SKILL.md)を使います。
基本は同じ検証条件での予測性能と特徴量数で判断し、追加・変換と削減を結果に応じて繰り返します。
コストなどは具体的な制約がある場合に加え、bootstrapやnested CVは必須にしません。
基本の診断はbootstrapなしのSHAPとfeature importanceで、分割gainを提供する木モデルでは累積gain・平均gain・利用回数を確認します。
重要度や誤差から変更候補を作り、再学習した比較で効果を確かめます。
[レポート雛形](skills/feature-design/assets/report.md)では、変更の意図と検証結果、採否の根拠を対応づけます。

予測が外れる対象・条件を調べる案件では、[誤差分析Skill](skills/error-analysis/SKILL.md)を使います。
分類・回帰・ランキングの予測と正解について、全体・比較するセグメント・計測する指標や図を先に決め、一括で診断・報告して完了します。
事例確認、SHAPやbootstrapも必要なものを事前に選びます。結果から生じた新しい疑問や改善案は次の分析候補に残します。
診断だけならホールドアウトは未使用に保ち、改善の実行・採用比較は対応する分析へ渡します。
[レポート雛形](skills/error-analysis/assets/report.md)は、検証項目の報告、傾向が見つかった項目、それぞれの検証方法と内容、適用範囲と次の検証、参考の順にまとめます。
全項目の結果を先に示し、特徴的な傾向から方法と根拠を辿れるようにします。

データの性質や利用上の前提を調べる案件では、[eda](skills/eda/SKILL.md) Skillで範囲を定めた1shotの探索を行います。
「`$inquiry-lab:analyze` を使って、このデータを一括で概観し、知見と次の問いを返して」と依頼できます。
全体像の把握では、イベントの性質、分布と構成、時間傾向、条件による違い、関係、観測上の制約を広く検討します。
構造と実例から説明のための暫定的な質問を立て、表形式・イベント・予測準備の参照を組み合わせて確認・評価します。
具体的な質問や方法はデータに合わせて選び、利用意図があれば、そこに使えそうな切り口も探します。
計画した項目の観測・解釈または未実施の理由を報告して完了し、結果から生まれた切り口をその場で追い続けません。
直接呼ぶ場合も出力は `runs/<番号>/result.md` と成果物で、`output.md` の執筆・更新は呼出元が担当します。
[単発EDAの雛形](skills/eda/assets/result.md)は「今回の観察の位置づけ」「対象と方法」「観察結果と読み取り」「今回言えることと限界」「参考・再現情報」の5章です。
何をどう観察し、その根拠からどこまで言えるかを確認できるようにします。質問別の回答や次の探索候補は付録に残します。
CLIの `init` と `run new` に `--template eda` を付けると、このEDA用run雛形を展開します。
汎用雛形で作成済みのrunは、記録を保ってこの構成へ整えます。

反復したい場合は「`$inquiry-lab:analyze` を使って、観測を受けて見方を変えながらEDAを繰り返して」と依頼します。
[eda-loop](skills/eda-loop/SKILL.md) が、1shotの結果を読み、次の依頼・方向転換・停止を判断します。
各回を新しいサブエージェントへ委任し、親は調査済み範囲と根拠から必要な情報を選んで渡します。
子は親の会話履歴を自動継承せず、指定runの結果と成果物を返します。親が知見の統合と次の探索を担当します。
独立したサブエージェントを使えない環境では `eda-loop` は利用できません。`eda` 単独の1shot利用は可能です。
対象・関心・予算の範囲で探索し、仮説の発見やモデル改善を完了条件にはしません。
loopから各回へ渡す関心・入力・既知の観測・固定条件と裁量・予算・出力先は、[依頼と返却の契約](skills/eda/references/request.md)に定めています。
loopは質問への回答と説明の不足から質問を見直し、必要な追加観察を次のrunへ渡します。
analyzeの記録手順を使い、[統合レポート雛形](skills/eda-loop/assets/report.md)で `output.md` をまとめます。
構成は「全体像の要約」「データと読み取りの前提」「データの特徴」「参考」の4章です。
項目を横断した総括は要約にまとめ、特徴の章では各観点の知見・探索経緯・未確認の範囲を示し、詳細を各runへつなぎます。
想定質問・項目別の回答・次の探索候補はrunに、停止理由と再開条件は作業履歴に残します。

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
Parquet対応のPyArrowを依存として導入します。Notebook Workbenchのインストールは不要です。

## データの基本確認

Notebookや分析ワークスペースを作らず、単一のローカルCSV・TSV・Parquetを読み取り専用で確認できます。
EDAでは[データの基本確認](skills/eda/references/data-inspection.md)を使い、観測範囲と読み方を共通化します。

```bash
inquiry-lab data inspect data.parquet --head 5 --json
inquiry-lab data inspect data.csv --columns category value --null-counts --json
inquiry-lab data values data.parquet --columns category --by period --limit 10 --group-limit 20 --json
```

`inspect` は列・型・行数・先頭行を返します。欠損数は `--null-counts` 指定時だけ全件集計し、
未指定は未集計と明示します。CSV/TSVは文字列を保持し空文字を欠損と数え、Parquetは保存された型を保持しnullを数えます。
CSV/TSVは行数取得にも全件走査が必要です。Parquetの行数はメタデータ由来で、先頭行は代表標本ではありません。

`values` は列ごとの値と件数を全件集計し、`--by` でグループを指定できます。
表示はJSON表現の辞書順で、頻度上位ではありません。省略件数も返します。
表示上限は走査量や集計メモリの上限ではないため、高カーディナリティの列は対象と費用を確認して選びます。
テキスト表示は長い値を省略し、`--json` は値と観測範囲を構造化して返します。

CSV/TSVはヘッダー付きUTF-8（BOM可）が対象です。ディレクトリのParquet dataset、URL、globは扱いません。
成功時は結果を標準出力へ返し、不正な入力データ・I/Oエラーは終了コード1、引数エラーは2で
標準エラーへ報告します。`--json` は成功時の結果形式を選び、エラーは既存CLIと同じテキスト形式です。
入力ファイルは変更せず、runや履歴は自動作成しません。EDAの中で使う場合は結果と実行条件を該当runに残します。

## JSONの基本確認

設定や分析結果のJSONを確認するときは、`json inspect` で指定階層の直下を表示します。

```bash
inquiry-lab json inspect config.json
inquiry-lab json inspect config.json --key model.params
inquiry-lab json inspect config.json --key model --key params
inquiry-lab json inspect results.json --key trials.0.metrics
```

単純な値はそのまま表示し、直下のオブジェクト・配列は展開せず型と要素数を示します。
`--key` はドット区切りと繰り返し指定を組み合わせられます。配列では0始まりの添字を使います。
キー名そのものに `.` が含まれるJSONは、参照先以外の階層も含めエラーにします。
重複キーも拒否し、どちらの値を読んだかが曖昧な状態を避けます。

オブジェクト・配列は入力順で先頭20項目を表示し、`--head` で表示数を変更できます。
長いキー・値はJSON表現の先頭160文字まで表示し、省略を明示します。
スカラーを参照した場合はその値だけを表示します。出力は閲覧用のテキストです。
入力は単一のローカルUTF-8 JSONファイル（BOM可）で、拡張子によらずJSONとして読みます。
JSONLは対象外です。ファイル全体をメモリへ読み込むため、表示上限やキー指定は読込量を制限しません。
入力を変更せず、runや履歴も自動作成しません。
不正なJSON・I/Oエラーは終了コード1、存在しないキーや不正なオプションは2で標準エラーへ報告します。

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

汎用テンプレート本文は英語、EDA用run雛形は日本語ですが、記入する言語は自由です。
Notebook、Pythonスクリプト、`analysis.yaml`、`run.yaml` は生成しません。
`state.json`は目的・終了条件を整理した後に`state update`で作成します。`init`では生成しません。

最初のrunをEDA用の構成で作る場合は、次のように指定します。

```bash
inquiry-lab init analyses/sales-eda --title "売上データの探索" --template eda
```

依頼文書と `output.md` は共通の雛形です。EDAはrun結果を仕上げ、`output.md` の執筆・更新は呼出元が担当します。

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

追加のrunは、次のように作成します。番号はCLIが割り当てます。

```bash
inquiry-lab run new --workspace analyses/sales-change --title "店舗別の変化を確認"
inquiry-lab run new --workspace analyses/sales-eda --title "期間別の構成を確認" --template eda
```

既存runが `001` だけなら、`runs/002/result.md` と `runs/002/artifacts/` を作り、runラベルを `run-002` に設定します。
`runs/` 直下の数字だけの名前の最大値＋1を使い、欠番は埋めません。数字の名前のファイルやリンクも使用済みとして扱います。
番号がなければ001から始め、3桁未満はゼロ埋めします。並行実行で作成先が衝突した場合は次の番号で再試行します。
成功時に返されたパスを保存先として使ってください。履歴JSONの記録や、履歴の `sequence` の採番は行いません。
既定では `requests/001-initial.md` を参照します。別の依頼には `--request requests/002-followup.md` のように、
分析先を基準とする相対パス、または絶対パスを指定できます。依頼文書は事前に作成してください。
既存runの再開には作成コマンドを使わず、保存済みの文書と成果物を使います。
`req-001` と `run-001` は文書を対応させるラベルです。runの番号を割り当てても、分析の実行・完了状態は管理しません。

## JSONで記録し、作業履歴を読む

同じ店舗別欠測の試行を[記録したJSON](docs/examples/history/000001.json)と
[生成した作業履歴.md](docs/examples/作業履歴.md)で比較できます。架空の集計値です。
履歴には各試行の短い `summary` を並べ、詳細へのリンクを置きます。
[各ループの詳細](docs/examples/history/000004.md)では、仮説・検証・結果・考察・参考を確認できます。
`results` の各要素が「結果」の箇条書きになり、`references` が「参考」のリンクになります。

既存のワークスペースを明示して、1回に1件を記録します。次はリポジトリのルートから
この例を新しいディレクトリに再現するコマンドです。

```bash
uv run inquiry-lab init analyses/missing --title "店舗別の欠測"
cp docs/examples/observations.csv analyses/missing/
for entry in docs/examples/history/*.json; do
  uv run inquiry-lab history record --workspace analyses/missing --input "$entry"
done
uv run inquiry-lab history render --workspace analyses/missing
```

- `record` はファイル（`--input` 省略時は標準入力）のJSONを検査し、`history/000001.json` のように保存します。`sequence` は作業順に付ける1〜999999の整数です。同じ番号の記録は上書きしません。
- 試行は `kind: "run"`、`run_id` と、`hypothesis`・`verification`・`results`・`discussion` の各配列で記します。各要素は1行の箇条書きです。試行を伴わない基準変更や停止判断には `kind: "decision"` を使い、`decision` と `reason` の配列に判断と理由を記します。
- `summary` には、その試行で何が分かり、どう判断したかを1〜2文で記します。経緯は全体像を辿るために必要な量に絞り、詳細な数値・手順・理由は既存の各項目に残します。以前のJSONに `summary` がない場合は、その記録の `current_state` を表示します。
- 両形式に `current_state`（その時点の判断や再開条件）と `references`（`label` と `target` の配列）を含めます。参照がなければ空配列にします。ローカルファイルはワークスペース基準のパス、MLflowなど外部の原本は対象のURLを指定します。
- 試行や判断が過去の記録を使った場合は、その番号を `"depends_on": [1]` のように指定できます。依存元は記録済みの小さい番号に限ります。`title` には図で読みたい短い題を指定できます。
- runの出発点にした過去のrunがあれば、その `sequence` を `base_run` に指定します。最初の試行や独立した試行は省略できます。[run-003の例](docs/examples/history/000004.json)は、原票を調べたrun-002（記録3）が行き詰まり、run-001（記録1）の集計から別の仮説を試したため、`"base_run": 1` と `"depends_on": [3]` を記録しています。
- 明示した依存関係があると、生成文書の冒頭にMermaidの図が出ます。線で結ばれた記録を表示し、各記録の詳細にも元のrunと依存元へのリンクを残します。CLIはMarkdownに `mermaid` コードブロックを書き、図の描画は対応するエディタやビューアが行います。
- `render` は1回で、短い `作業履歴.md` と各記録の詳細 `history/NNNNNN.md` を生成します。履歴には依存図・現在地・作業順の要約を置き、詳細にはJSONの各項目を表示します。ローカルの参考リンクは出力先に合わせて調整します。訂正は正本のJSONを編集し、両方を再生成します。

## 分析全体の状態とcompaction後の復元

`state.json`には全体の目標・終了条件と、現在の個別作業・次の行動を分けて残します。
[入力例](skills/analyze/assets/state.json)を案件に合わせて記入し、全体を渡して更新します。

```bash
inquiry-lab state update --workspace analyses/sales-change --input /tmp/analysis-state.json
inquiry-lab state show --workspace analyses/sales-change
inquiry-lab state context --workspace analyses/sales-change
```

`update`は検査後にファイルを置き換え、更新日時を付けます。`--input`省略時は標準入力を読みます。
`show`はネスト・件数・長さを省略せず、保存済みの状態全体をJSONで表示します。
`context`はCodexの`SessionStart`（`compact`）へ渡すJSONを返す読み取り専用コマンドです。
状態が読めない場合は復旧案内、履歴の最大番号と反映済み番号が異なる場合は照合の案内を返します。
長いstateは本文を部分的に切り捨てず、保存先と`show`での確認を案内します。

依頼文書は合意条件、historyは判断の経緯、runは実行根拠として残し、stateから参照します。
更新するのはanalyzeの担当者で、個別作業の開始前・判断後・条件変更後・中断時に保存します。
CLIは状態遷移や終了を自動判定しません。同時更新は後の保存が優先されるため、更新者を一人にします。
JSONの項目、再開時の照合、hookの設定例は[全体状態の手順](skills/analyze/references/state.md)を参照してください。
hookは設定と信頼操作が必要です。プラグインやCLIの導入だけでは有効になりません。

## CLIの動作

`init` の展開先は存在しないディレクトリを指定してください。親ディレクトリは必要に応じて作成します。
空のディレクトリ、既存ファイル、シンボリックリンクを含め、既存の展開先は変更せずに拒否します。
タイトルは前後の空白を除いて空でない1行を指定します。成功時は作成先の絶対パスを標準出力へ返します。
展開エラーは終了コード1、引数エラーは終了コード2で標準エラー出力へ報告します。
`run new` は既存の分析先の `runs/` に新しいrunだけを作成します。`runs/` がない場合やシンボリックリンクの場合、
依頼文書が存在しない場合は拒否します。既存の番号を避けて作成し、空ディレクトリやリンクも上書きしません。
展開中の書込失敗では、`init` は作成途中のワークスペース、`run new` は今回作ったrunだけを除去します。

## Pythonからグラフを保存する

可視化を使う分析環境へ、追加依存を含めてインストールします。CLIだけの利用では不要です。

```bash
uv pip install '.[visualize]'
```

上記はリポジトリ直下で実行します。別の環境では `.` をこのリポジトリのパスに置き換えます。

公開関数の選択と共通の保存仕様は [inquiry-lab-api](skills/inquiry-lab-api/SKILL.md) にまとめています。
Polars DataFrameを受け取り、固定した見た目の図を保存します。入力条件と実行できる使用例は次の参照を使います。

| 用途 | 関数 | APIの詳細・使用例 |
|---|---|---|
| 一般の数値列・分類スコアの分布 | `plot_histogram` | [ヒストグラム](skills/inquiry-lab-api/references/histogram.md) |
| 2値分類のROC曲線・AUC | `plot_roc_curve` | [分類モデルのグラフ](skills/inquiry-lab-api/references/classifier.md) |
| 予測確率の較正とビンごとの件数 | `plot_calibration_curve` | [分類モデルのグラフ](skills/inquiry-lab-api/references/classifier.md) |

0.2.0では、分類専用だった `visualize.ml.classifier.plot_score_histogram` を
`visualize.common.plot_histogram` に置き換えています。呼出元はimport先を変更し、
対象列を `column="score"` のように指定してください。

## 開発

このリポジトリで「モデル評価用の分析テンプレートを作りたい」などと依頼すると、開発用の
[create-analysis-template](.agents/skills/create-analysis-template/SKILL.md) が自動選択の対象になります。
目的、入力、比較手順、終了条件を `skills/<テーマ名>/SKILL.md` にまとめ、
出力レポートの雛形を `assets/report.md`、必要な詳細を `references/` に置きます。
各Skillの自動選択を無効にし、analyzeの選択表へ登録します。
繰り返し使う計算があれば、そのSkillの `scripts/` に同梱します。

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

CLIは `src/inquiry_lab/cli.py`、展開処理は `src/inquiry_lab/workspace.py` にあります。
文章テンプレートは `src/inquiry_lab/templates/` に置き、配布パッケージに同梱しています。
EDA用run雛形の正本は `skills/eda/assets/result.md` です。変更時は同じ内容を
`src/inquiry_lab/templates/eda-result.md` へコピーします。テストで両者の一致を検査します。
開発方針、変更時に守る契約、配布物の確認方法は [AGENTS.md](AGENTS.md) を参照してください。

## コード・テンプレート・Skillの由来

`src/inquiry_lab/data.py` と `tests/test_data.py` はNotebook Workbenchの `data_ops.py` と
対応テストを基にしています（Apache-2.0、commit `a2ad2658e29034acfd15e51b8ee81df00f6a7cf7`）。
2026-11-06時点のローカル作業ツリーを確認し、データの取得・JSON表現・集計範囲を引き継ぎ、
エラー処理とCLI登録をinquiry-labの契約へ合わせました。Notebook Workbench側の同等CLIは維持します。

文章テンプレートはNotebook Workbenchの`analysis_templates`を基にしています
（commit `1b2fb66572a1e55fd504b6161a1cf156d09c70e9`、Apache-2.0）。
元の問い・結果・統合レポートの構成を保ち、Notebook固有の参照、実行状態への依存、
未実装の必須項目検査を示すmarkerを除去しています。

`analyze` はNotebook Workbenchの分析Skillと反復分析の設計を基にしています
（Apache-2.0、ベースcommit `a2ad2658e29034acfd15e51b8ee81df00f6a7cf7`）。
2026-11-03時点のローカル作業ツリーにある、未コミットの `SKILL.md` の変更と
未追跡の `references/iterative-analysis.md` も参照しました。
Notebook固有の実行・状態管理を切り離し、問いの整理、判断基準、結果に応じた進行を扱う形へ
変更しています。具体的な保存形式や記録の操作手順は含めていません。

対話の進め方は、Matt Pocockの
[grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md)
の意思決定の依存関係、推奨案を伴う質問、調査可能な事実と利用者の判断の分離を参考にしています。
全分岐の解決を開始条件にせず、分析を始めるために必要な合意を作り、結果に応じて問い直します。
