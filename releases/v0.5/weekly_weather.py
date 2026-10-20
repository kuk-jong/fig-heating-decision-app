"""Weekly 24-hour temperature profiles and dimensionally consistent heating loads."""
from functools import lru_cache
from io import StringIO
import json
from pathlib import Path
import numpy as np
import pandas as pd

NIGHT_START_HOUR = 18
NIGHT_DURATION_HOURS = 14
PERIOD_HOURS = 24.0
OMEGA = 2 * np.pi / PERIOD_HOURS


def seasonal_week(dates):
    """Fixed calendar bins: Jan 1-7 is week 1; Dec 24-31 is week 52.
    Feb 29 shares Feb 28's calendar coordinate, avoiding leap-year phase drift.
    """
    dates = pd.DatetimeIndex(pd.to_datetime(dates))
    ref = [pd.Timestamp(2001, d.month, min(d.day, 28) if d.month == 2 else d.day).dayofyear for d in dates]
    return np.minimum((np.asarray(ref) - 1) // 7 + 1, 52)


def clean_hourly(frame):
    time = pd.to_datetime(frame['datetime'], format='mixed', errors='coerce')
    try:
        if time.dt.tz is not None:
            raise ValueError('시간대 없는 한국 현지 시각으로 입력하세요.')
    except AttributeError as exc:
        raise ValueError('날짜·시간 형식을 확인하세요.') from exc
    temp = pd.to_numeric(frame['temp_mean'], errors='coerce')
    valid = time.notna() & np.isfinite(temp) & temp.between(-60, 60)
    clean = pd.DataFrame({'datetime': time[valid], 'temp_mean': temp[valid]})
    if clean.empty:
        raise ValueError('유효한 시간별 평균기온 자료가 없습니다.')
    off_hour = int((clean.datetime.dt.minute.ne(0) | clean.datetime.dt.second.ne(0)).sum())
    clean['datetime'] = clean.datetime.dt.floor('h')
    duplicates = int(clean.datetime.duplicated().sum())
    clean = clean.groupby('datetime', as_index=False).temp_mean.mean().sort_values('datetime')
    return clean, {'input_rows': len(frame), 'invalid_rows': int((~valid).sum()),
                   'merged_rows': duplicates, 'subhour_rows': off_hour}


def read_hourly_csv(raw):
    text = None
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeError:
            continue
    if text is None:
        raise ValueError('CSV 인코딩은 UTF-8 또는 CP949이어야 합니다.')
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines[:20]) if '날짜' in line and '평균기온' in line), None)
    if header is not None:
        frame = pd.read_csv(StringIO(text), skiprows=header, dtype=str)
        frame = frame.rename(columns={'날짜': 'datetime', '평균기온': 'temp_mean'})
    else:
        frame = pd.read_csv(StringIO(text), dtype=str).rename(columns={'date': 'datetime'})
    if not {'datetime', 'temp_mean'}.issubset(frame.columns):
        raise ValueError('시간별 CSV에 날짜·평균기온 또는 datetime·temp_mean 컬럼이 필요합니다. 일최저기온 CSV는 사용할 수 없습니다.')
    if 'region' in frame and frame.region.dropna().nunique() > 1:
        raise ValueError('업로드 CSV는 한 관측지의 자료만 포함해야 합니다.')
    clean, quality = clean_hourly(frame[['datetime', 'temp_mean']])
    if 'region' in frame and not frame.region.dropna().empty:
        quality['declared_region'] = str(frame.region.dropna().iloc[0]).strip()
    return clean, quality


def fit_weekly_models(clean, label):
    x = clean.copy()
    x['year'] = x.datetime.dt.year
    x['week'] = seasonal_week(x.datetime)
    x['hour'] = x.datetime.dt.hour
    weeks = {}
    for week, group in x.groupby('week'):
        counts = group.groupby('hour').size().reindex(range(24), fill_value=0)
        if counts.min() < 3:
            continue
        # Give each year's observed cell mean equal weight, rather than letting
        # a better-observed year dominate a particular clock hour.
        cells = group.groupby(['year', 'hour']).temp_mean.mean().groupby('hour').mean().reindex(range(24))
        design = np.column_stack([np.ones(24), np.sin(OMEGA*np.arange(24)), np.cos(OMEGA*np.arange(24))])
        coeff = np.linalg.lstsq(design, cells.to_numpy(), rcond=None)[0]
        pred = design @ coeff
        weeks[str(int(week))] = {'a': float(coeff[0]), 'sin': float(coeff[1]), 'cos': float(coeff[2]),
            'amplitude': float(np.hypot(coeff[1], coeff[2])),
            'phase': float(np.arctan2(coeff[2], coeff[1])),
            'rmse_hourly_means': float(np.sqrt(np.mean((cells.to_numpy()-pred)**2))),
            'hours_mean': [round(float(t), 5) for t in cells], 'hour_counts': [int(n) for n in counts],
            'years': sorted(map(int, group.year.unique()))}
    if not weeks:
        raise ValueError('각 시간대에 최소 3개 관측값을 갖춘 주간 자료가 없습니다. 여러 날의 24시간 자료를 제공하세요.')
    return {'label': label, 'county': label.split()[0], 'source': 'hourly_observations',
            'start': str(x.datetime.min()), 'end': str(x.datetime.max()), 'rows': len(x),
            'years': sorted(map(int, x.year.unique())), 'weeks': weeks}


@lru_cache(maxsize=1)
def load_catalog():
    return json.loads((Path(__file__).parent/'data'/'weekly_weather.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=2)
def model_from_upload(raw, label):
    clean, quality = read_hourly_csv(raw)
    declared = quality.get('declared_region')
    if declared and declared.split()[0] != label.split()[0]:
        raise ValueError('CSV에 표시된 지역과 선택한 관측지의 시군이 다릅니다.')
    model = fit_weekly_models(clean, label)
    model['quality'] = quality
    model['source'] = 'uploaded_hourly_observations'
    return model


def hourly_temperatures(model, dates, hours):
    dates = pd.DatetimeIndex(dates)
    hours = np.asarray(hours, dtype=int)
    if len(set(hours.tolist())) != len(hours) or np.any((hours < 0) | (hours > 23)):
        raise ValueError('가온 시간은 중복 없는 0~23시이어야 합니다.')
    predictions = np.empty((len(dates), len(hours)))
    for week in np.unique(seasonal_week(dates)):
        coeff = model['weeks'].get(str(int(week)))
        if coeff is None:
            raise ValueError(f'{int(week)}주차의 시간별 관측자료가 부족합니다. 다른 자료를 선택하세요.')
        values = coeff['a'] + coeff['sin']*np.sin(OMEGA*hours) + coeff['cos']*np.cos(OMEGA*hours)
        predictions[seasonal_week(dates) == week, :] = values
    return predictions


def heating_energy(model, dates, start_hour, duration_hours, target_temp, surface_area, u_value,
                   airtightness_factor, wind_factor):
    """One-hour bins; U is W/(m2 K). Returns useful heat in kWh, peak kW, hours/day.
    Each row is a calendar day. Across-midnight windows include that date's 00-07
    and 18-23 bins, so seasonal/week boundaries use the correct date's function.
    """
    if not (0 <= start_hour <= 23 and 0 <= duration_hours <= 24):
        raise ValueError('시작 시각 0~23시, 가온 가능시간 0~24시간을 지정하세요.')
    hours = (int(start_hour) + np.arange(int(duration_hours))) % 24
    if len(hours) == 0 or len(dates) == 0:
        return {'heat_kwh': 0.0, 'peak_kw': 0.0, 'heating_hours_per_day': 0.0}
    temperatures = hourly_temperatures(model, dates, hours)
    delta = np.maximum(float(target_temp)-temperatures, 0)
    load_kw = float(surface_area)*float(u_value)*delta*float(airtightness_factor)*float(wind_factor)/1000
    return {'heat_kwh': float(load_kw.sum()), 'peak_kw': float(load_kw.max()),
            'heating_hours_per_day': float((delta > 0).sum()/len(dates))}
