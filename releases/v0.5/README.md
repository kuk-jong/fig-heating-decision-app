# 무화과 시설재배 경영의사결정지원시스템 — 후속 버전 0.6.3

등록 신청 당시 버전과 기존 운영 앱을 유지하면서 별도로 실행하는 후속 앱이다. 생산량·경영비·매출·수익성 분석, 주간·시간별 기온 회귀, 난방비·민감도 분석 및 3D 온실 시각화를 포함한다.

## 로컬 실행

이 폴더에서 Python 3.12 기준으로 실행한다.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows에서는 패키지 설치 후 `run_app.bat`를 실행할 수 있다. 초기 로그인 비밀번호는 1234이다.
`.streamlit/secrets.toml.example`을 참고하여 같은 폴더의 `.streamlit/secrets.toml`에 APP_PASSWORD와 APP_URL을 설정한다. 실제 비밀번호 파일은 저장소에 올리지 않는다.
3D에는 WebGL 지원 브라우저와 Three.js CDN 인터넷 연결이 필요하다.

## 기존 서비스와 별도로 배포

Streamlit Community Cloud에서 **새 앱**을 만들고 다음 값을 사용한다.

- Repository: `kuk-jong/fig-heating-decision-app`
- Branch: `codex/annual-climate-regression` (PR #2 병합 후에는 main도 가능)
- Main file path: `releases/v0.5/app.py`
- Python: 3.12
- Secrets: 새 APP_PASSWORD, 새 서비스 주소 APP_URL

새 서비스의 실제 주소는 배포 후 정한다. 기존 서비스의 배포 설정을 새 경로로 바꾸지 않는다.

## 분석 방법

1. 지역과 관측지, 생산량·단가·경영비, 온실·보온·에너지 조건을 입력한다.
2. 목표온도와 겨울 작기 시작연도를 지정한다. 계산은 야간 18:00~다음 날 08:00로 제한하며 별도 가온시간 입력은 없다.
3. 업로드 없이 내장 관측 기반 주간 모형을 사용할 수 있다. 전남 15개 시군 20개 관측지의 2016~2025년 자료를 사용하며 실제 기간은 관측지별로 다르다.
4. 다른 자료를 쓰려면 한 관측지의 시간별 농업기상 원본 CSV 또는 datetime,temp_mean CSV를 업로드한다. 일최저기온 CSV는 사용할 수 없다.
5. 분석 실행 후 난방비·경영수지·민감도 결과를 확인한다. 계수와 기온곡선은 내부 계산용으로 유지한다.

주별 하루 기온함수를 사용하며 해당 주의 각 날짜에 같은 함수를 적용한다. 야간 14개 시간대 중 목표온도보다 낮은 시간만 열부하를 계산한다. U는 W/(㎡·K)로 가정하고 kWh로 변환한다. 평균 대표곡선은 한파를 평활화할 수 있으며 실측 난방비 정확도를 보장하지 않는다.

원본 시간별 관측자료는 저장소에 게시하지 않는다. tools/build_weekly_weather.py로 지역별 계수와 검증 기록을 재생성할 수 있다.

## 설계 및 검사

- [설계·UML](docs/APP_BLUEPRINT.md)
- [기온·난방부하 명세](docs/CLIMATE_MODEL.md)
- [관측자료·2025 독립연도 검증](docs/WEEKLY_WEATHER_VALIDATION.md)
- `python -m unittest discover -s tests -v`: 수치검사 22개
- `python tests/smoke_app.py`: 지역자료·야간 온도기준 가온·시간별 CSV·재실행·오류 처리 AppTest

배포 경로 호환성을 위해 폴더는 releases/v0.5로 유지하지만 앱 버전은 0.6.3이다. 기존 원본판 및 기존 3D판은 변경하지 않는다.

야간 14시간은 계산 가능한 시간대이며 연속 가동을 뜻하지 않는다. 실제 난방 필요시간은 하루 0~14시간이다. 주간 일사를 직접 계산하지 않는 대신 주간 난방을 제외한 가정이므로 흐린 날·한파의 총 난방비는 작게 추정할 수 있다.

기본 온실 기밀도는 과수연구소 설정에 따라 취약(누기 많음, 계수 1.25)이다. APP_URL이 없거나 비어 있으면 현재 후속 앱의 공개 주소로 QR코드와 다운로드 버튼을 표시한다. APP_URL을 지정하면 해당 주소를 우선한다.
