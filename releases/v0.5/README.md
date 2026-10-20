# 무화과 시설재배 경영의사결정지원시스템 — 후속 버전 0.5.0

등록 신청 당시 버전과 기존 운영 앱을 유지하면서 별도로 실행하는 후속 앱이다. 생산량·경영비·매출·수익성 분석, 연간 사인 기온 회귀, 난방비·민감도 분석 및 3D 온실 시각화를 포함한다.

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

1. 로그인 후 지역, 생산량·단가·경영비, 온실·보온·에너지 조건을 입력한다.
2. 실제 일별 관측 CSV가 있으면 업로드한다. 필수 컬럼은 region, date, min_temp이다.
3. 여러 해의 연중 자료를 권장한다. 사이드바의 예시는 합성자료이며 관측값이 아니다.
4. 연간 분석 실행 후 경영수지를 확인한다. 기온 회귀계수·적합도·기온곡선은 내부 계산용으로 사용하며 결과 화면에 표시하지 않는다.
5. 입력을 변경하면 다시 분석 실행을 누른다.

기온식은 `T(x)=A+B sin(Cx+D)`, C는 연간 주기로 고정하며 A·B·D를 회귀 추정한다.
CSV가 없으면 기존 내장 가정곡선의 근사값을 사용한다. 잘못된 CSV는 분석을 중단한다.
일최저기온을 가온 14시간의 외기로 사용하는 가정은 유지하며, 학습자료 적합도는 예측 정확도 보장이 아니다.

## 설계 및 검사

- [설계·UML](docs/APP_BLUEPRINT.md)
- [기온모형 명세](docs/CLIMATE_MODEL.md)
- `python -m unittest discover -s tests -v`: 수치·CSV·난방비 연결 8개 검사
- `python tests/smoke_app.py`: 로그인·분석·CSV 회귀·재실행·오류 중단 AppTest

기존 원본판과 기존 3D판의 실행 소스는 main 기준으로 보존한다. 본 폴더는 두 앱에서 파일을 불러오지 않는다.
