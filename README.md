[README.md](https://github.com/user-attachments/files/21808218/README.md)
# KMV/Merton + Activist Scenario Integration

本リポジトリは、**Merton構造型信用リスクモデル（KMV法）** と  
**アクティビスト・イベント由来の売上減少 → 時価総額下落シナリオ** を統合し、  
シナリオ別の **Distance to Default (DD)** と **Probability of Default (PD)** を推計します。

---

## 1. 背景と目的

**構造型（structural）信用リスクモデル**である Merton (1974) は、企業の**資産価値** \(V\) を原資産、**負債額** \(D\) を行使価格とする**ヨーロピアン・コール**として株式を捉え、償還時に \(V_T < D\) となる確率を**デフォルト確率（PD）**と定義します。  
本実装では、観測可能な **株式時価総額** \(E\) と **株式ボラティリティ** \(\sigma_E\) から、**資産価値** \(V\) と **資産ボラティリティ** \(\sigma_V\) を逆算し、**DDとPD**を算出します。  
さらに、**売上減少率**に対して**時価総額下落率**（Base / Light / Severe）を割り当て、\(E\) をシナリオ調整した上で PD 感応度を評価します。

---

## 2. 数式（Merton/KMV）

### 2.1 d1, d2 の定義
LaTeX:
$$
d_1 = \frac{\ln\!\left(\frac{V}{D}\right) + \left(r + \frac{1}{2} \sigma_V^2\right)T}{\sigma_V \sqrt{T}}, 
\quad d_2 = d_1 - \sigma_V \sqrt{T}
$$

画像（SVG）:
![d1_d2_formula](images/d1_d2.svg)

---

### 2.2 株式価値とボラティリティ
LaTeX:
$$
E = V\,N(d_1) - D e^{-rT} N(d_2),
\quad
\sigma_E \approx \frac{V\,N(d_1)}{E}\,\sigma_V
$$

画像（SVG）:
![equity_formula](images/equity_formula.svg)

---

### 2.3 DD と PD
LaTeX:
$$
DD = \frac{\ln\!\left(\frac{V}{D}\right) + \left(r - \frac{1}{2}\sigma_V^2\right)T}{\sigma_V \sqrt{T}}, 
\quad PD = N(-DD)
$$

画像（SVG）:
![dd_pd_formula](images/dd_pd_formula.svg)

---

## 3. 実装の要点

- **資産逆算**：観測 \(E, \sigma_E\) と既知 \(D, r, T\) から \(V, \sigma_V\) を同時に解く。  
  固定点反復／ニュートン風更新で、  
  \(E(V,\sigma_V)=V\,N(d_1)-De^{-rT}N(d_2)\) と \(\sigma_E \approx \frac{V N(d_1)}{E}\sigma_V\) を同時満たす。
- **シナリオ・マップ**：売上減少率 \(\Rightarrow\) 利益／時価総額下落率（Base / Light / Severe）。  
  範囲間は**線形補間**し、売上減少 \(s\%\) に対する**時価総額下落率**で \(E\) を調整。
- **ボラティリティ・ルール**（任意）：  
  `VolShockRule(mode="linear", gamma=0.5)` により、売上減少に応じて \(\sigma_E\) を拡大（`mode="none"` で無効）。

---

## 4. 使い方（クイックスタート）

### 4.1 依存関係
```bash
pip install numpy pandas scipy matplotlib

4.2 実行
python kmv_scenario_integration.py

4.3 期待される出力

表形式：各社 ×（Baseline / Base / Light / Severe）× 売上減少率 の
E,σE,V,σV,DD,PD を標準出力へ表示。

グラフ：各社ごとに PD vs Sales Decline を描画（matplotlib）。

5. 設定パラメータ

売上減少レンジ：sales_range を調整（例：range(0, 51, 5)）。

ボラ・ショック：VolShockRule(mode="none") で無効、gamma で強度を調整。

シナリオ表：BASE_MAP, LIGHT_MAP, SEVERE_MAP を編集（閾値間は線形補間）。

6. 検証と注意点

本モデルは負債の単一満期や資産価値の GBM など単純化を含みます。
実務では、期日構造や優先順位、クレジット・スプレッド等の追加考慮が必要です。

𝜎𝐸 の推定は、十分なサンプル長と外れ値処理が前提です。

パラメトリックなシナリオ・マップは企業特性に依存します。可能ならイベント・スタディや過去事例回帰で銘柄別に推定してください。

7. 参考文献

Merton, R. C. (1974). On the Pricing of Corporate Debt: The Risk Structure of Interest Rates. Journal of Finance, 29(2), 449–470.

Black, F., & Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. Journal of Political Economy, 81(3), 637–654.

Crosbie, P., & Bohn, J. (2003). Modeling Default Risk. KMV LLC.

8. ライセンス

MIT License



