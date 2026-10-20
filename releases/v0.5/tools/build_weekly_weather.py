"""Build derived profiles without publishing raw hourly observations.
Usage: python tools/build_weekly_weather.py --source "path/to/전남 기상데이터"
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import weekly_weather as weather


def build(source):
    sites = {}
    diagnostics = []
    for path in sorted(source.glob('*/*.csv')):
        if path.name == 'kangin.csv':
            continue  # Converted copy of the same station, not a second source.
        raw = path.read_bytes()
        clean, quality = weather.read_hourly_csv(raw)
        clean = clean[clean.datetime.dt.year.between(2016, 2025)].copy()
        label = path.parent.name.split('(')[0].strip()
        model = weather.fit_weekly_models(clean, label)
        model['quality'] = quality
        model['source_file'] = path.name
        model['source_sha256'] = hashlib.sha256(raw).hexdigest()
        expected = len(pd.date_range('2016-01-01', '2025-12-31 23:00', freq='h'))
        model['period_coverage'] = round(len(clean)/expected, 6)
        model['reference_period'] = '2016–2025'
        sites[label] = model
        winter = clean[clean.datetime.dt.month.isin([11,12,1,2])]
        night = winter[(winter.datetime.dt.hour>=18)|(winter.datetime.dt.hour<8)]
        coeff = np.array([[model['weeks'][str(int(w))][k] for k in ['a','sin','cos']]
                          for w in weather.seasonal_week(night.datetime)])
        hour = night.datetime.dt.hour.to_numpy()
        prediction = coeff[:,0]+coeff[:,1]*np.sin(weather.OMEGA*hour)+coeff[:,2]*np.cos(weather.OMEGA*hour)
        actual = night.temp_mean.to_numpy()
        # Matching observed timestamps avoids conflating model smoothing with missing hours.
        measured_dh = float(np.maximum(15-actual,0).sum())
        model_dh = float(np.maximum(15-prediction,0).sum())
        holdout = clean[clean.datetime.dt.year==2025]
        training = clean[clean.datetime.dt.year<2025]
        past_model = weather.fit_weekly_models(training, label)
        checks = []
        for week in weather.seasonal_week(holdout.datetime):
            checks.append(past_model['weeks'].get(str(int(week))))
        mask = np.array([c is not None for c in checks])
        h = holdout.datetime.dt.hour.to_numpy()[mask]
        c = np.array([[x[k] for k in ['a','sin','cos']] for x in checks if x is not None])
        yhat = c[:,0]+c[:,1]*np.sin(weather.OMEGA*h)+c[:,2]*np.cos(weather.OMEGA*h)
        yrmse = float(np.sqrt(np.mean((holdout.temp_mean.to_numpy()[mask]-yhat)**2)))
        diagnostics.append({'site':label,'start':model['start'],'end':model['end'],'rows':len(clean),
            'coverage':model['period_coverage'],'weeks':len(model['weeks']),
            'winter_night_reference_hours':len(night),'target_temp':15,'start_hour':18,'duration_hours':14,
            'observed_degree_hours':measured_dh,'weekly_curve_degree_hours':model_dh,
            'curve_minus_observed_percent':100*(model_dh/measured_dh-1) if measured_dh else None,
            'holdout_year':2025,'holdout_temperature_rmse':yrmse,'holdout_hours':int(mask.sum())})
        print(label,len(clean),'hours',len(model['weeks']),'weeks',flush=True)
    if len(sites)!=20 or any(len(m['weeks'])!=52 for m in sites.values()):
        raise ValueError('예상한 관측지 20개·각 52주 모형을 확인하세요.')
    data={'schema_version':1,'period':'2016–2025','temperature':'시간별 평균기온 (℃)',
          'calendar_week':'Jan 1–7 = 1; Dec 24–31 = 52; Feb 29 shares Feb 28',
          'site_count':len(sites),'sites':sites}
    (ROOT/'data/weekly_weather.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report={'built_on':'2026-10-21','raw_files_published':False,'reference_period':'2016–2025',
            'training_fit_note':'Each year-hour cell has equal weight in weekly clock-hour means.',
            'diagnostics':diagnostics}
    (ROOT/'data/weekly_weather_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 주별 시간기온 모형 자료 검증','',
           '2016~2025년 시간별 관측자료에서 지역별 계수만 생성했다. 원자료는 수정·게시하지 않았다.',
           '평균기온은 각 시각 행의 평균기온 필드이며 하루 24시간 평균을 반복한 값이 아니다.',
           '같은 날짜·시간은 평균, 무효 날짜·비유한 기온·범위 밖(-60~60℃) 값은 제외했다.',
           '아래 난방도시는 **설정 15℃·18시부터 14시간**의 예시 조건이다. 실제 관측이 존재하는 동일 시각에 대해 대표곡선과 원자료를 비교한다.',
           'RMSE는 2016~2024년으로 적합한 곡선을 2025년 시간기온에 적용한 독립연도 값이다. 난방비 실측 정확도가 아니다.','',
           '| 관측지 | 유효 시간 | 전체기간 관측률 | 주차 수 | 곡선 난방도시 차이 | 2025 기온 RMSE |',
           '|---|---:|---:|---:|---:|---:|']
    for d in diagnostics:
        lines.append(f"| {d['site']} | {d['rows']:,} | {d['coverage']:.1%} | {d['weeks']} | {d['curve_minus_observed_percent']:+.1f}% | {d['holdout_temperature_rmse']:.2f}℃ |")
    lines+=['','주간 함수는 대표적인 하루를 반복하므로 한파와 날씨 변동을 재현하지 않는다. 난방도시 차이는 목표온도·시간대가 달라지면 달라진다.',
            '전체기간 관측률은 모든 지역에 동일하게 2016-01-01~2025-12-31의 시간슬롯을 분모로 사용한다. 강진은 관측 시작이 늦어 낮다.',
            '결측값을 0℃로 채우거나 장기간 선형 보간하지 않았다. 연도별 관측일 수가 다른 경우 해당 연도·시간대의 관측 평균을 먼저 구한다.']
    (ROOT/'docs/WEEKLY_WEATHER_VALIDATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    build(parser.parse_args().source)
