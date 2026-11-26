---
name: create-modeling-template
description: "inquiry-lab の modeling とモデル系専門 Skill の手順・参照文書・レポート雛形を作成・改訂するときに使う。対象はモデル改善の進行、設定比較、特徴量設計、モデルの性格把握・誤差診断。個別案件の学習・評価には modeling または analyze を使う。"
---

# モデリング用テンプレートを保守する

## 変更の置き場所を決める

- [modeling](../../../plugins/inquiry-lab/skills/modeling/SKILL.md) は、改善目的から比較を選び、結果を受けて次の仮説・採否・終了を判断する。これらの判断を変える依頼は入口の手順を改訂する。
- 設定の選定は [parameter-tuning](../../../plugins/inquiry-lab/skills/parameter-tuning/SKILL.md)、特徴量の表現・比較は [feature-design](../../../plugins/inquiry-lab/skills/feature-design/SKILL.md) を改訂する。新しい専門 Skill を作るときは、modeling から呼ぶ条件、渡す比較条件、受け取る結果を決める。
- 性格把握と誤差診断は [models-understanding](../../../plugins/inquiry-lab/skills/models-understanding/SKILL.md) と [error-analysis](../../../plugins/inquiry-lab/skills/error-analysis/SKILL.md) が担う。依頼や返却内容を変えたら、改善中に呼ぶ modeling と、診断だけを依頼する [analyze](../../../plugins/inquiry-lab/skills/analyze/SKILL.md) の両方から使えることを確認する。

## 比較から判断までをつなぐ

比較手順を変えるときは、基準モデルと候補、固定する評価対象・指標、変更点を特定し、どの結果なら採用・現行維持・保留を選ぶかを手順と出力で揃える。
データ区分の役割と test 評価・再評価の判断は[データ利用方針](../../../plugins/inquiry-lab/skills/modeling/references/data-usage.md)を参照し、共通方針の変更はその文書に反映する。

委任・再開を変えるときは[モデルの引き継ぎ手順](../../../plugins/inquiry-lab/skills/modeling/references/tree.md)を確認する。作業者の state は担当仮説を指し、比較結果と参照先は共有 tree と割当 run に残る。専門 Skill が結果を返した後、全体進行担当が Core・履歴・統合レポートに判断を反映できるかを確かめる。

## 手順とレポートを照合する

執筆指示は対象 Skill の出力節に、読者に示す項目はその `assets/report.md` に置く。[modeling の統合レポート](../../../plugins/inquiry-lab/skills/modeling/assets/report.md)では、採用中の構成、基準からの変化、停止理由から根拠の run をたどれるようにする。

例えば特徴量候補を見送る場合を当てはめる。専門 Skill の run に同条件での比較結果と見送り理由が残り、modeling はそれを根拠に現行維持や次の試行を選べるかを確認する。診断だけの依頼なら、観測結果と限界を返して完了できるかを確かめる。最後に変更した Skill の構文と呼出元・雛形へのリンクを検証する。
