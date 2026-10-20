import json
from io import BytesIO
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import weekly_weather as w


def model(a=0, sine=0, cosine=0):
    return {'weeks':{str(i):{'a':a,'sin':sine,'cos':cosine} for i in range(1,53)}}


class WeeklyWeatherTests(unittest.TestCase):
    def test_calendar_week_leap_and_year_boundaries(self):
        values=w.seasonal_week(['2024-01-01','2025-01-07','2025-01-08','2024-02-29','2025-02-28','2025-12-31'])
        self.assertEqual(values.tolist(),[1,1,2,9,9,52])

    def test_fit_restores_daily_wave(self):
        dates=pd.date_range('2024-01-01',periods=7*24,freq='h')
        temp=8+3*np.sin(w.OMEGA*dates.hour)+2*np.cos(w.OMEGA*dates.hour)
        m=w.fit_weekly_models(pd.DataFrame({'datetime':dates,'temp_mean':temp}),'해남군 시험지')
        c=m['weeks']['1']
        self.assertAlmostEqual(c['a'],8)
        self.assertAlmostEqual(c['sin'],3)
        self.assertAlmostEqual(c['cos'],2)
        self.assertLess(c['rmse_hourly_means'],1e-10)

    def test_week_changes_at_date_boundary(self):
        m=model(1);m['weeks']['2']['a']=9
        t=w.hourly_temperatures(m,pd.to_datetime(['2025-01-07','2025-01-08']),[0,23])
        np.testing.assert_allclose(t,[[1,1],[9,9]])

    def test_positive_degree_hours_do_not_cancel_warm_hours(self):
        m=model(10,cosine=10)
        t=w.hourly_temperatures(m,pd.date_range('2025-01-01',periods=1),range(24))
        expected=float(np.maximum(10-t,0).sum())
        result=w.heating_energy(m,pd.date_range('2025-01-01',periods=1),0,24,10,1000,1,1,1)
        self.assertGreater(expected,0)
        self.assertAlmostEqual(result['heat_kwh'],expected)
        self.assertAlmostEqual(result['peak_kw'],10)

    def test_night_window_and_physical_units(self):
        dates=pd.date_range('2025-01-01',periods=2)
        # 100 m2 * 2 W/(m2 K) * 5 K = 1000 W = 1 kW.
        r=w.heating_energy(model(5),dates,18,14,10,100,2,1,1)
        self.assertAlmostEqual(r['heat_kwh'],28)
        self.assertAlmostEqual(r['peak_kw'],1)
        self.assertAlmostEqual(r['heating_hours_per_day'],14)
        r=w.heating_energy(model(5,cosine=2),dates,18,14,10,100,2,1,1)
        hours=np.r_[np.arange(18,24),np.arange(0,8)]
        expected=float(np.sum(.2*(10-(5+2*np.cos(w.OMEGA*hours))))*2)
        self.assertAlmostEqual(r['heat_kwh'],expected)

    def test_zero_hours_and_warm_conditions(self):
        dates=pd.date_range('2025-01-01',periods=1)
        self.assertEqual(w.heating_energy(model(0),dates,18,0,10,100,2,1,1)['heat_kwh'],0)
        self.assertEqual(w.heating_energy(model(20),dates,18,14,10,100,2,1,1)['heat_kwh'],0)

    def test_missing_week_and_invalid_schedule_are_errors(self):
        with self.assertRaises(ValueError):w.hourly_temperatures({'weeks':{}},pd.date_range('2025-01-01',periods=1),[0])
        with self.assertRaises(ValueError):w.heating_energy(model(),pd.date_range('2025-01-01',periods=1),18,25,10,1,1,1,1)

    def test_korean_header_cp949_and_duplicate_cleaning(self):
        raw='기간별조회,,,\n농업기상,,,\n날짜,평균기온,최고기온,최저기온\n(년-월-일 시:분),( ℃ ),( ℃ ),( ℃ )\n2024-01-01 0:00,1,2,0\n2024-01-01 0:00,3,4,0\n2024-01-01 1:00,-,4,0\n'
        clean,q=w.read_hourly_csv(raw.encode('cp949'))
        self.assertEqual(len(clean),1)
        self.assertEqual(clean.temp_mean.iloc[0],2)
        self.assertEqual(q['merged_rows'],1)
        self.assertEqual(q['invalid_rows'],2)

    def test_daily_minimum_upload_cannot_be_misread_as_hourly(self):
        with self.assertRaises(ValueError):w.read_hourly_csv(b'date,min_temp\n2024-01-01,1')
        with self.assertRaises(ValueError):w.fit_weekly_models(pd.DataFrame({'datetime':pd.date_range('2024-01-01',periods=10),'temp_mean':range(10)}),'test')

    def test_each_year_has_equal_weight_in_hourly_means(self):
        a=pd.date_range('2023-01-01',periods=7*24,freq='h')
        b=pd.date_range('2024-01-01',periods=3*24,freq='h')
        x=pd.DataFrame({'datetime':a.append(b),'temp_mean':np.r_[np.zeros(len(a)),np.full(len(b),10)]})
        m=w.fit_weekly_models(x,'test')
        self.assertAlmostEqual(m['weeks']['1']['a'],5)

    def test_fuel_cost_units_and_electric_basic_charge(self):
        import ast, math
        tree=ast.parse((ROOT/'original_app.py').read_text(encoding='utf-8'))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) or isinstance(n,ast.Assign) and all(isinstance(t,ast.Name) for t in n.targets)]
        ns={'np':np,'pd':pd,'math':math,'weekly_weather':w}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<core>','exec'),ns)
        args=dict(surface_area=1000,u_val=2,target_temp=10,unit_fuel_cost=65.9,energy_source='농사용 전기',
                  climate_model={'model':model(5),'start_hour':18,'duration_hours':14,'winter_start_year':2026},
                  winter_total_yield=0,market_price=30000,airtightness_factor=1,side_wing_factor_value=1)
        revenue,cost,hours=ns['weekly_winter_analysis'](**args)
        # App wrapper uses all 24 hours even when old session values say 14.
        self.assertEqual(cost,int(28800/.98*65.9+10/.98*1150*4))
        self.assertEqual(hours,24)
        args.update(energy_source='면세유(경유)',unit_fuel_cost=1100)
        self.assertEqual(ns['weekly_winter_analysis'](**args)[1],int(28800/(8500/860*.85)*1100))
        args['climate_model']['winter_start_year']=2027
        self.assertEqual(ns['weekly_winter_analysis'](**args)[1],int(29040/(8500/860*.85)*1100))

    def test_upload_declared_county_must_match(self):
        csv=b'region,datetime,temp_mean\nother,2024-01-01 00:00,1'
        with self.assertRaises(ValueError):w.model_from_upload(csv,'해남군 옥천면')

    def test_bundled_stations_have_complete_annual_models(self):
        catalog=w.load_catalog()
        self.assertEqual(catalog['site_count'],20)
        for m in catalog['sites'].values():
            self.assertEqual(len(m['weeks']),52)
            self.assertTrue(all(min(c['hour_counts'])>=3 for c in m['weeks'].values()))
            t=w.hourly_temperatures(m,pd.date_range('2026-11-01','2027-02-28'),range(24))
            self.assertTrue(np.isfinite(t).all())

if __name__=='__main__':unittest.main()
