"""Streamlit interaction test of the deployed entry point."""
from io import BytesIO
from pathlib import Path
import os, sys, json
from streamlit.testing.v1 import AppTest
APP_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_DIR));os.chdir(APP_DIR)
a=AppTest.from_file(str(APP_DIR/'app.py'),default_timeout=60).run()
assert not a.exception,[e.message for e in a.exception]
a.text_input[0].set_value('1234')
next(b for b in a.button if b.label=='로그인').click();a.run()
assert not a.exception,[e.message for e in a.exception]
assert any('v0.6.3' in c.value for c in a.caption)
next(b for b in a.button if '연간 분석 실행' in b.label).click();a.run()
assert not a.exception,[e.message for e in a.exception]
assert len(a.metric)==13
assert any('해남군 옥천면' in c.value and '관측' in c.value for c in a.caption)
assert not any('외기온 추정식' in e.label for e in a.expander)
next(s for s in a.selectbox if s.label=='전남 시·군 선택').set_value('나주시')
next(b for b in a.button if '연간 분석 실행' in b.label).click();a.run()
assert not a.exception and len(a.metric)==13
assert any('나주시' in c.value and '관측' in c.value for c in a.caption)
next(s for s in a.selectbox if s.label=='전남 시·군 선택').set_value('해남군')
next(b for b in a.button if '연간 분석 실행' in b.label).click();a.run()
assert not any(s.label=='가온 가능시간 (시간/일)' for s in a.slider)
assert not any(s.label=='가온 시작 시각' for s in a.selectbox)
assert any('야간 18:00~다음 날 08:00 난방' in c.value for c in a.caption)
saved=a.session_state['enh_last_analysis'].copy()
saved['climate_file']=BytesIO((APP_DIR/'examples/hourly_climate_example.csv').read_bytes())
a.session_state['enh_last_analysis']=saved;a.run()
assert not a.exception and len(a.metric)==13,[e.message for e in a.exception]
assert any('업로드 시간별' in c.value for c in a.caption)
a.run();assert not a.exception and len(a.metric)==13
saved['climate_file']=BytesIO(b'bad\n1');a.session_state['enh_last_analysis']=saved;a.run()
assert not a.exception and len(a.error)==1 and len(a.metric)==0
# A county lacking bundled observations must not silently borrow another county.
a.session_state['enh_last_analysis']={**saved,'climate_file':None,'weather_station':'목포시 업로드 관측지'};a.run()
assert not a.exception and len(a.error)==1 and len(a.metric)==0
# Summer-only analysis does not require winter weather.
a.session_state['enh_last_analysis']={**saved,'climate_file':None,'winter_enabled':False};a.run()
assert not a.exception and len(a.metric)>0
print(json.dumps({'version':'0.6.3','bundled_weather':'pass','night_thermostatic_14h':'pass','hourly_csv':'pass',
                  'rerun':'pass','invalid_csv':'pass','unavailable_county':'pass','summer_only':'pass'},ensure_ascii=False))
