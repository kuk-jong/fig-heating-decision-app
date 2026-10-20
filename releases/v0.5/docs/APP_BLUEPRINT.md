# 무화과 시설재배 경영의사결정지원시스템 — 후속 버전 설계

버전: 0.6.0 / 개정일: 2026-10-21.
`releases/v0.5`의 독립 앱만 설명한다. 등록 신청 당시 제출본이나 기존 운영 앱을 대체한 문서가 아니다.
이번 구현·문서·UML 갱신에는 생성형 AI를 활용했다.

## 1. 버전 경계

- 기존 원본판 `app.py` 및 `01. 최초 파이썬 앱/app.py`는 main 기준 코드를 유지한다.
- 기존 3D판 `streamlit-enhanced/`도 main 기준 코드를 유지한다.
- 새 앱은 `releases/v0.5/app.py`에서 실행한다. 독립 `original_app.py`, `view3d.py`, JavaScript, 패키지 목록과 예시 CSV를 포함한다.
- 현재 main 기반 기존 파일을 바꾸지 않은 상태로 새 앱을 별도 Streamlit 서비스에 배포할 수 있다.
- 비밀번호와 QR 주소는 새 서비스의 APP_PASSWORD·APP_URL로 설정한다. 기본 비밀번호는 1234이다.

## 2. 현재 구현과 계산

생산량·판매단가로 매출, 여름 경영비 비율, 겨울 난방비와 시설 감가상각, 계절별·연간 손익을 계산한다. 보온·목표온도·연료단가·기밀도·방풍벽 조건의 민감도를 비교한다. 3D 식재·설비는 예시이며 생산량·투자비 계산과 독립이다.

2016~2025년 시간별 관측자료로 관측지·주차별 24시간 대표곡선을 적합한다. 같은 주는 같은 함수를 적용하고 다음 주에 계수를 변경한다. 사용자가 정한 가온 허용시간에 시간별 양의 온도차만 합산하며, U의 W 단위를 kWh로 환산한다. 계수·기온곡선은 내부 계산용이다. 자료가 없거나 부족하면 분석을 중단하며 다른 지역 자료로 대체하지 않는다.

자세한 계수·데이터·검증 명세: [CLIMATE_MODEL.md](CLIMATE_MODEL.md).

## 3. 파일 구조

```text
releases/v0.5/
  app.py                 # 후속 버전 화면·접속·마지막 결과 유지
  original_app.py        # 독립 계산 함수 본문 (기존 파일을 런타임에 참조하지 않음)
  view3d.py
  viewer-assets/         # 온실·식재·설비 JavaScript
  requirements.txt
  weekly_weather.py      # 주차별 시간기온·열부하
  data/weekly_weather.json # 20개 관측지별 52주 계수 (원자료 미포함)
  VERSION                # 0.6.0
  run_app.bat
  .streamlit/secrets.toml.example
  examples/hourly_climate_example.csv  # 합성 예시, 관측자료 아님
  tests/test_weekly_weather.py
  tests/smoke_app.py
  docs/                  # 설계·명세·다이어그램 원본
```

## 4. 사용자 기능 요약

아래는 유스케이스 요약 흐름도이다.

```mermaid
flowchart LR
    user["사용자"] --> login["로그인"]
    user --> inputFarm["생산·경영·온실 조건 입력"]
    user --> uploadCsv["시간별 관측 CSV 업로드"]
    user --> sample["합성 예시 CSV 다운로드"]
    user --> schedule["관측지·시작 시각·가온시간 선택"]
    user --> analyze["연간 경영분석 실행"]
    analyze --> income["계절·연간 매출과 비용 확인"]
    analyze --> view["3D 온실 확인"]
    analyze --> sensitivity["조건별 민감도 비교"]
```

## 5. 클래스 UML — 향후 구조 분리안

현재 실제 코드는 함수와 dict 기반이다. 아래 클래스는 객체·모듈로 분리할 때의 설계안이며 구현 완료를 뜻하지 않는다.

```mermaid
classDiagram
    class GreenhouseSpec {
        +float width
        +float length
        +float side_height
        +float ridge_height
        +int span_count
        +str side_wing_level
        +float side_wing_width
        +float side_wing_factor
        +str airtightness_level
        +float airtightness_factor
        +floor_area() float
        +surface_area() float
        +render_preview() str
    }

    class ProductionPlan {
        +float summer_yield
        +int summer_price
        +float summer_cost_ratio
        +float winter_yield
        +int winter_price
    }

    class InvestmentCost {
        +int film_cost
        +int curtain_cost
        +int heater_cost
        +int facility_cost
        +annual_depreciation() int
    }

    class EnergySetting {
        +str energy_source
        +int unit_fuel_cost
        +float target_temp
        +float u_value
        +float airtightness_factor
        +float side_wing_factor
    }

    class WeeklyWeather {
        +str region_name
        +dict weekly_coefficients
        +str station
        +float hourly_period
        +str source
        +float rmse
        +float r_squared
        +hourly_temperature(date, hour) float
    }

    class ClimateDataset {
        +DataFrame records
        +validate_schema() bool
        +filter_region(region_name) DataFrame
        +clean_and_merge_daily() DataFrame
        +fit_weekly_models(station) WeeklyWeather
    }

    class AnalysisInput {
        +GreenhouseSpec greenhouse
        +ProductionPlan production
        +InvestmentCost investment
        +EnergySetting energy
        +WeeklyWeather climate
        +HeatingSchedule schedule
    }

    class HeatingSchedule {
        +int start_hour
        +int duration_hours
        +int winter_start_year
    }

    class AnalysisResult {
        +int summer_revenue
        +int summer_cost
        +int winter_revenue
        +int winter_fuel_cost
        +int depreciation
        +int annual_profit
    }

    class SensitivityResult {
        +DataFrame target_temp_table
        +DataFrame fuel_cost_table
        +DataFrame insulation_table
        +DataFrame airtightness_table
        +DataFrame side_wing_table
    }

    class HeatingCalculator {
        +calculate_heating_cost(input) int
        +calculate_profit(input) AnalysisResult
        +calculate_sensitivity(input) SensitivityResult
    }

    AnalysisInput --> GreenhouseSpec
    AnalysisInput --> ProductionPlan
    AnalysisInput --> InvestmentCost
    AnalysisInput --> EnergySetting
    AnalysisInput --> WeeklyWeather
    AnalysisInput --> HeatingSchedule
    ClimateDataset --> WeeklyWeather
    HeatingCalculator --> AnalysisInput
    HeatingCalculator --> AnalysisResult
    HeatingCalculator --> SensitivityResult
```

## 6. 시퀀스 UML — 후속 버전의 실제 호출

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant Weather
    participant Heat
    participant Report
    User->>UI: 관측지·작기·가온시간 지정
    UI->>Weather: 내장 계수 또는 시간별 CSV 사용
    Weather->>Weather: CSV이면 전처리 및 주별 회귀
    Weather-->>UI: 주별 모형 또는 오류
    alt 자료 부족
        UI-->>User: 분석 중단 및 오류 표시
    else 유효한 모형
        UI->>Heat: 경영분석 및 민감도 계산
        Heat->>Weather: 날짜·시각별 기온 평가
        Weather-->>Heat: 가온 허용시간의 기온
        Heat->>Heat: 양의 온도차 및 W에서 kWh 환산
        Heat->>Heat: 연료비 및 전기 기본요금 계산
        Heat-->>Report: 경영수지 및 시나리오 결과
        Report-->>User: 경영 리포트 표시
    end
```

## 7. 후속 버전 컴포넌트 관계

현재 파일·함수군 연결을 표현한 흐름도이다. 기존 앱은 별도 서비스로 유지한다.

```mermaid
flowchart TD
    entry["releases/v0.5/app.py"] --> core["동일 폴더의 original_app.py 동적 로딩"]
    entry --> version["후속 버전 0.6.0 표시"]
    entry --> config["새 서비스의 APP_PASSWORD 및 APP_URL"]
    core --> regress["CSV 검증 및 weekly_weather.py 주별 시간기온"]
    regress --> numpy["NumPy lstsq"]
    regress --> bundled["data/weekly_weather.json 20개 관측지"]
    core --> heating["난방비·연간 수지·민감도"]
    entry --> component["view3d.py"]
    component --> assets["viewer-assets JavaScript"]
    assets --> cdn["Three.js CDN"]
    entry --> sample["examples 합성 CSV 다운로드"]
    tests["수치검사 및 AppTest"] --> core
    tests --> entry
```

## 8. 데이터 처리 흐름

```mermaid
flowchart TD
    request["분석 실행"] --> hasCsv{"시간별 CSV 있음"}
    hasCsv -->|"예"| validate["필수 컬럼 및 선택 지역 검증"]
    validate --> clean["무효 행 제외 및 중복 시간 평균"]
    clean --> eligible{"필요 주차별 24시간과 관측수 충족"}
    validate -->|"오류"| stop["오류 표시 및 분석 중단"]
    eligible -->|"아니오"| stop
    eligible -->|"예"| regression["절편 sin cos 최소제곱 회귀"]
    regression --> model["주차별 24시간 기온모형"]
    hasCsv -->|"아니오"| fallback["선택 관측지의 내장 주별 모형"]
    fallback --> model
    model --> daily["작기 날짜와 시각별 T_w(h)"]
    daily --> heat["가온 허용시간의 양의 온도차"]
    heat --> cost["W에서 kWh 환산 및 효율·연료단가"]
    cost --> profit["매출·경영비·감가상각과 손익 계산"]
    model --> sensitivity["같은 모형으로 민감도 비교"]
    profit --> report["리포트"]
    sensitivity --> report
```

## 9. 검증·운영 경계

- 수치·CSV·난방비 연결 단위검사 21개 및 AppTest 로그인·분석·CSV 회귀·재실행·오류 중단 확인.
- 다이어그램 5종은 Mermaid 문법과 SVG·PNG 렌더링 확인.
- 원본판과 기존 3D판 실행 소스는 main과 동일한지 별도 비교.
- 예시 CSV는 합성자료이며 실측 검증을 대신하지 않는다.
- 2025년 기온은 이전 연도로 적합한 곡선으로 별도 검증했다. 시간대 대표평균의 적합 RMSE와 독립연도 기온 RMSE는 구분한다.
- 실측 난방비 검증, 일별 목표온도 변경, 시간별 관측 자체를 이용한 연도별 난방비 분석은 후속 과제이다.
