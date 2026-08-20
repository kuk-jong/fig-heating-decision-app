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
