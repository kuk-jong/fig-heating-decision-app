"""원본 화면에 덧붙이는 전환·신규 진입 분석. 통화 단위: 원."""
def decision_metrics(summary, investment, baseline_cash, extra_cost, own_labor, loan_percent, rate, years):
    loan = investment * loan_percent / 100
    interest = loan * rate / 100
    principal = loan / years
    operating = summary['total_annual_profit'] + summary['depreciation'] - extra_cost
    profit = operating - summary['depreciation'] - interest
    increment = operating - baseline_cash
    return dict(investment=investment,loan=loan,interest=interest,principal=principal,
                operating=operating,profit=profit,full_profit=profit-own_labor,
                equity_cash=operating-interest-principal,increment=increment,
                payback=investment/increment if investment>0 and increment>0 else None)


def sidebar_extension(st):
    with st.sidebar:
        st.markdown('### 농가 유형 · 전환 목적')
        farmer=st.radio('분석 대상',['기존 비가림 농가','신규 재배 농가'],key='enh_farmer')
        purpose=st.selectbox('검토 목적',['겨울 생산','수확기 연장','조기 출하','비가림 유지'],key='enh_purpose')
        st.caption('목적은 상담 기록입니다. 원본 겨울 계산은 11~2월·14시간 가온 기준으로 유지합니다. 연장·조기출하 기간을 자동 계산하지 않습니다.')
        with st.expander('추가 투자 · 운영 조건',expanded=False):
            baseline=st.number_input('현재 연간 영업현금 (만원)',value=900.0,step=50.0,disabled=farmer=='신규 재배 농가',help='현재 매출에서 현금 경영비를 차감. 감가상각·원금 차감 전.')
            existing_dep=st.number_input('재사용 기존 시설의 연간 감가상각 (만원)',min_value=0.0,value=0.0,disabled=farmer=='신규 재배 농가')
            reuse=st.multiselect('재사용하는 시설 (신규 투자 제외)',['이중비닐 공사','보온커튼 공사','이중비닐 피복재','다겹보온커튼 자재'],disabled=farmer=='신규 재배 농가')
            extra_invest=st.number_input('골조·묘목·기반 등 추가 투자 (만원)',min_value=0.0,value=0.0,help='신규 농가는 원본 보온 패키지 외에 필요한 전체 시설 견적을 입력하세요.')
            life=st.number_input('추가 투자 내용연수 (년)',min_value=1,max_value=50,value=10)
            winter_labor=st.number_input('추가 고용노동비 (만원/년)',min_value=0.0,value=0.0)
            winter_other=st.number_input('추가 포장·배송·수리 등 (만원/년)',min_value=0.0,value=0.0)
            own=st.number_input('자가노동 평가액 (만원/년)',min_value=0.0,value=0.0)
            loan=st.slider('신규 투자 차입비율 (%)',0,100,0)
            rate=st.number_input('연 금리 (%)',min_value=0.0,max_value=30.0,value=4.0)
            years=st.number_input('원금 균등 상환기간 (년)',min_value=1,max_value=20,value=5)
        with st.expander('준비 확인 · 근거',expanded=False):
            ready={k:st.checkbox(k,key='ready_'+k) for k in ['용수·배수','전력·난방 견적','관리·수확 인력','작형 교육·실증','판매처·판매량']}
            source=st.selectbox('수량·단가·추가 비용 근거',['가정값','농가 실적','현장 견적·실적 혼합','실증·참고자료'])
            note=st.text_area('상담 메모·근거 날짜',max_chars=3000)
    return dict(farmer=farmer,purpose=purpose,baseline=0 if farmer=='신규 재배 농가' else baseline*10000,
                existing_dep=0 if farmer=='신규 재배 농가' else existing_dep*10000,
                reuse=[] if farmer=='신규 재배 농가' else reuse,extra_invest=extra_invest*10000,life=life,
                extra_cost=(winter_labor+winter_other)*10000,own=own*10000,loan=loan,rate=rate,years=years,ready=ready,source=source,note=note)


def show_extension(st,pd,values,core):
    x=values['_extension']
    adjusted=values.copy()
    mapping={'이중비닐 공사':'cost_film','보온커튼 공사':'cost_curtain','이중비닐 피복재':'cost_heater','다겹보온커튼 자재':'cost_facility'}
    for name in x['reuse']:adjusted[mapping[name]]=0
    region=core.REGION_DATA[values['region_name']]
    csv,error=core.climate_params_from_csv(values.get('climate_file'),values['region_name'])
    if csv:region={'base':csv['base'],'amp':csv['amp']}
    result=core.calculate_profit_summary(adjusted,region)
    # Original excludes facility depreciation in summer-only mode. Additional
    # analysis explicitly includes investment for any selected plan.
    result['depreciation']=core.annual_depreciation_won(*[adjusted[k] for k in mapping.values()])+x['extra_invest']/x['life']+x['existing_dep']
    result['total_annual_profit']=result['summer_revenue']-result['summer_cost']+result['winter_revenue']-result['winter_fuel_cost']-result['depreciation']
    investment=sum(adjusted[k] for k in mapping.values())*10000+x['extra_invest']
    r=decision_metrics(result,investment,x['baseline'],x['extra_cost'],x['own'],x['loan'],x['rate'],x['years'])
    st.divider();st.subheader('시설전환 · 신규 진입 보완 분석')
    st.caption('위 성적표는 원본 계산입니다. 아래는 재사용·추가 투자·추가 운영비·자가노동·차입을 반영한 별도 결과입니다. 자동 투자 권고는 하지 않습니다.')
    cols=st.columns(4)
    for col,label,value in zip(cols,['신규 투자','추가 비용·이자 반영 잔여액','자가노동 차감 후','현재 대비 추가 영업현금'],[investment,r['profit'],r['full_profit'],r['increment']]):col.metric(label,f'{value/10000:,.1f} 만원')
    c1,c2=st.columns(2)
    with c1:
        st.markdown('**자금 조달·회수**')
        st.write(f"차입금 {r['loan']/10000:,.1f}만원 / 첫해 이자 {r['interest']/10000:,.1f}만원 / 연간 원금 {r['principal']/10000:,.1f}만원")
        st.write(f"원리금 차감 후 연간 현금: {r['equity_cash']/10000:,.1f}만원")
        st.write('추가 영업현금 기반 단순 회수: '+(f"{r['payback']:.1f}년" if r['payback'] else '산출 불가 또는 신규 투자 없음'))
        st.caption('정상연도 반복 가정의 단순 회수입니다. 첫해 정착·월별 부족액·할인·세금·재투자·보조금은 미반영이며 원금은 손익에서 차감하지 않습니다.')
    with c2:
        st.markdown('**상담 전 확인**')
        missing=[k for k,v in x['ready'].items() if not v]
        st.write('미확인: '+(' · '.join(missing) if missing else '입력상 모두 확인'))
        st.write(f"농가: {x['farmer']} / 목적: {x['purpose']} / 근거: {x['source']}")
        if x['note']:st.text(x['note'])
    st.markdown('**물량·단가·난방비 동시 시나리오**')
    rows=[]
    for name,qty,price,heat in [('보수',.75,.8,1.25),('기준',1,1,1),('낙관',1.1,1.1,.9)]:
        v=adjusted.copy()
        v['summer_total_yield']*=qty;v['winter_total_yield']*=qty
        v['summer_price']*=price;v['market_price']*=price
        t=core.calculate_profit_summary(v,region)
        t['depreciation']=result['depreciation']
        t['total_annual_profit']=t['summer_revenue']-t['summer_cost']+t['winter_revenue']-t['winter_fuel_cost']*heat-t['depreciation']
        z=decision_metrics(t,investment,x['baseline'],x['extra_cost'],x['own'],x['loan'],x['rate'],x['years'])
        rows.append({'시나리오':name,'물량 배율':qty,'단가 배율':price,'난방비 배율':heat,'자가노동 차감 후(만원)':z['full_profit']/10000,'추가 영업현금(만원)':z['increment']/10000})
    table=pd.DataFrame(rows);st.bar_chart(table.set_index('시나리오')[['자가노동 차감 후(만원)','추가 영업현금(만원)']]);st.dataframe(table,hide_index=True,width='stretch')
    st.caption('배율은 비교용 가정입니다. 생산·가격 예측이 아니며 여름 경영비는 원본의 매출 비율로 함께 변합니다. 추가 운영비는 고정합니다.')
    st.download_button('보완 분석 CSV 다운로드',table.to_csv(index=False).encode('utf-8-sig'),'fig-decision-scenarios.csv','text/csv')
