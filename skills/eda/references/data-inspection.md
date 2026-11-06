# データの基本確認

ローカルのCSV・TSV・Parquetについて、構造と少量の実例、欠損、区分別の値を確認するときに読む。
この参照をEDAの基本確認の共通契約とし、同梱CLIを標準の取得手段にする。
利用範囲と予測用途のデータ分離を確認してから実行する。

## 確認内容を選ぶ

未知の入力ではスキーマと少量の実例から始める。既に確認した版・範囲の結果は再利用し、
毎回の全列・全件集計を必須にしない。列が多いときは関心に合う列を選び、JSONで取得する。

```bash
inquiry-lab data inspect data.parquet --head 5 --json
inquiry-lab data inspect data.csv --columns category value --null-counts --json
inquiry-lab data values data.csv --columns category --json
inquiry-lab data values data.parquet --columns category --by period --limit 10 --group-limit 20 --json
```

CLIは入力を変更せず、Notebookや分析ワークスペースを要求しない。
確認だけのCLI利用は結果を返して終了する。EDAの中で使う場合は、入力の版、実行コマンド、
選択列、確認範囲と結果を指定runへ記録し、保存したJSONを根拠として参照できるようにする。
既存結果を上書きしない保存先を選ぶ。コマンドはrunや履歴を自動作成しない。

## 結果の読み方を揃える

- `inspect` は行数、選択列の型、先頭5行を既定で返す。先頭行は代表標本ではない。
  `row_count_source` は行数の取得方法、`rows_examined` は値を確認した行数を示す。
  CSV/TSVは行数のために全件走査する。Parquetは行数をメタデータから取得し、プレビュー用のバッチを読む。
  `--head 0` のParquetはスキーマとメタデータだけで、全データページの読取成功を保証しない。
- `--null-counts` は選択列を全件走査する。省略時の `missing_counts: null` と
  `missing_counts_scope: not_requested` は未集計を示す。欠損ゼロと解釈しない。
- CSV/TSVは型推論せず文字列を保ち、先頭ゼロも保持する。欠損は空文字で、空白や文字列の
  `NA`・`null` は含めない。Parquetは保存された型を保ち、欠損は実際のnullだけで、NaNや空文字は含めない。
  `missing_definition` を確認し、業務上の欠測コードは別途定義する。欠損集計はトップレベルのセル単位。
- `values` は全行を読み、選択した各列を独立に集計する。`--by` は複数列でグループを作る。
  表示はcanonical JSON表現の辞書順で、頻度順や数値順ではない。頻度上位の一覧として扱わない。
  `unique_count`、`omitted_values`、`group_count`、`omitted_groups` から省略範囲を確認する。
  表示上限は全件走査や集計メモリの上限ではなく、メモリ使用量は値とグループの種類数に応じて増える。
- テキスト表示は長い値を省略する。値を照合・再利用するときは `--json` を使う。
  JSONでは日時・時刻はISO文字列、decimal・binary・duration・非有限浮動小数点数は
  `decimal`・`hex`・`duration`（整数と`unit`）・`float`で表す。日時・時刻・durationはナノ秒精度を保つ。

## 対象外と次の観察

入力は単一のローカルファイルに限る。CSV/TSVはヘッダー付きUTF-8（BOM可）とし、
重複・空の列名や不正な行はエラーになる。ディレクトリのParquet dataset、URL、globは対象外。
CLIが未導入の場合や対象外の入力では、案件のPython・SQLなどを使い、同じ確認範囲・欠損定義・
表示の省略を明示する。未対応の形式を、CLIで確認済みとは扱わない。

取得結果から列の意味やデータ品質の合否を自動確定しない。
キーの一意性、分布、関係、時間傾向など、次に必要な観察はEDAの計画で選ぶ。
この基本確認だけで1shot全体を完了したことにせず、依頼された範囲と終了条件に照らす。
