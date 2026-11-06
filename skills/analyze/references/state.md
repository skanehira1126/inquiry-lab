# 分析全体の状態

分析の実行を始めるときと、既存分析を再開するときに読む。
`state.json` は、全体の目的・終了条件と現在の個別作業を区別して保存する現在状態の要約。
合意条件の正本は依頼文書、判断の経緯はhistory、実行の根拠は各runに残し、stateから参照する。
状態の意味と次の行動はanalyzeが判断し、CLIは形式の検査・保存・表示を担当する。

## 更新と再開

1. 初回の実行前に[入力例](../assets/state.json)を案件に合わせて書き換える。
   全体の`goal`と`completion_criteria`を決め、今回の個別作業は`current_task`に置く。
   計画だけの依頼で新しい分析先を作る必要はない。`init`はstateを自動作成しない。
2. 個別作業の開始前、結果から次を決めた後、目的・条件の変更後、中断・報告前に更新する。
   判断の経緯は先にhistoryへ記録し、反映した最後の番号を`history_sequence`に置く。
   未実行の計画は完了扱いにせず、実行中なら進捗と再確認に必要な実行ID・出力先への参照を残す。
3. 再開時・compaction後は`state show`で全体を読む。反映済み番号より後の履歴、最新の利用者指示、
   関係するrunの原本と照合する。実行中の処理は稼働・結果を確認し、重複起動しない。
   stateが欠ける・古い・矛盾する場合は原本から現在地を確認して更新する。
4. 個別作業が完了したら、全体の終了条件の充足状況と残る証拠不足を見直す。
   目的への回答を揃えた終了、予算・追加試行の価値による打ち切り、入力・判断待ちによる保留を区別する。
   専門Skillのデータ利用制約や最終評価後の探索禁止は引き継ぐ。

```bash
inquiry-lab state update --workspace <分析先> --input <入力JSON>
inquiry-lab state show --workspace <分析先>
```

`update`はJSON全体を渡す置換方式。`--input`省略時は標準入力を読む。
既存ディレクトリだけを対象に、検査を通った全体を一時ファイルから置き換える。
入力エラーや置換前の書込失敗では以前のstateを保つ。`state.json`のシンボリックリンクは拒否する。
成功時は保存先の絶対パスを返す。部分更新・自動採否・状態遷移の実行・履歴生成はしない。
`show`は検査したJSON全体を表示する読み取り専用コマンドで、長さや階層による省略はない。
両コマンドともJSON・検査・I/Oエラーは終了コード1、引数エラーは2。

stateの更新者はanalyzeを担当する一人にする。同時更新は後から保存した内容になる。
子へ個別作業を委任した場合、子はrunと成果物を返し、親が全体stateを更新する。
直接呼ばれた専門Skillでは、その依頼自体を全体目標とする。

## JSONの項目

以下は全て必須。`updated_at`のみCLIが保存時にUTCで付け直すため入力では省略できる。
未知の項目・重複キー・ドットを含むキーを拒否する。
文字列は前後空白のない空でない1行とし、複数の項目は配列へ分ける。

| 項目 | 内容 |
|---|---|
| `schema_version` | `1` |
| `goal` | 分析全体で答える問い・判断 |
| `status` | `in_progress` / `completed` / `stopped` / `blocked` |
| `completion_criteria` | 1件以上の`condition`、`status`、`evidence`。statusは`met` / `unmet` / `unknown`、evidenceは根拠と参照の文字列配列 |
| `current_conclusion` | 現時点の回答。不明・未評価ならその理由 |
| `current_task` | 作業がなければ`null`。あれば下記のオブジェクト |
| `next_action` | 次に何をするかと理由。終了時は報告・再開条件など |
| `constraints` | 予算、利用可能データ、禁止事項などの文字列配列。なければ`[]` |
| `blockers` | 入力不足・利用者判断待ちなどの文字列配列。なければ`[]` |
| `history_sequence` | 反映済みの最後の履歴番号。未記録なら`0`、それ以外は記録済みの1〜999999 |
| `references` | `label`と`target`を持つ参照配列。依頼・履歴・run・原本へつなぐ |

`current_task`には`goal`、`done_when`、`status`、`run`、`progress`を全て置く。
`status`は`planned` / `in_progress` / `completed` / `blocked`。
`run`は分析先基準のrunのパス、runがなければ`null`。`progress`には実施済み・未実施を区別して記す。
`references.target`も分析先基準の相対パスか外部URLとし、ファイルの実在・根拠の妥当性はanalyzeが確認する。
`history_sequence`が指す記録は保存時にCLIも確認するが、意味上どこまで反映したかは推測しない。

## SessionStart hookで復元する

圧縮後の`SessionStart`（`source: compact`）から次を呼ぶ。
コマンドは明示された分析先だけを読み、標準出力へhook用JSONを返す。hookの標準入力は消費しない。

```bash
inquiry-lab state context --workspace <分析先の絶対パス>
```

設定例をプロジェクトの`.codex/hooks.json`へ既存hookと併存させる。
コマンド中のCLIと分析先は、実環境で使える絶対パスへ置き換える。
CLIがhookのPATHから見つかる場合は`inquiry-lab`でもよい。

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "^compact$",
      "hooks": [{
        "type": "command",
        "command": "\"/absolute/path/to/inquiry-lab\" state context --workspace \"/absolute/path/to/analysis\"",
        "timeout": 10,
        "additionalContextLimit": 8000
      }]
    }]
  }
}
```

CLIの`/hooks`、またはデスクトップのHooks設定で内容を確認し、信頼する操作が必要。
導入・更新やcompactionをCLIから自動実行しない。
通常の開始・再開にも適用する場合はmatcherを`^(startup|resume|compact)$`へ変える。
複数分析を扱う場合は対象パスを切り替え、別の分析状態を同じ会話へ混ぜない。

`context`は`hookSpecificOutput.additionalContext`へstateと照合手順を渡す。
state本文が整形後6000 UTF-8バイトを超える場合は、部分的に切り捨てずパスと`state show`の案内を返す。
読込・検査に失敗した場合も終了コード0で復旧案内と`systemMessage`を返し、未確認であることを明示する。
履歴の最大番号と`history_sequence`が異なる場合は照合を促す。stateや履歴を書き換えず、分析の終了も判断しない。
hookが未設定・未信頼・利用不可の場合も、再開時の`state show`と上記の照合手順は使える。

公式仕様: [SessionStart](https://learn.chatgpt.com/docs/hooks#sessionstart)。
`PostCompact`の標準出力はモデルの追加文脈にならないため、復元には使わない。
