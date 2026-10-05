"""독립 진입점: 원본 사이드바·성적표·개략도·민감도 구성을 유지."""
from pathlib import Path
import types
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from enhancement import sidebar_extension,show_extension
from view3d import greenhouse_component

st.set_page_config(page_title='무화과 경영의사결정지원 · 보완판',layout='wide')
source=(Path(__file__).parent/'original_app.py').read_text(encoding='utf-8')
# Load the snapshot's existing functions without running its page entry point.
source=source.rsplit('\nrequire_login()\n',1)[0]
source=source.replace('st.set_page_config(page_title="전남 무화과 경영 분석기", layout="wide")','')
core=types.ModuleType('fig_original_core')
exec(compile(source,str(Path(__file__).parent/'original_app.py'),'exec'),core.__dict__)
# The 3D component replaces the legacy drawing in this independent edition.
core.greenhouse_svg=lambda *args,**kwargs: ''
core.require_login()
st.title('전남 무화과 경영의사결정지원시스템 · 보완판')
st.caption('Python·Streamlit 원본 구성 유지 / 별도 사본 v0.1')
st.info('기존 비가림 농가의 시설전환과 신규 진입을 비교합니다. 원본 겨울 모델의 기간은 11~2월이며, 기본 수량·단가는 근거를 확인해 변경하세요.')
extension=sidebar_extension(st)
submit,values=core.collect_inputs()
if submit:
    values['_extension']=extension
    st.session_state['enh_last_analysis']=values.copy()
if 'enh_last_analysis' in st.session_state:
    saved=st.session_state['enh_last_analysis'].copy()
    st.caption('마지막으로 분석 실행한 입력 결과입니다. 입력을 변경하면 다시 분석 실행을 눌러 반영하세요.')
    with st.expander('3D 온실 구조 · 양액설비 시각화',expanded=True):
        if saved['gh_ridge_h'] <= saved['gh_side_h']:
            st.warning('3D 표시를 위해 동고를 측고보다 높게 입력하세요.')
        else:
            components.html(greenhouse_component(core.normalize_inputs(saved),core),height=390)
            st.caption('입력 온실 규격 연동 · 양액기 쪽이 정면 · 보온커튼 열림. 식재 간격과 설비는 개략 예시이며 투자·수량 계산과 독립입니다.')
    core.show_results(saved)
    saved=core.normalize_inputs(saved)
    show_extension(st,pd,saved,core)
else:st.info('왼쪽 사이드바를 입력하고 연간 분석 실행을 눌러주세요.')
core.show_references()

