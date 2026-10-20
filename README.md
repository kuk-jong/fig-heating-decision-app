# 전남 무화과 가온재배 의사결정지원 앱

무화과 가온재배 농가가 겨울재배 도입 여부를 판단할 수 있도록 난방비, 시설비, 여름/겨울 매출, 순이익을 계산하는 Streamlit 앱입니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud 배포

1. 이 폴더 전체를 GitHub 저장소에 올립니다.
2. Streamlit Community Cloud에서 `New app`을 선택합니다.
3. GitHub 저장소를 연결합니다.
4. Main file path는 `app.py`로 지정합니다.
5. App settings > Secrets에 아래 값을 등록합니다.

```toml
APP_PASSWORD = "원하는_접속_비밀번호"
# 배포 주소가 기본값과 다른 경우에만 추가하세요.
APP_URL = "https://내-앱-주소.streamlit.app"
```

## 주요 파일

- `app.py`: 배포용 진입 파일
- `01. 최초 파이썬 앱/app.py`: 실제 Streamlit 앱 본문
- `01. 최초 파이썬 앱/APP_BLUEPRINT.md`: 앱 설계도 및 UML
- `01. 최초 파이썬 앱/climate_csv_template.csv`: 10년치 지역별 기상 CSV 업로드용 예시 형식
- `requirements.txt`: Streamlit Cloud 설치 의존성

## CSV 업로드 형식

선택적으로 겨울철 기상자료 CSV를 업로드할 수 있습니다.

필수 컬럼:

- `region`
- `date`
- `min_temp`

예시는 `01. 최초 파이썬 앱/climate_csv_template.csv`를 참고하세요.


## 연간 사인 기온모형

- `T(x) = A + B sin(Cx + D)`, `C = 2π / 365.2425` 고정.
- x는 1월 1일부터의 날짜 위치를 해당 연도 길이로 정규화한 값입니다(윤년 보정).
- 선택 지역 CSV의 전체 일별 일최저기온으로 절편·사인·코사인 최소제곱 회귀를 수행하고 A·B·D로 환산합니다.
- 여러 해의 연중 자료를 권장합니다. 겨울 자료만으로도 적합할 수 있지만 계수 불확실성에 주의해야 합니다.
- 유효 관측일 3일 이상과 계절 범위 60일 이상이 필요합니다. 동일 날짜 중복은 평균, 잘못된 날짜·결측·무한 기온은 제외합니다.
- 잘못된 CSV를 업로드하면 오류를 표시하고 분석을 중단하며 내장값으로 몰래 대체하지 않습니다.
- CSV가 없으면 기존 내장 가정곡선을 연간식으로 근사합니다. 실측자료 회귀가 아니며 표시되는 경고를 확인하세요.
- 결과에서 계수, 관측일 수, 학습자료 적합 RMSE·R², 평균과 곡선을 확인할 수 있습니다.
- 난방비와 민감도 분석에 동일한 곡선을 적용합니다. 일최저기온을 14시간 가온기간 외기로 쓰는 가정은 유지합니다.
- 검증: `python -m unittest discover -s tests -v` (저장소 루트에서 실행).

설계·UML: [APP_BLUEPRINT.md](01.%20최초%20파이썬%20앱/APP_BLUEPRINT.md).
계산·데이터 명세: [CLIMATE_MODEL.md](docs/CLIMATE_MODEL.md).
기상 CSV 예시는 두 지역의 1년 합성자료이며 실측값이 아닙니다. 실제 분석에는 관측자료로 교체하세요.
