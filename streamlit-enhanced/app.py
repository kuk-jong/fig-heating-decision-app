"""독립 진입점: 원본 사이드바·성적표·개략도·민감도 구성을 유지."""
from pathlib import Path
import types
import streamlit as st
import streamlit.components.v1 as components
from view3d import greenhouse_component

st.set_page_config(page_title='무화과 경영의사결정지원 · 보완판',layout='wide')
source=(Path(__file__).parent/'original_app.py').read_text(encoding='utf-8')
# Load the snapshot's existing functions without running its page entry point.
source=source.rsplit('\nrequire_login()\n',1)[0]
source=source.replace('st.set_page_config(page_title="전남 무화과 경영 분석기", layout="wide")','')
source=source.replace(':,.1f} 만원', ':,.0f} 만원').replace(':,.1f}만원', ':,.0f}만원')
anchor='    st.subheader("☀️ 1. 여름 재배 성적표")'
if source.count(anchor)!=1:
    raise RuntimeError('원본 성적표 위치를 확인하세요.')
source=source.replace(anchor,'    show_greenhouse_3d(values)\n\n'+anchor)
core=types.ModuleType('fig_original_core')
exec(compile(source,str(Path(__file__).parent/'original_app.py'),'exec'),core.__dict__)
def show_greenhouse_3d(values):
    with st.expander('3D 온실 구조 · 양액설비 시각화',expanded=True):
        if values['gh_ridge_h'] <= values['gh_side_h']:
            st.warning('3D 표시를 위해 동고를 측고보다 높게 입력하세요.')
        else:
            components.html(greenhouse_component(core.normalize_inputs(values),core),height=390)
            st.caption('입력 온실 규격 연동 · 양액기 쪽이 정면 · 보온커튼 열림. 식재 간격과 설비는 개략 예시이며 투자·수량 계산과 독립입니다.')
core.show_greenhouse_3d=show_greenhouse_3d
# The 3D component replaces the legacy drawing in this independent edition.
core.greenhouse_svg=lambda *args,**kwargs: ''
core.require_login()
st.title('전남 무화과 경영의사결정지원시스템 · 보완판')
st.caption('Python·Streamlit 원본 구성 + 3D 온실 / 별도 사본 v0.3')
st.info('원본 겨울 모델의 기간은 11~2월입니다. 기본 수량·단가는 현장 근거를 확인해 변경하세요.')
submit,values=core.collect_inputs()
if submit:
    st.session_state['enh_last_analysis']=values.copy()
if 'enh_last_analysis' in st.session_state:
    saved=st.session_state['enh_last_analysis'].copy()
    st.caption('마지막으로 분석 실행한 입력 결과입니다. 입력을 변경하면 다시 분석 실행을 눌러 반영하세요.')
    core.show_results(saved)
else:st.info('왼쪽 사이드바를 입력하고 연간 분석 실행을 눌러주세요.')
core.show_references()

