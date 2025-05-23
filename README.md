# DCF Calculator

A sophisticated web application for calculating intrinsic value of stocks using Discounted Cash Flow (DCF) model and multiple-based valuation methods.

## Screenshot 

- DCF calculator tab
  
![1](https://github.com/user-attachments/assets/24edbb89-c384-4886-af4a-3693c7c26d03)

- Financial Statement tab
  
![2](https://github.com/user-attachments/assets/63177b36-decc-45a7-8f40-427828e3ffc3)


- Charts & Latest News tab
  
![3](https://github.com/user-attachments/assets/ab21ed74-15ef-4b7f-9045-f493b80f5284)

---

## English

### Overview

DCF Calculator is a powerful Streamlit-based web application designed for investors, financial analysts, and students to perform comprehensive stock valuations. The application combines modern financial theory with user-friendly interfaces, allowing for detailed intrinsic value calculations through multiple valuation methodologies including Discounted Cash Flow (DCF), earnings-based approaches, and market multiple comparisons.

Built with Python and leveraging real-time financial data from yfinance, this tool offers professional-grade valuation capabilities in an accessible format, suitable for both beginners and experienced financial professionals.

### Key Features

#### Multiple Valuation Models

- **Two-stage DCF Model**: 
  - Implements the industry-standard two-stage DCF model with customizable growth and terminal phases
  - Calculates present value of future cash flows and terminal value
  - Adjusts for net debt and shares outstanding to determine per-share intrinsic value
  - Visualizes projected cash flows with interactive charts

- **Earnings-Based DCF**: 
  - Uses EPS (Earnings Per Share) as the foundation for valuation
  - Supports both trailing and forward EPS calculations
  - Automatically extracts EPS data from financial statements
  - Projects future earnings based on historical growth rates or user inputs

- **FCF-Based DCF**: 
  - Utilizes Free Cash Flow as the primary valuation metric
  - Automatically calculates FCF from operating cash flow and capital expenditures
  - Provides adjustable growth rate projections based on historical data
  - Accounts for capital structure variations in different companies

- **Peter Lynch Fair Value**: 
  - Implements Peter Lynch's famous PEG-based valuation methodology
  - Considers earnings growth rate in relation to P/E ratio
  - Determines fair value using the formula: Fair Value = EPS × Growth Rate × PEG Ratio
  - Compares results against current market prices for buy/sell recommendations

- **EV/EBITDA Valuation**: 
  - Calculates Enterprise Value to EBITDA ratio for comparative analysis
  - Provides industry-relative valuation metrics
  - Adjusts for capital structure differences between companies
  - Offers a comprehensive look at operating performance valuation

- **Multiple-Based Valuation (P/E, P/B)**: 
  - Uses traditional market multiples for quick comparative valuation
  - Compares current multiples to historical averages and industry benchmarks
  - Calculates fair value based on normalized multiple ranges
  - Combines multiple approaches for a balanced valuation perspective

#### Comprehensive Financial Data

- **Real-Time Market Data**: 
  - Fetches latest stock prices, market caps, and trading volumes
  - Updates automatically on each search
  - Displays key price points and trading patterns

- **Financial Statement Analysis**: 
  - Provides access to Income Statements, Balance Sheets, and Cash Flow Statements
  - Shows up to 5 years of historical financial data
  - Highlights key financial metrics and ratios
  - Calculates year-over-year growth rates for critical metrics

- **Advanced Ratio Analysis**: 
  - Calculates and interprets essential financial ratios
  - Tracks liquidity metrics (Current Ratio, Quick Ratio)
  - Analyzes profitability indicators (ROE, ROA, Profit Margins)
  - Evaluates efficiency metrics (Asset Turnover, Inventory Turnover)
  - Assesses solvency measures (Debt-to-Equity, Interest Coverage)

> **Note**: Please note that the status and interpretation of financial ratios are relative and may not be completely accurate in all contexts. These ratios should be used as guidance rather than absolute indicators of financial health.

#### Interactive Analysis Tools

- **Sensitivity Analysis**: 
  - Creates dynamic sensitivity tables showing valuation changes across variable inputs
  - Allows users to instantly see how changes in growth rates affect fair value
  - Provides visual heat maps of different WACC and terminal growth rate combinations
  - Identifies critical thresholds where valuation classifications change

- **Interactive Visualizations**: 
  - Displays DCF model components with detailed breakdowns
  - Shows historical price charts with moving averages
  - Compares fair value estimates to current market prices
  - Presents financial statement trends graphically

- **Value Creation Analysis**: 
  - Compares ROIC (Return on Invested Capital) to WACC
  - Assesses whether companies are creating or destroying shareholder value
  - Visualizes historical value creation trends
  - Provides insights into sustainable competitive advantages

#### Advanced WACC Calculations

- **Detailed WACC Methodology**: 
  - Calculates Weighted Average Cost of Capital with transparent methodology
  - Automatically retrieves risk-free rates from current treasury yields
  - Estimates market risk premium based on historical data
  - Retrieves beta values directly from financial data providers

- **Cost of Equity Components**: 
  - Uses CAPM (Capital Asset Pricing Model) for cost of equity
  - Allows manual adjustment of risk-free rate and market risk premium
  - Provides beta estimates with explanation of volatility implications
  - Offers industry-specific equity risk premium guidance

- **Cost of Debt Analysis**: 
  - Extracts interest expense data from financial statements
  - Considers tax shield effects on cost of debt
  - Calculates after-tax cost of debt automatically
  - Allows manual overrides for special situations

- **Capital Structure Optimization**: 
  - Analyzes optimal debt-to-equity ratios
  - Shows how capital structure changes affect WACC
  - Compares current capital structure to industry averages
  - Provides suggestions for potential WACC improvements

### Installation Guide

```bash
# Clone the repository
git clone https://github.com/parkminhyung/DCF_calculator

# Navigate to the project directory
cd DCF_calculator

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt

# Run the application
streamlit run main.py
```

### Detailed Usage Guide

#### Getting Started

1. Enter a stock ticker symbol in the sidebar (e.g., AAPL, MSFT, GOOGL)
2. Click the "Search" button to fetch the latest financial data
3. Review the automatically populated company overview at the top of the screen

#### DCF Valuation Model Tab

1. Review the pre-populated DCF parameters based on the company's financial data
2. Adjust the following key inputs as needed:
   - Initial Free Cash Flow (FCF)
   - Forecast Period (typically 5-10 years)
   - Growth Rate (%)
   - Terminal Growth Rate (%)
   - WACC components (risk-free rate, beta, market risk premium, etc.)
3. Click "Apply Parameters" to recalculate the DCF model
4. Examine the valuation results including:
   - DCF Fair Value per share
   - Comparison to current market price
   - Upside/downside potential
   - Valuation status classification

#### Financial Statements Tab

1. Navigate between Income Statement, Balance Sheet, and Cash Flow Statement subtabs
2. Review historical financial data with year-over-year comparisons
3. Analyze key financial ratios and metrics
4. Export financial data for further analysis if needed

#### Sensitivity Analysis

1. Locate the sensitivity analysis section in the DCF Valuation tab
2. Observe how changes in growth rates and discount rates impact fair value
3. Identify the combination of variables that bring the model closest to current market prices
4. Use insights to refine your base case assumptions

#### Model Comparison

1. Review the different valuation models (DCF, Earnings-based, Peter Lynch, etc.)
2. Compare fair value estimates across methodologies
3. Consider the weighted average valuation from multiple approaches
4. Use the "Valuation Status" indicator to guide investment decisions

### Use Cases

- **Individual Investors**: Evaluate potential stock investments based on intrinsic value
- **Portfolio Managers**: Screen large sets of stocks for valuation opportunities
- **Financial Analysts**: Create detailed valuation models with sensitivity testing
- **Finance Students**: Learn practical applications of DCF and other valuation methods
- **Corporate Finance**: Estimate company valuations for strategic planning

### Dependencies

- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **yfinance**: Financial data API
- **matplotlib**: Static data visualization
- **plotly**: Interactive charts and graphs
- **datetime**: Date and time manipulation
- **math**: Mathematical functions



### License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 한국어

### 개요

DCF 계산기는 투자자, 재무 분석가 및 학생들이 종합적인 주식 가치평가를 수행할 수 있도록 설계된 강력한 Streamlit 기반 웹 애플리케이션입니다. 이 애플리케이션은 현대 금융 이론과 사용자 친화적인 인터페이스를 결합하여 현금흐름할인법(DCF), 수익 기반 접근법 및 시장 멀티플 비교를 포함한 다양한 가치평가 방법론을 통해 상세한 내재 가치 계산을 가능하게 합니다.

Python으로 제작되고 yfinance의 실시간 재무 데이터를 활용하는 이 도구는 초보자와 경험 있는 금융 전문가 모두에게 적합한 접근 가능한 형식으로 전문적인 수준의 가치평가 기능을 제공합니다.

### 주요 기능

#### 다양한 가치평가 모델

- **2단계 DCF 모델**: 
  - 맞춤 설정 가능한 성장 및 영구 단계로 업계 표준 2단계 DCF 모델 구현
  - 미래 현금흐름과 영구가치의 현재가치 계산
  - 순부채와 발행주식수를 조정하여 주당 내재가치 결정
  - 인터랙티브 차트로 예상 현금흐름 시각화

- **수익 기반 DCF**: 
  - EPS(주당순이익)를 가치평가의 기반으로 사용
  - 과거 및 미래 EPS 계산 지원
  - 재무제표에서 EPS 데이터 자동 추출
  - 과거 성장률 또는 사용자 입력에 기반한 미래 수익 예측

- **FCF 기반 DCF**: 
  - 자유현금흐름을 주요 가치평가 지표로 활용
  - 영업현금흐름과 자본지출로부터 FCF 자동 계산
  - 과거 데이터에 기반한 조정 가능한 성장률 예측 제공
  - 다양한 기업의 자본 구조 변동 고려

- **피터 린치 공정가치**: 
  - 피터 린치의 유명한 PEG 기반 가치평가 방법론 구현
  - P/E 비율과 관련하여 수익 성장률 고려
  - 공정가치 = EPS × 성장률 × PEG 비율 공식 사용
  - 매수/매도 추천을 위해 현재 시장 가격과 결과 비교

- **EV/EBITDA 가치평가**: 
  - 비교 분석을 위한 기업가치 대 EBITDA 비율 계산
  - 산업 관련 가치평가 지표 제공
  - 기업 간 자본 구조 차이 조정
  - 영업 성과 가치평가에 대한 포괄적인 관점 제공

- **멀티플 기반 가치평가 (P/E, P/B)**: 
  - 신속한 비교 가치평가를 위한 전통적인 시장 멀티플 사용
  - 현재 멀티플을 과거 평균 및 산업 벤치마크와 비교
  - 정규화된 멀티플 범위에 기반한 공정가치 계산
  - 균형 잡힌 가치평가 관점을 위한 다중 접근법 결합

#### 종합적인 재무 데이터

- **실시간 시장 데이터**: 
  - 최신 주가, 시가총액 및 거래량 가져오기
  - 각 검색 시 자동 업데이트
  - 주요 가격 포인트 및 거래 패턴 표시

- **재무제표 분석**: 
  - 손익계산서, 재무상태표 및 현금흐름표에 접근 제공
  - 최대 5년간의 과거 재무 데이터 표시
  - 주요 재무 지표 및 비율 강조
  - 중요 지표의 전년 대비 성장률 계산

- **고급 비율 분석**: 
  - 필수 재무 비율 계산 및 해석
  - 유동성 지표 추적 (유동비율, 당좌비율)
  - 수익성 지표 분석 (ROE, ROA, 이익률)
  - 효율성 지표 평가 (자산회전율, 재고회전율)
  - 지급능력 측정 (부채 대 자본 비율, 이자보상배율)

> **참고**: 재무 비율의 상태와 설명은 상대적인 것이라, 모든 상황에서 정확하지 않을 수 있습니다. 이러한 비율은 재무 상태의 절대적인 지표가 아닌 참고 지표로 사용되어야 합니다.

#### 대화형 분석 도구

- **민감도 분석**: 
  - 변수 입력에 따른 가치평가 변화를 보여주는 동적 민감도 테이블 생성
  - 사용자가 성장률 변화가 공정가치에 미치는 영향을 즉시 확인 가능
  - 다양한 WACC 및 영구성장률 조합의 시각적 히트맵 제공
  - 가치평가 분류가 변경되는 중요 임계값 식별

- **인터랙티브 시각화**: 
  - 상세한 분석과 함께 DCF 모델 구성 요소 표시
  - 이동평균을 포함한 과거 주가 차트 표시
  - 공정가치 추정치와 현재 시장 가격 비교
  - 재무제표 추세를 그래프로 표시

- **가치 창출 분석**: 
  - ROIC(투자자본수익률)와 WACC 비교
  - 기업이 주주 가치를 창출하는지 또는 파괴하는지 평가
  - 과거 가치 창출 추세 시각화
  - 지속 가능한 경쟁 우위에 대한 통찰력 제공

#### 고급 WACC 계산

- **상세한 WACC 방법론**: 
  - 투명한 방법론으로 가중평균자본비용 계산
  - 현재 국채 수익률로부터 무위험 수익률 자동 검색
  - 과거 데이터에 기반한 시장 위험 프리미엄 추정
  - 금융 데이터 제공업체로부터 베타값 직접 검색

- **자기자본비용 구성요소**: 
  - 자기자본비용에 CAPM(자본자산가격결정모델) 사용
  - 무위험 수익률 및 시장 위험 프리미엄의 수동 조정 허용
  - 변동성 영향에 대한 설명과 함께 베타 추정치 제공
  - 산업별 자기자본 위험 프리미엄 지침 제공

- **부채비용 분석**: 
  - 재무제표에서 이자비용 데이터 추출
  - 부채비용에 대한 세금 혜택 효과 고려
  - 세후 부채비용 자동 계산
  - 특수 상황을 위한 수동 오버라이드 허용

- **자본 구조 최적화**: 
  - 최적의 부채 대 자본 비율 분석
  - 자본 구조 변화가 WACC에 미치는 영향 표시
  - 현재 자본 구조를 산업 평균과 비교
  - 잠재적 WACC 개선을 위한 제안 제공

### 설치 가이드

```bash
# 저장소 복제
git clone https://github.com/parkminhyung/DCF_calculator

# 프로젝트 디렉토리로 이동
cd DCF_calculator

# 가상환경 생성 (선택사항이지만 권장됨)
python -m venv venv
source venv/bin/activate  # Windows에서: venv\Scripts\activate

# 필요한 패키지 설치
pip install -r requirements.txt

# 애플리케이션 실행
streamlit run main.py
```

### 상세 사용 가이드

#### 시작하기

1. 사이드바에 주식 티커 기호 입력 (예: AAPL, MSFT, GOOGL)
2. "검색" 버튼을 클릭하여 최신 재무 데이터 가져오기
3. 화면 상단에 자동으로 채워진 회사 개요 검토

#### DCF 가치평가 모델 탭

1. 회사의 재무 데이터에 기반한 미리 채워진 DCF 매개변수 검토
2. 필요에 따라 다음과 같은 주요 입력값 조정:
   - 초기 자유현금흐름(FCF)
   - 예측 기간 (일반적으로 5-10년)
   - 성장률 (%)
   - 영구성장률 (%)
   - WACC 구성요소 (무위험 수익률, 베타, 시장 위험 프리미엄 등)
3. "매개변수 적용" 클릭하여 DCF 모델 재계산
4. 다음을 포함한 가치평가 결과 검토:
   - 주당 DCF 공정가치
   - 현재 시장 가격과 비교
   - 상승/하락 잠재력
   - 가치평가 상태 분류

#### 재무제표 탭

1. 손익계산서, 재무상태표 및 현금흐름표 서브탭 사이 이동
2. 전년 대비 비교와 함께 과거 재무 데이터 검토
3. 주요 재무 비율 및 지표 분석
4. 필요한 경우 추가 분석을 위해 재무 데이터 내보내기

#### 민감도 분석

1. DCF 가치평가 탭에서 민감도 분석 섹션 찾기
2. 성장률 및 할인율 변화가 공정가치에 미치는 영향 관찰
3. 모델을 현재 시장 가격에 가장 가깝게 만드는 변수 조합 식별
4. 통찰력을 활용하여 기본 가정 세분화

#### 모델 비교

1. 다양한 가치평가 모델 (DCF, 수익 기반, 피터 린치 등) 검토
2. 방법론 간 공정가치 추정치 비교
3. 다중 접근법의 가중 평균 가치평가 고려
4. 투자 결정을 안내하기 위해 "가치평가 상태" 지표 사용

### 사용 사례

- **개인 투자자**: 내재 가치에 기반한 잠재적 주식 투자 평가
- **포트폴리오 매니저**: 가치평가 기회를 위한 대규모 주식 세트 스크리닝
- **재무 분석가**: 민감도 테스트와 함께 상세한 가치평가 모델 생성
- **재무 학생**: DCF 및 기타 가치평가 방법의 실질적인 응용 학습
- **기업 재무**: 전략 계획을 위한 기업 가치평가 추정

### 의존성

- **streamlit**: 웹 애플리케이션 프레임워크
- **pandas**: 데이터 조작 및 분석
- **numpy**: 수치 계산
- **yfinance**: 재무 데이터 API
- **matplotlib**: 정적 데이터 시각화
- **plotly**: 인터랙티브 차트 및 그래프
- **datetime**: 날짜 및 시간 조작
- **math**: 수학 함수



### 라이센스

이 프로젝트는 MIT 라이센스에 따라 라이센스가 부여됩니다 - 자세한 내용은 LICENSE 파일을 참조하세요.

---

## 日本語

### 概要

DCF計算機は、投資家、財務アナリスト、学生が包括的な株式評価を行うために設計された強力なStreamlitベースのウェブアプリケーションです。このアプリケーションは、現代の金融理論とユーザーフレンドリーなインターフェースを組み合わせ、DCF（割引キャッシュフロー）、収益ベースのアプローチ、市場の倍率比較など、さまざまな評価方法による詳細な内在価値計算を可能にします。

Pythonで構築され、yfinanceからのリアルタイム財務データを活用するこのツールは、初心者から経験豊富な金融専門家まで適したアクセスしやすい形式で、プロフェッショナルグレードの評価機能を提供します。

### 主な機能

#### 複数の評価モデル

- **2段階DCFモデル**: 
  - カスタマイズ可能な成長段階と永続段階を持つ業界標準の2段階DCFモデルを実装
  - 将来のキャッシュフローと継続価値の現在価値を計算
  - 純負債と発行済株式数を調整して1株当たりの内在価値を決定
  - インタラクティブなチャートで予測キャッシュフローを視覚化

- **収益ベースDCF**: 
  - EPS（1株当たり利益）を評価の基礎として使用
  - 過去と将来のEPS計算をサポート
  - 財務諸表からEPSデータを自動抽出
  - 過去の成長率またはユーザー入力に基づいて将来の収益を予測

- **FCFベースDCF**: 
  - フリーキャッシュフローを主要な評価指標として活用
  - 営業キャッシュフローと資本的支出からFCFを自動計算
  - 過去のデータに基づく調整可能な成長率予測を提供
  - 異なる企業の資本構造の変動を考慮

- **ピーター・リンチの公正価値**: 
  - ピーター・リンチの有名なPEGベースの評価方法論を実装
  - P/E比率に関連して収益成長率を考慮
  - 公正価値 = EPS × 成長率 × PEG比率の公式を使用
  - 買い/売り推奨のために現在の市場価格と結果を比較

- **EV/EBITDA評価**: 
  - 比較分析のためのエンタープライズバリューとEBITDA比率を計算
  - 業界関連の評価指標を提供
  - 企業間の資本構造の違いを調整
  - 営業パフォーマンス評価の包括的な見方を提供

- **マルチプルベース評価（P/E、P/B）**: 
  - 迅速な比較評価のための伝統的な市場倍率を使用
  - 現在の倍率を過去の平均と業界ベンチマークと比較
  - 正規化された倍率範囲に基づいて公正価値を計算
  - バランスの取れた評価視点のために複数のアプローチを組み合わせる

#### 包括的な財務データ

- **リアルタイム市場データ**: 
  - 最新の株価、時価総額、取引量を取得
  - 各検索で自動更新
  - 主要な価格ポイントと取引パターンを表示

- **財務諸表分析**: 
  - 損益計算書、貸借対照表、キャッシュフロー計算書へのアクセスを提供
  - 最大5年間の過去の財務データを表示
  - 主要な財務指標と比率を強調
  - 重要な指標の前年比成長率を計算

- **高度な比率分析**: 
  - 重要な財務比率の計算と解釈
  - 流動性指標の追跡（流動比率、当座比率）
  - 収益性指標の分析（ROE、ROA、利益率）
  - 効率性指標の評価（資産回転率、在庫回転率）
  - 支払能力指標の評価（負債資本比率、利息カバレッジ）

> **注意**: 財務比率の状態と説明は相対的なものであり、すべての状況で正確であるとは限りません。これらの比率は、財務健全性の絶対的な指標ではなく、ガイダンスとして使用する必要があります。

#### インタラクティブな分析ツール

- **感度分析**: 
  - 変数入力に応じた評価変化を示す動的感度テーブルを作成
  - 成長率の変化が公正価値にどう影響するかをユーザーがすぐに確認可能
  - 様々なWACCと永続成長率の組み合わせのビジュアルヒートマップを提供
  - 評価分類が変更される重要なしきい値を特定

- **インタラクティブな可視化**: 
  - 詳細な内訳を含むDCFモデルコンポーネントを表示
  - 移動平均を含む過去の価格チャートを表示
  - 公正価値の推定値と現在の市場価格を比較
  - 財務諸表のトレンドをグラフィカルに表示

- **価値創造分析**: 
  - ROIC（投下資本利益率）とWACCを比較
  - 企業が株主価値を創造しているか破壊しているかを評価
  - 過去の価値創造トレンドを視覚化
  - 持続可能な競争優位性に関する洞察を提供

#### 高度なWACC計算

- **詳細なWACC方法論**: 
  - 透明な方法論で加重平均資本コストを計算
  - 現在の国債利回りから無リスク金利を自動的に取得
  - 過去のデータに基づく市場リスクプレミアムの推定
  - 金融データプロバイダーから直接ベータ値を取得

- **資本コストコンポーネント**: 
  - 株主資本コストにCAPM（資本資産価格モデル）を使用
  - 無リスク金利と市場リスクプレミアムの手動調整を許可
  - ボラティリティの意味の説明を含むベータ推定値を提供
  - 業界特有の株式リスクプレミアムガイダンスを提供

- **負債コスト分析**: 
  - 財務諸表から金利費用データを抽出
  - 負債コストへの税シールド効果を考慮
  - 税引後負債コストを自動計算
  - 特殊状況のための手動オーバーライドを許可

- **資本構造最適化**: 
  - 最適な負債対資本比率を分析
  - 資本構造の変更がWACCにどのように影響するかを表示
  - 現在の資本構造を業界平均と比較
  - 潜在的なWACC改善のための提案を提供

### インストールガイド

```bash
# リポジトリをクローン
git clone https://github.com/parkminhyung/DCF_calculator

# プロジェクトディレクトリに移動
cd DCF_calculator

# 仮想環境を作成（オプションですが推奨）
python -m venv venv
source venv/bin/activate  # Windowsでは: venv\Scripts\activate

# 必要なパッケージをインストール
pip install -r requirements.txt

# アプリケーションを実行
streamlit run main.py
```

### 詳細な使用ガイド

#### はじめに

1. サイドバーに株式ティッカーシンボルを入力（例：AAPL、MSFT、GOOGL）
2. 「検索」ボタンをクリックして最新の財務データを取得
3. 画面上部に自動的に入力された会社概要を確認

#### DCF評価モデルタブ

1. 会社の財務データに基づいて事前入力されたDCFパラメータを確認
2. 必要に応じて次の主要な入力を調整：
   - 初期フリーキャッシュフロー（FCF）
   - 予測期間（通常5〜10年）
   - 成長率（％）
   - 永続成長率（％）
   - WACCコンポーネント（無リスク金利、ベータ、市場リスクプレミアムなど）
3. 「パラメータを適用」をクリックしてDCFモデルを再計算
4. 次を含む評価結果を検討：
   - 1株当たりDCF公正価値
   - 現在の市場価格との比較
   - 上昇／下落の可能性
   - 評価状況分類

#### 財務諸表タブ

1. 損益計算書、貸借対照表、キャッシュフロー計算書のサブタブ間を移動
2. 前年比較を含む過去の財務データを確認
3. 主要な財務比率と指標を分析
4. 必要に応じて、さらなる分析のために財務データをエクスポート

#### 感度分析

1. DCF評価タブで感度分析セクションを見つける
2. 成長率と割引率の変化が公正価値にどのように影響するかを観察
3. モデルを現在の市場価格に最も近くする変数の組み合わせを特定
4. 得られた洞察を使用して基本ケースの仮定を改良

#### モデル比較

1. さまざまな評価モデル（DCF、収益ベース、ピーター・リンチなど）を確認
2. 方法論間の公正価値推定値を比較
3. 複数のアプローチからの加重平均評価を検討
4. 投資判断のガイドとして「評価状況」インジケータを使用

### ユースケース

- **個人投資家**: 内在価値に基づいて潜在的な株式投資を評価
- **ポートフォリオマネージャー**: 評価機会のために大規模な株式セットをスクリーニング
- **財務アナリスト**: 感度テスト付きの詳細な評価モデルを作成
- **金融学生**: DCFやその他の評価方法の実践的な応用を学習
- **企業財務**: 戦略的計画のための企業評価を推定

### 依存関係

- **streamlit**: ウェブアプリケーションフレームワーク
- **pandas**: データ操作と分析
- **numpy**: 数値計算
- **yfinance**: 財務データAPI
- **matplotlib**: 静的データ可視化
- **plotly**: インタラクティブなチャートとグラフ
- **datetime**: 日付と時間の操作
- **math**: 数学関数



### ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細はLICENSEファイルを参照してください。

---

## 中文

### 概述

DCF计算器是一个专为投资者、财务分析师和学生设计的强大Streamlit基础网络应用程序，使用户能够进行全面的股票估值。该应用结合了现代金融理论和用户友好的界面，通过多种估值方法（包括贴现现金流、基于收益的方法和市场倍数比较）进行详细的内在价值计算。

这款工具采用Python构建，利用yfinance的实时财务数据，以易于使用的格式提供专业级的估值功能，适合初学者和经验丰富的金融专业人士使用。

### 主要功能

#### 多种估值模型

- **两阶段DCF模型**: 
  - 实现行业标准的两阶段DCF模型，具有可定制的增长和永续期
  - 计算未来现金流和终值的现值
  - 调整净债务和流通股数以确定每股内在价值
  - 通过交互式图表可视化预测现金流

- **基于收益的DCF**: 
  - 使用EPS（每股收益）作为估值基础
  - 支持计算历史和预期EPS
  - 自动从财务报表中提取EPS数据
  - 基于历史增长率或用户输入预测未来收益

- **基于FCF的DCF**: 
  - 将自由现金流作为主要估值指标
  - 从经营现金流和资本支出自动计算FCF
  - 提供基于历史数据的可调整增长率预测
  - 考虑不同公司的资本结构变化

- **彼得·林奇公允价值**: 
  - 实现彼得·林奇著名的基于PEG的估值方法
  - 考虑P/E比率相关的收益增长率
  - 使用公式：公允价值 = EPS × 增长率 × PEG比率
  - 将结果与当前市场价格进行比较，以提供买入/卖出建议

- **EV/EBITDA估值**: 
  - 计算企业价值与EBITDA比率进行比较分析
  - 提供行业相关估值指标
  - 调整公司间资本结构差异
  - 提供对经营业绩估值的全面视角

- **基于倍数的估值（P/E，P/B）**: 
  - 使用传统市场倍数进行快速比较估值
  - 将当前倍数与历史平均值和行业基准进行比较
  - 根据标准化倍数范围计算公允价值
  - 结合多种方法提供平衡的估值视角

#### 全面的财务数据

- **实时市场数据**: 
  - 获取最新股价、市值和交易量
  - 每次搜索自动更新
  - 显示关键价格点和交易模式

- **财务报表分析**: 
  - 提供利润表、资产负债表和现金流量表访问
  - 显示长达5年的历史财务数据
  - 突出关键财务指标和比率
  - 计算关键指标的同比增长率

- **高级比率分析**: 
  - 计算和解释基本财务比率
  - 跟踪流动性指标（流动比率、速动比率）
  - 分析盈利能力指标（ROE、ROA、利润率）
  - 评估效率指标（资产周转率、存货周转率）
  - 评估偿债能力指标（债务权益比、利息覆盖率）

> **注意**：请注意，财务比率的状态和解释是相对的，在所有情况下可能不完全准确。这些比率应被用作指导，而非财务健康状况的绝对指标。

#### 交互式分析工具

- **敏感度分析**: 
  - 创建动态敏感度表，显示不同输入变量下的估值变化
  - 允许用户立即看到增长率变化对公允价值的影响
  - 提供不同WACC和永续增长率组合的视觉热图
  - 识别估值分类发生变化的临界阈值

- **交互式可视化**: 
  - 使用详细分解显示DCF模型组件
  - 显示带有移动平均线的历史价格图表
  - 比较公允价值估计与当前市场价格
  - 图形化呈现财务报表趋势

- **价值创造分析**: 
  - 比较ROIC（投资资本回报率）与WACC
  - 评估公司是否在创造或消耗股东价值
  - 可视化历史价值创造趋势
  - 提供关于可持续竞争优势的见解

#### 高级WACC计算

- **详细的WACC方法**: 
  - 使用透明方法计算加权平均资本成本
  - 从当前国债收益率自动获取无风险利率
  - 基于历史数据估计市场风险溢价
  - 直接从财务数据提供商获取贝塔值

- **权益成本组成部分**: 
  - 使用CAPM（资本资产定价模型）计算权益成本
  - 允许手动调整无风险利率和市场风险溢价
  - 提供贝塔估计值并解释波动性含义
  - 提供行业特定的权益风险溢价指导

- **债务成本分析**: 
  - 从财务报表中提取利息费用数据
  - 考虑税盾效应对债务成本的影响
  - 自动计算税后债务成本
  - 允许特殊情况的手动覆盖

- **资本结构优化**: 
  - 分析最优债务权益比率
  - 显示资本结构变化如何影响WACC
  - 将当前资本结构与行业平均水平比较
  - 提供潜在WACC改进建议

### 安装指南

```bash
# 克隆存储库
git clone https://github.com/parkminhyung/DCF_calculator

# 导航到项目目录
cd DCF_calculator

# 创建虚拟环境（可选但推荐）
python -m venv venv
source venv/bin/activate  # Windows上：venv\Scripts\activate

# 安装所需包
pip install -r requirements.txt

# 运行应用程序
streamlit run main.py
```

### 详细使用指南

#### 入门

1. 在侧边栏输入股票代码（例如AAPL、MSFT、GOOGL）
2. 点击"搜索"按钮获取最新财务数据
3. 查看屏幕顶部自动填充的公司概览

#### DCF估值模型选项卡

1. 查看基于公司财务数据预填充的DCF参数
2. 根据需要调整以下关键输入：
   - 初始自由现金流（FCF）
   - 预测期间（通常为5-10年）
   - 增长率（%）
   - 永续增长率（%）
   - WACC组成部分（无风险利率、贝塔值、市场风险溢价等）
3. 点击"应用参数"重新计算DCF模型
4. 检查估值结果，包括：
   - 每股DCF公允价值
   - 与当前市场价格比较
   - 上行/下行潜力
   - 估值状态分类

#### 财务报表选项卡

1. 在利润表、资产负债表和现金流量表子选项卡之间导航
2. 查看带有同比比较的历史财务数据
3. 分析关键财务比率和指标
4. 如需要，导出财务数据进行进一步分析

#### 敏感度分析

1. 在DCF估值选项卡中找到敏感度分析部分
2. 观察增长率和折现率变化如何影响公允价值
3. 确定使模型最接近当前市场价格的变量组合
4. 利用洞察来细化基础案例假设

#### 模型比较

1. 查看不同估值模型（DCF、基于收益、彼得·林奇等）
2. 比较不同方法的公允价值估计
3. 考虑多种方法的加权平均估值
4. 使用"估值状态"指标指导投资决策

### 使用案例

- **个人投资者**: 基于内在价值评估潜在股票投资
- **投资组合经理**: 筛选大量股票寻找估值机会
- **财务分析师**: 创建带有敏感度测试的详细估值模型
- **金融学生**: 学习DCF和其他估值方法的实际应用
- **企业财务**: 为战略规划估计公司估值

### 依赖项

- **streamlit**: 网络应用程序框架
- **pandas**: 数据操作和分析
- **numpy**: 数值计算
- **yfinance**: 财务数据API
- **matplotlib**: 静态数据可视化
- **plotly**: 交互式图表和图形
- **datetime**: 日期和时间操作
- **math**: 数学函数



### 许可证

该项目根据MIT许可证授权 - 详情请参阅LICENSE文件。
