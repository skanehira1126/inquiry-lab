# SHAPと特徴量重要度を読む

[models-understanding](../../models-understanding/SKILL.md)で選んだ手法に対応する節を使う。

## SHAPを使う場合

開発validの共通対象で計算し、特徴量ごとの `mean(abs(SHAP))` と、符号付きSHAP値の分布を確認する。
平均的な寄与の大きさに加え、一部の対象でだけ強く働く特徴量や、値によって寄与の方向が変わる特徴量を見る。
計算量が大きい場合は対象を抽出し、対象範囲・件数・抽出方法・乱数を保存する。
モデル版、説明する出力・クラス、出力尺度、説明方法、背景データの扱いを明記し、モデル間で比較条件を揃える。
この分布は対象ごとの寄与の違いであり、bootstrapによる信頼区間ではない。
[SHAPの集約と分布表示](https://shap.readthedocs.io/en/latest/example_notebooks/api_examples/plots/beeswarm.html)、
[説明条件](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html)

## 分割gainを使う場合

次の3項目を同じ木・反復範囲の未正規化値から集計する。

| 項目 | 定義 | 読み取ること |
|---|---|---|
| 累積gain（total_gain） | その特徴量を使った全分割のgainの合計 | 学習時の分割で積み上げた改善量 |
| 利用回数（split_count） | その特徴量が分割に使われた回数 | 分割でどれだけ繰り返し使われたか。木の本数や対象行数とは異なる。 |
| 平均gain（mean_gain） | total_gain / split_count | 使われた分割1回あたりの改善量。利用0回は未定義（N/A）とする。 |

LightGBMの `Booster.feature_importance(importance_type="gain")` は累積gain、`"split"` は利用回数なので、
両者から平均gainを求める。XGBoostの `Booster.get_score()` では `"total_gain"` が累積、`"gain"` が平均、
`"weight"` が利用回数であり、同じgainという名前でも定義が異なる。
APIが未使用の特徴量を省略する場合は、入力一覧と照合して累積gain・利用回数を0、平均gainをN/Aとして残す。
[LightGBMの定義](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html#lightgbm.Booster.feature_importance)、
[XGBoostの定義](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.Booster.get_score)

利用回数が多く平均gainが小さい場合と、少数回だが平均gainが大きい場合を区別する。
gainは学習時の指標であり、検証精度の改善幅とは扱わない。目的関数、木の数、パラメータなどが違うモデル間で
生の値の大小だけを比較しない。相関や同じ由来の特徴量も確認し、重要度の順位だけで一括削除しない。
選んだ手法で取得できない項目や計算上の制約は理由を示す。
