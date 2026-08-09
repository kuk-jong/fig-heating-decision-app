import base64
import math
import os

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="전남 무화과 경영 분석기", layout="wide")


REGION_DATA = {
    "영암군 (무화과 주산지)": {"base": 2.0, "amp": 8.0},
    "해남군": {"base": 2.2, "amp": 7.8},
    "목포시": {"base": 2.5, "amp": 7.5},
    "신안군": {"base": 3.0, "amp": 7.0},
    "진도군": {"base": 3.2, "amp": 6.8},
    "완도군": {"base": 3.5, "amp": 6.5},
    "무안군": {"base": 1.5, "amp": 8.2},
    "강진군": {"base": 2.0, "amp": 8.0},
    "장흥군": {"base": 1.8, "amp": 8.2},
    "여수시": {"base": 3.0, "amp": 7.0},
    "순천시": {"base": 1.5, "amp": 8.5},
    "광양시": {"base": 2.0, "amp": 8.0},
    "고흥군": {"base": 2.8, "amp": 7.2},
    "보성군": {"base": 1.0, "amp": 8.5},
    "나주시": {"base": 0.5, "amp": 9.0},
    "담양군": {"base": -0.5, "amp": 9.5},
    "곡성군": {"base": -1.0, "amp": 10.0},
    "구례군": {"base": -0.5, "amp": 9.8},
    "화순군": {"base": -1.0, "amp": 9.8},
    "장성군": {"base": -0.5, "amp": 9.5},
    "함평군": {"base": 1.0, "amp": 8.8},
    "영광군": {"base": 1.0, "amp": 8.8},
}

U_VALUES = {
    "비닐 1겹 (U=5.5)": 5.5,
    "비닐 2겹 (U=4.5)": 4.5,
    "다겹보온커튼 (U=2.0)": 2.0,
    "고효율 패키지 (U=1.5)": 1.5,
}

FUEL_SETTINGS = {
    "면세유(경유)": {"efficiency": 0.85, "calorific": 8500, "default_unit_cost": 1100},
    "농사용 전기": {"efficiency": 0.98, "calorific": 860, "default_unit_cost": 50},
}

AIR_TIGHTNESS_LEVELS = {
    "매우 우수 (누기 적음, 0.90)": 0.90,
    "양호 (표준, 1.00)": 1.00,
    "보통 (약간 누기, 1.10)": 1.10,
    "취약 (누기 많음, 1.25)": 1.25,
    "매우 취약 (보수적, 1.40)": 1.40,
}

SIDE_WING_LEVELS = {
    "없음 (노출, 1.00)": 1.00,
    "한쪽 방풍벽 (0.97)": 0.97,
    "양쪽 방풍벽 (표준, 0.94)": 0.94,
    "양쪽 방풍벽+보강 (0.90)": 0.90,
}

DEFAULT_GREENHOUSE = {
    "span_count": 3,
    "gh_width": 8.0,
    "gh_length": 42.0,
    "gh_side_h": 2.5,
    "gh_ridge_h": 4.0,
}

BASE_INVESTMENT_AREA_PYEONG = 300.0
BASE_INVESTMENT_AREA_M2 = BASE_INVESTMENT_AREA_PYEONG * 3.3
BASE_INVESTMENT_10K_WON = {
    "double_vinyl_construction": 957,
    "thermal_curtain_construction": 840,
    "double_vinyl_material": 24,
    "thermal_curtain_material": 248,
}

WINTER_START = "2025-11-01"
WINTER_END = "2026-02-28"
WINTER_MONTHS = {11, 12, 1, 2}


def get_password() -> str:
    try:
        password = st.secrets.get("APP_PASSWORD", None)
    except Exception:
        password = None
    return password or os.getenv("APP_PASSWORD", "1234")


def require_login() -> None:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return

    st.title("🔒 접근 제한 구역입니다.")
    st.markdown("과수연구소 관계자 외 접근금지")
    st.write("이 시스템은 허가된 사용자만 이용할 수 있습니다.")

    password_input = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if password_input == get_password():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")

    st.stop()


def greenhouse_surface_area(
    gh_width: float,
    gh_length: float,
    gh_side_h: float,
    gh_ridge_h: float,
    span_count: int,
) -> float:
    roof_height = max(gh_ridge_h - gh_side_h, 0)
    roof_curve_len = arch_roof_length(gh_width, roof_height)

    area_roof = roof_curve_len * gh_length * span_count
    area_side = 2 * gh_length * gh_side_h
    one_end_wall = (gh_width * gh_side_h) + ((2 / 3) * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count
    return area_roof + area_side + area_end


def arch_roof_length(width: float, roof_height: float, segments: int = 24) -> float:
    if roof_height <= 0:
        return width

    xs = np.linspace(-width / 2, width / 2, segments + 1)
    ys = roof_height * (1 - (xs / (width / 2)) ** 2)
    return float(np.sum(np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2)))


def side_wing_factor(side_wing_level: str, side_wing_width: float) -> float:
    base_factor = SIDE_WING_LEVELS.get(side_wing_level, 1.0)
    if base_factor >= 1.0:
        return 1.0

    width_ratio = min(max(side_wing_width, 0.0) / 1.5, 1.5)
    benefit = (1.0 - base_factor) * width_ratio
    return max(1.0 - benefit, 0.85)


def greenhouse_svg(
    gh_width: float,
    gh_length: float,
    gh_side_h: float,
    gh_ridge_h: float,
    span_count: int,
    side_wing_level: str,
    side_wing_width: float,
    insul_type: str,
    cost_curtain: float,
) -> str:
    roof_height = max(gh_ridge_h - gh_side_h, 0.1)
    svg_width = 560
    svg_height = 280
    base_y = 218
    side_top_y = 160
    ridge_y = max(48, side_top_y - roof_height * 62)
    house_left = 74
    house_right = 486
    house_width = house_right - house_left
    house_mid = (house_left + house_right) / 2
    span_count = max(int(span_count), 1)
    span_label = "1동" if span_count == 1 else f"{span_count}연동"
    total_width = gh_width * span_count
    span_width = house_width / span_count
    wing_factor = side_wing_factor(side_wing_level, side_wing_width)
    wing_px = min(max(side_wing_width, 0), 3.0) * 28
    cover_label = insul_type.split(" (", 1)[0]
    curtain_label = "다겹보온커튼 포함" if "커튼" in insul_type or cost_curtain > 0 else "보온커튼 미반영"

    wall_panels = ""
    roof_svg = ""
    valley_lines = ""
    rib_lines = ""
    for idx in range(span_count):
        x1 = house_left + span_width * idx
        x2 = x1 + span_width
        mid_x = (x1 + x2) / 2
        wall_panels += f"""
  <rect x="{x1:.1f}" y="{side_top_y:.1f}" width="{span_width:.1f}" height="{base_y - side_top_y:.1f}" fill="#bfdbfe" opacity="0.38" stroke="#60a5fa" stroke-width="1.4" />
"""
        roof_svg += f"""
  <path d="M {x1:.1f} {side_top_y:.1f} Q {mid_x:.1f} {ridge_y:.1f} {x2:.1f} {side_top_y:.1f}" fill="none" stroke="#0f6f95" stroke-width="7" stroke-linecap="round" />
  <path d="M {x1:.1f} {side_top_y:.1f} Q {mid_x:.1f} {ridge_y:.1f} {x2:.1f} {side_top_y:.1f}" fill="none" stroke="#e0f2fe" stroke-width="3" stroke-linecap="round" opacity="0.85" />
"""
        for rib_idx in range(1, 5):
            t = rib_idx / 5
            rib_x = x1 + span_width * t
            roof_y = (1 - t) ** 2 * side_top_y + 2 * (1 - t) * t * ridge_y + t**2 * side_top_y
            rib_lines += f'<line x1="{rib_x:.1f}" y1="{roof_y + 3:.1f}" x2="{rib_x:.1f}" y2="{base_y:.1f}" stroke="#38bdf8" stroke-width="1.6" opacity="0.52" />'

    if span_count > 1:
        for idx in range(1, span_count):
            x = house_left + span_width * idx
            valley_lines += f"""
  <path d="M {x:.1f} {side_top_y - 1:.1f} L {x:.1f} {base_y:.1f}" stroke="#475569" stroke-width="2.6" opacity="0.62" />
  <path d="M {x - 12:.1f} {side_top_y - 2:.1f} Q {x:.1f} {side_top_y + 14:.1f} {x + 12:.1f} {side_top_y - 2:.1f}" fill="none" stroke="#94a3b8" stroke-width="4" stroke-linecap="round" />
"""

    wing_svg = ""
    if wing_factor < 1.0:
        left_outer = house_left - wing_px
        right_outer = house_right + wing_px
        left_wing = f"""
  <path d="M {house_left:.1f} {side_top_y:.1f} Q {house_left - wing_px * 0.55:.1f} {side_top_y + 34:.1f} {left_outer:.1f} {base_y:.1f} L {house_left:.1f} {base_y:.1f} Z" fill="#bae6fd" stroke="#0284c7" stroke-width="2.8" opacity="0.78" />
  <path d="M {house_left:.1f} {side_top_y:.1f} Q {house_left - wing_px * 0.55:.1f} {side_top_y + 34:.1f} {left_outer:.1f} {base_y:.1f}" fill="none" stroke="#0369a1" stroke-width="5" stroke-linecap="round" />
"""
        right_wing = f"""
  <path d="M {house_right:.1f} {side_top_y:.1f} Q {house_right + wing_px * 0.55:.1f} {side_top_y + 34:.1f} {right_outer:.1f} {base_y:.1f} L {house_right:.1f} {base_y:.1f} Z" fill="#bae6fd" stroke="#0284c7" stroke-width="2.8" opacity="0.78" />
  <path d="M {house_right:.1f} {side_top_y:.1f} Q {house_right + wing_px * 0.55:.1f} {side_top_y + 34:.1f} {right_outer:.1f} {base_y:.1f}" fill="none" stroke="#0369a1" stroke-width="5" stroke-linecap="round" />
"""
        if side_wing_level.startswith("한쪽"):
            right_wing = ""
        wing_svg = f"""
  {left_wing}
  {right_wing}
  <text x="{house_mid}" y="52" text-anchor="middle" font-size="12" fill="#475569">방풍벽: {side_wing_level}, {side_wing_width:g}m</text>
"""

    svg_markup = f"""
<svg viewBox="0 0 {svg_width} {svg_height}" width="100%" height="280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="온실 개략도">
  <rect width="{svg_width}" height="{svg_height}" fill="#f8fafc" rx="8" />
  {wing_svg}
  {wall_panels}
  {roof_svg}
  {rib_lines}
  {valley_lines}
  <line x1="38" y1="{base_y}" x2="522" y2="{base_y}" stroke="#334155" stroke-width="2.6" />
  <line x1="{house_left}" y1="{side_top_y}" x2="{house_left}" y2="{base_y}" stroke="#0f6f95" stroke-width="3" />
  <line x1="{house_right}" y1="{side_top_y}" x2="{house_right}" y2="{base_y}" stroke="#0f6f95" stroke-width="3" />
  <text x="{house_mid}" y="28" text-anchor="middle" font-size="17" font-weight="700" fill="#0f172a">온실 개략도</text>
  <text x="{house_mid}" y="250" text-anchor="middle" font-size="14" font-weight="700" fill="#334155">1동 폭 {gh_width:g}m / 전체 온실 폭 {total_width:g}m / 온실 길이 {gh_length:g}m / {span_label}</text>
  <text x="{house_mid}" y="272" text-anchor="middle" font-size="13" fill="#475569">피복/보온: {cover_label}, {curtain_label}</text>
  <line x1="50" y1="{side_top_y}" x2="50" y2="{base_y}" stroke="#475569" stroke-width="2" marker-start="url(#arrowUp)" marker-end="url(#arrowDown)" />
  <line x1="515" y1="{ridge_y}" x2="515" y2="{base_y}" stroke="#475569" stroke-width="2" marker-start="url(#arrowUp)" marker-end="url(#arrowDown)" />
  <text x="34" y="{(base_y + side_top_y) / 2:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="#334155" transform="rotate(-90 34 {(base_y + side_top_y) / 2:.1f})">측고 {gh_side_h:g}m</text>
  <text x="535" y="{(base_y + ridge_y) / 2:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="#334155" transform="rotate(-90 535 {(base_y + ridge_y) / 2:.1f})">동고(최고높이) {gh_ridge_h:g}m</text>
  <defs>
    <marker id="arrowUp" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M4,0 L8,8 L0,8 Z" fill="#475569" />
    </marker>
    <marker id="arrowDown" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,0 L4,8 Z" fill="#475569" />
    </marker>
  </defs>
</svg>
"""
    encoded_svg = base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    return (
        '<img alt="온실 개략도" '
        f'src="data:image/svg+xml;base64,{encoded_svg}" '
        'style="width:100%; max-width:760px; height:auto; display:block; margin:0 auto;" />'
    )


def annual_depreciation_won(
    cost_film: float,
    cost_curtain: float,
    cost_heater: float,
    cost_facility: float,
) -> int:
    annual_cost_10k_won = cost_film / 10 + cost_curtain / 10 + cost_heater / 3 + cost_facility / 5
    return int(annual_cost_10k_won * 10000)


def scaled_investment_defaults_10k(floor_area_m2: float) -> dict:
    scale = max(floor_area_m2, 0.0) / BASE_INVESTMENT_AREA_M2
    return {key: int(round(value * scale)) for key, value in BASE_INVESTMENT_10K_WON.items()}


def simulated_min_temp(base_t: float, amp_t: float, day_idx: int, days_total: int) -> float:
    return base_t - (amp_t * np.sin(np.pi * day_idx / days_total))


def climate_params_from_csv(uploaded_file, region_name: str) -> tuple[dict | None, str | None]:
    if uploaded_file is None:
        return None, None

    required_columns = {"region", "date", "min_temp"}
    try:
        climate_df = pd.read_csv(uploaded_file)
    except Exception as exc:
        return None, f"CSV 파일을 읽지 못했습니다: {exc}"

    missing_columns = required_columns - set(climate_df.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return None, f"CSV 필수 컬럼이 없습니다: {missing_text}"

    climate_df["date"] = pd.to_datetime(climate_df["date"], errors="coerce")
    climate_df["min_temp"] = pd.to_numeric(climate_df["min_temp"], errors="coerce")
    climate_df = climate_df.dropna(subset=["date", "min_temp"])
    climate_df = climate_df[climate_df["date"].dt.month.isin(WINTER_MONTHS)]

    region_df = climate_df[climate_df["region"] == region_name]
    if region_df.empty:
        return None, f"CSV에서 선택 지역 '{region_name}'의 겨울철 자료를 찾지 못했습니다."

    monthly_min = region_df.groupby(region_df["date"].dt.month)["min_temp"].mean()
    base_t = float(monthly_min.mean())
    amp_t = float(max((monthly_min.max() - monthly_min.min()) / 2, 0.1))
    years = region_df["date"].dt.year.nunique()

    return {"base": base_t, "amp": amp_t, "years": int(years), "rows": int(len(region_df))}, None


def winter_analysis(
    surface_area: float,
    u_val: float,
    target_temp: float,
    unit_fuel_cost: float,
    energy_source: str,
    region_base: float,
    region_amp: float,
    winter_total_yield: float,
    market_price: float,
    airtightness_factor: float,
    side_wing_factor_value: float,
) -> tuple[int, int, float]:
    dates = pd.date_range(WINTER_START, WINTER_END)
    days_total = len(dates)
    fuel = FUEL_SETTINGS[energy_source]
    daily_base_yield = winter_total_yield / days_total if days_total else 0

    winter_revenue = 0.0
    winter_fuel_cost = 0.0
    total_heating_hours = 0.0

    for day_idx, date in enumerate(dates):
        min_temp = simulated_min_temp(region_base, region_amp, day_idx, days_total)
        delta_t = max(target_temp - min_temp, 0)
        heating_hours = 14 if delta_t > 0 else 0
        daily_load = surface_area * u_val * delta_t * heating_hours * airtightness_factor * side_wing_factor_value
        needed_energy = daily_load / (fuel["calorific"] * fuel["efficiency"])
        winter_fuel_cost += needed_energy * unit_fuel_cost
        total_heating_hours += heating_hours

        season_factor = 1.0
        if date.month == 1:
            season_factor = 0.8
        elif date.month in (11, 2):
            season_factor = 1.1
        winter_revenue += daily_base_yield * season_factor * market_price

    avg_heating_hours = total_heating_hours / days_total if days_total else 0
    return int(winter_revenue), int(winter_fuel_cost), avg_heating_hours


def calculate_profit_summary(values: dict, region_info: dict) -> dict:
    surface_area = greenhouse_surface_area(
        values["gh_width"],
        values["gh_length"],
        values["gh_side_h"],
        values["gh_ridge_h"],
        values["span_count"],
    )
    winter_enabled = values.get("winter_enabled", True)
    depreciation = 0
    winter_revenue = 0
    winter_fuel_cost = 0
    avg_heating_hours = 0.0
    if winter_enabled:
        depreciation = annual_depreciation_won(
            values["cost_film"],
            values["cost_curtain"],
            values["cost_heater"],
            values["cost_facility"],
        )
        winter_revenue, winter_fuel_cost, avg_heating_hours = winter_analysis(
            surface_area=surface_area,
            u_val=U_VALUES[values["insul_type"]],
            target_temp=values["target_temp"],
            unit_fuel_cost=values["unit_fuel_cost"],
            energy_source=values["energy_source"],
            region_base=region_info["base"],
            region_amp=region_info["amp"],
            winter_total_yield=values["winter_total_yield"],
            market_price=values["market_price"],
            airtightness_factor=AIR_TIGHTNESS_LEVELS[values["airtightness_level"]],
            side_wing_factor_value=side_wing_factor(values["side_wing_level"], values["side_wing_width"]),
        )

    summer_revenue = values["summer_total_yield"] * values["summer_price"]
    summer_cost = summer_revenue * (values["summer_cost_ratio"] / 100)
    summer_net_profit = summer_revenue - summer_cost
    winter_net_profit = winter_revenue - winter_fuel_cost - depreciation

    return {
        "floor_area_m2": values["gh_width"] * values["gh_length"] * values["span_count"],
        "surface_area": surface_area,
        "depreciation": depreciation,
        "winter_revenue": winter_revenue,
        "winter_fuel_cost": winter_fuel_cost,
        "avg_heating_hours": avg_heating_hours,
        "winter_net_profit": winter_net_profit,
        "summer_revenue": summer_revenue,
        "summer_cost": summer_cost,
        "summer_net_profit": summer_net_profit,
        "total_annual_revenue": summer_revenue + winter_revenue,
        "total_annual_profit": summer_net_profit + winter_net_profit,
    }


def sensitivity_table(values: dict, region_info: dict, variable: str) -> pd.DataFrame:
    records = []

    if variable == "target_temp":
        scenario_values = range(8, 23, 2)
        for target_temp in scenario_values:
            scenario = values.copy()
            scenario["target_temp"] = target_temp
            summary = calculate_profit_summary(scenario, region_info)
            records.append(
                {
                    "시나리오": f"{target_temp}℃",
                    "겨울 난방비(만원)": summary["winter_fuel_cost"] / 10000,
                    "겨울 순이익(만원)": summary["winter_net_profit"] / 10000,
                    "연간 순이익(만원)": summary["total_annual_profit"] / 10000,
                }
            )

    elif variable == "fuel_cost":
        for rate in [0.8, 0.9, 1.0, 1.1, 1.2]:
            scenario = values.copy()
            scenario["unit_fuel_cost"] = int(values["unit_fuel_cost"] * rate)
            summary = calculate_profit_summary(scenario, region_info)
            records.append(
                {
                    "시나리오": f"{int((rate - 1) * 100):+d}%",
                    "연료 단가(원)": scenario["unit_fuel_cost"],
                    "겨울 난방비(만원)": summary["winter_fuel_cost"] / 10000,
                    "겨울 순이익(만원)": summary["winter_net_profit"] / 10000,
                    "연간 순이익(만원)": summary["total_annual_profit"] / 10000,
                }
            )

    elif variable == "insulation":
        for insul_type in U_VALUES:
            scenario = values.copy()
            scenario["insul_type"] = insul_type
            summary = calculate_profit_summary(scenario, region_info)
            records.append(
                {
                    "시나리오": insul_type,
                    "U값": U_VALUES[insul_type],
                    "겨울 난방비(만원)": summary["winter_fuel_cost"] / 10000,
                    "겨울 순이익(만원)": summary["winter_net_profit"] / 10000,
                    "연간 순이익(만원)": summary["total_annual_profit"] / 10000,
                }
            )

    elif variable == "airtightness":
        for airtightness_level in AIR_TIGHTNESS_LEVELS:
            scenario = values.copy()
            scenario["airtightness_level"] = airtightness_level
            summary = calculate_profit_summary(scenario, region_info)
            records.append(
                {
                    "시나리오": airtightness_level,
                    "기밀도 계수": AIR_TIGHTNESS_LEVELS[airtightness_level],
                    "겨울 난방비(만원)": summary["winter_fuel_cost"] / 10000,
                    "겨울 순이익(만원)": summary["winter_net_profit"] / 10000,
                    "연간 순이익(만원)": summary["total_annual_profit"] / 10000,
                }
            )

    elif variable == "side_wing":
        for side_wing_level in SIDE_WING_LEVELS:
            scenario = values.copy()
            scenario["side_wing_level"] = side_wing_level
            summary = calculate_profit_summary(scenario, region_info)
            records.append(
                {
                    "시나리오": side_wing_level,
                    "방풍벽 계수": side_wing_factor(side_wing_level, values["side_wing_width"]),
                    "겨울 난방비(만원)": summary["winter_fuel_cost"] / 10000,
                    "겨울 순이익(만원)": summary["winter_net_profit"] / 10000,
                    "연간 순이익(만원)": summary["total_annual_profit"] / 10000,
                }
            )

    return pd.DataFrame(records)


def normalize_inputs(values: dict) -> dict:
    normalized = values.copy()
    normalized.setdefault("side_wing_level", "양쪽 방풍벽 (표준, 0.94)")
    normalized.setdefault("side_wing_width", 1.5)
    normalized.setdefault("airtightness_level", "양호 (표준, 1.00)")
    normalized.setdefault("insul_type", "비닐 2겹 (U=4.5)")
    normalized.setdefault("energy_source", "면세유(경유)")
    normalized.setdefault("winter_enabled", True)
    return normalized


def collect_inputs() -> tuple[bool, dict]:
    with st.sidebar:
        with st.form(key="input_form"):
            st.header("📝 데이터 입력")
            st.info("데이터 입력 후 맨 아래 버튼을 누르세요.")

            with st.expander("0. 지역 선택", expanded=True):
                region_name = st.selectbox("전남 시·군 선택", list(REGION_DATA.keys()))

            with st.expander("1. 온실 규격", expanded=False):
                span_count = st.number_input(
                    "연동 수",
                    value=DEFAULT_GREENHOUSE["span_count"],
                    step=1,
                    min_value=1,
                    help="1이면 단동, 2 이상이면 연동 온실로 자동 해석합니다.",
                )
                gh_width = st.number_input(
                    "1동 기준 폭 (m)", value=DEFAULT_GREENHOUSE["gh_width"], step=0.5, min_value=1.0
                )
                gh_length = st.number_input("길이 (m)", value=DEFAULT_GREENHOUSE["gh_length"], step=1.0, min_value=1.0)
                gh_side_h = st.number_input("측고 (m)", value=DEFAULT_GREENHOUSE["gh_side_h"], step=0.2, min_value=0.5)
                gh_ridge_h = st.number_input(
                    "동고(최고높이) (m)", value=DEFAULT_GREENHOUSE["gh_ridge_h"], step=0.2, min_value=0.5
                )
                side_wing_level = st.selectbox(
                    "방풍벽",
                    list(SIDE_WING_LEVELS.keys()),
                    index=2,
                    help="온실 양쪽 사이드에 설치되는 방풍벽입니다. 표준은 양쪽 약 1.5m로 가정합니다.",
                )
                side_wing_width = st.number_input(
                    "방풍벽 폭 (m)",
                    value=1.5,
                    step=0.1,
                    min_value=0.0,
                    help="보통 온실 폭 양 사이드에 약 1.5m 방풍벽이 있는 경우가 많습니다.",
                )
                floor_area_m2 = gh_width * gh_length * span_count
                st.caption(f"온실면적: {floor_area_m2:,.0f} ㎡ / 약 {floor_area_m2 / 3.3:,.1f} 평")

            with st.expander("2. 연간 생산 계획", expanded=False):
                st.markdown("**🌞 여름 작기**")
                summer_total_yield = st.number_input("여름 총 생산량 (kg)", value=3000, step=100, min_value=0)
                summer_price = st.number_input("여름 평균 단가 (원/kg)", value=6000, step=500, min_value=0)
                summer_cost_ratio = st.slider(
                    "여름철 경영비 비율 (%)",
                    10,
                    80,
                    30,
                    help="매출액 중 비료, 인건비 등이 차지하는 비율",
                )

                st.markdown("---")
                st.markdown("**⛄ 겨울 작기**")
                winter_enabled = st.checkbox(
                    "겨울재배 실시",
                    value=True,
                    help="선택을 해제하면 여름재배만 분석하고 겨울 매출, 난방비, 겨울 투자 상각은 0으로 계산합니다.",
                )
                if winter_enabled:
                    winter_total_yield = st.number_input("겨울 예상 생산량 (kg)", value=1200, step=100, min_value=0)
                    market_price = st.number_input("겨울 예상 단가 (원/kg)", value=18000, step=1000, min_value=0)
                else:
                    winter_total_yield = 0
                    market_price = 0
                    st.info("겨울재배 미실시: 여름재배만 기준으로 연간 소득을 계산합니다.")

            with st.expander("3. 시설투자비(만원)", expanded=False):
                investment_defaults = scaled_investment_defaults_10k(floor_area_m2)
                investment_scale = floor_area_m2 / BASE_INVESTMENT_AREA_M2
                st.caption(
                    f"첨부 엑셀 300평 기준 투자비를 현재 온실면적 {floor_area_m2 / 3.3:,.1f}평에 비례 환산합니다. "
                    f"(환산계수 {investment_scale:.2f})"
                )
                cost_film = st.number_input(
                    "이중비닐 공사비 (10년 상각)",
                    value=investment_defaults["double_vinyl_construction"],
                    step=10,
                    min_value=0,
                )
                cost_curtain = st.number_input(
                    "보온커튼 공사비 (10년 상각)",
                    value=investment_defaults["thermal_curtain_construction"],
                    step=10,
                    min_value=0,
                )
                cost_heater = st.number_input(
                    "이중비닐 피복재 (3년 상각)",
                    value=investment_defaults["double_vinyl_material"],
                    step=10,
                    min_value=0,
                )
                cost_facility = st.number_input(
                    "다겹보온커튼 자재비 (5년 상각)",
                    value=investment_defaults["thermal_curtain_material"],
                    step=10,
                    min_value=0,
                )

            with st.expander("4. 에너지 설정", expanded=False):
                energy_source = st.selectbox("사용 연료", list(FUEL_SETTINGS.keys()))
                unit_fuel_cost = st.number_input(
                    "연료 단가 (원)",
                    value=FUEL_SETTINGS[energy_source]["default_unit_cost"],
                    min_value=0,
                )
                target_temp = st.slider("목표 온도 (℃)", 8, 22, 15)
                insul_type = st.selectbox("보온 등급", list(U_VALUES.keys()))
                airtightness_level = st.selectbox(
                    "온실 기밀도",
                    list(AIR_TIGHTNESS_LEVELS.keys()),
                    index=1,
                    help="기밀도가 낮을수록 틈새바람과 누기로 난방부하가 증가한다고 가정합니다.",
                )

            submit_btn = st.form_submit_button(
                label="🚜 연간 분석 실행",
                type="primary",
                width="stretch",
            )

        with st.expander("5. 기상 CSV 자료(선택)", expanded=False):
            climate_file = st.file_uploader(
                "10년치 지역별 기상 CSV 업로드",
                type=["csv"],
                help="필수 컬럼: region, date, min_temp",
            )
            st.caption("업로드하지 않으면 앱 내장 간이 지역 파라미터를 사용합니다.")

        st.write("---")
        st.markdown("**📱 모바일로 접속하기(선택)**")
        qr_data = st.text_input("앱 URL", value="", help="배포 후 Streamlit URL을 넣으면 QR이 생성됩니다.")
        if qr_data.strip():
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={qr_data.strip()}"
            st.image(qr_url, caption="카메라로 스캔하세요")

    return submit_btn, {
        "region_name": region_name,
        "gh_width": gh_width,
        "gh_length": gh_length,
        "gh_side_h": gh_side_h,
        "gh_ridge_h": gh_ridge_h,
        "span_count": span_count,
        "side_wing_level": side_wing_level,
        "side_wing_width": side_wing_width,
        "summer_total_yield": summer_total_yield,
        "summer_price": summer_price,
        "summer_cost_ratio": summer_cost_ratio,
        "winter_enabled": winter_enabled,
        "winter_total_yield": winter_total_yield,
        "market_price": market_price,
        "cost_film": cost_film,
        "cost_curtain": cost_curtain,
        "cost_heater": cost_heater,
        "cost_facility": cost_facility,
        "energy_source": energy_source,
        "unit_fuel_cost": unit_fuel_cost,
        "target_temp": target_temp,
        "insul_type": insul_type,
        "airtightness_level": airtightness_level,
        "climate_file": climate_file,
    }


def show_results(values: dict) -> None:
    values = normalize_inputs(values)
    region_info = REGION_DATA[values["region_name"]]
    csv_region_info, climate_error = climate_params_from_csv(values.get("climate_file"), values["region_name"])
    climate_source = "내장 간이 파라미터"
    if csv_region_info:
        region_info = {"base": csv_region_info["base"], "amp": csv_region_info["amp"]}
        climate_source = f"업로드 CSV 기반({csv_region_info['years']}개년, {csv_region_info['rows']:,}행)"
    elif climate_error:
        st.warning(climate_error)

    summary = calculate_profit_summary(values, region_info)

    winter_revenue = summary["winter_revenue"]
    winter_fuel_cost = summary["winter_fuel_cost"]
    depreciation = summary["depreciation"]
    winter_net_profit = summary["winter_net_profit"]
    summer_revenue = summary["summer_revenue"]
    summer_cost = summary["summer_cost"]
    summer_net_profit = summary["summer_net_profit"]
    total_annual_revenue = summary["total_annual_revenue"]
    total_annual_profit = summary["total_annual_profit"]

    st.header(f"📊 연간 경영 분석 리포트 ({values['region_name']})")
    st.caption(f"기상자료 기준: {climate_source}")

    st.subheader("🏠 온실/모델 요약")
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    c1.metric("온실면적", f"{summary['floor_area_m2']:,.0f} ㎡")
    c2.metric("외피면적(근사)", f"{summary['surface_area']:,.0f} ㎡")
    c3.metric("보온 U값", f"{U_VALUES[values['insul_type']]:.1f}")
    c4.metric("기밀도 계수", f"{AIR_TIGHTNESS_LEVELS[values['airtightness_level']]:.2f}")
    st.caption(
        f"평균 가온시간: {summary['avg_heating_hours']:.1f} 시간/일 / "
        f"방풍벽 계수: {side_wing_factor(values['side_wing_level'], values['side_wing_width']):.2f}"
    )
    st.markdown(
        greenhouse_svg(
            values["gh_width"],
            values["gh_length"],
            values["gh_side_h"],
            values["gh_ridge_h"],
            values["span_count"],
            values["side_wing_level"],
            values["side_wing_width"],
            values["insul_type"],
            values["cost_curtain"],
        ),
        unsafe_allow_html=True,
    )

    st.subheader("☀️ 1. 여름 재배 성적표")
    col1, col2, col3 = st.columns(3)
    col1.metric("여름 매출", f"{summer_revenue / 10000:,.0f} 만원")
    col2.metric("여름 경영비", f"{summer_cost / 10000:,.0f} 만원")
    col3.metric(
        "여름 순이익",
        f"{summer_net_profit / 10000:,.0f} 만원",
        delta="수익 발생" if summer_net_profit > 0 else "수익 주의",
    )

    st.subheader("❄️ 2. 겨울 재배 투자 성적표")
    if values.get("winter_enabled", True):
        col1, col2, col3 = st.columns(3)
        col1.metric("겨울 매출", f"{winter_revenue / 10000:,.0f} 만원")
        col2.metric("겨울 비용(난방+상각)", f"{(winter_fuel_cost + depreciation) / 10000:,.0f} 만원")
        col3.metric(
            "겨울 순이익",
            f"{winter_net_profit / 10000:,.0f} 만원",
            delta="투자 성공" if winter_net_profit > 0 else "투자 주의",
        )
    else:
        st.info("겨울재배를 선택하지 않아 겨울 매출, 난방비, 겨울 투자 상각은 연간 분석에서 제외했습니다.")

    annual_title = "📅 3. 연간 총 소득 (여름 + 겨울)" if values.get("winter_enabled", True) else "📅 3. 연간 총 소득 (여름재배만)"
    st.subheader(annual_title)
    c1, c2, c3 = st.columns(3)
    c1.metric("연간 총 매출", f"{total_annual_revenue / 10000:,.0f} 만원")
    c2.metric("연간 총 순이익", f"{total_annual_profit / 10000:,.0f} 만원")
    c3.metric(
        "겨울 기여 순이익" if values.get("winter_enabled", True) else "여름 순이익",
        f"{(winter_net_profit if values.get('winter_enabled', True) else summer_net_profit) / 10000:,.0f} 만원",
    )

    st.write("---")
    st.subheader("💰 소득 구조 시각화")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.caption("계절별 매출 비중")
        df_rev = pd.DataFrame(
            {"계절": ["여름 작기", "겨울 작기"], "매출액": [summer_revenue, winter_revenue]}
        ).set_index("계절")
        st.bar_chart(df_rev)

    with chart_col2:
        st.caption("비용 구조 분석")
        df_cost = pd.DataFrame(
            {
                "항목": ["여름 경영비", "겨울 난방비", "시설 감가상각비"],
                "금액": [summer_cost, winter_fuel_cost, depreciation],
            }
        ).set_index("항목")
        st.bar_chart(df_cost)

    winter_line = (
        f"- 겨울 순이익: **{int(winter_net_profit / 10000):,}만원**"
        if values.get("winter_enabled", True)
        else "- 겨울재배: **미실시**"
    )
    st.success(
        f"""
**📢 최종 진단**
- 여름 순이익: **{int(summer_net_profit / 10000):,}만원**
{winter_line}
- 연간 총 순이익: **{int(total_annual_profit / 10000):,}만원**
"""
    )

    show_sensitivity_analysis(values, region_info)


def show_sensitivity_analysis(values: dict, region_info: dict) -> None:
    st.write("---")
    st.subheader("🔎 4. 민감도 분석")
    if not values.get("winter_enabled", True):
        st.info("겨울재배를 선택하지 않아 난방비 중심 민감도 분석은 표시하지 않습니다.")
        return
    st.caption("목표온도, 연료단가, 보온등급, 기밀도, 방풍벽이 난방비와 순이익에 미치는 영향을 비교합니다.")

    temp_df = sensitivity_table(values, region_info, "target_temp")
    fuel_df = sensitivity_table(values, region_info, "fuel_cost")
    insul_df = sensitivity_table(values, region_info, "insulation")
    airtight_df = sensitivity_table(values, region_info, "airtightness")
    side_wing_df = sensitivity_table(values, region_info, "side_wing")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["목표온도", "연료단가", "보온등급", "기밀도", "방풍벽"])

    with tab1:
        st.line_chart(temp_df.set_index("시나리오")[["겨울 난방비(만원)", "겨울 순이익(만원)"]])
        st.dataframe(temp_df, width="stretch", hide_index=True)

    with tab2:
        st.line_chart(fuel_df.set_index("시나리오")[["겨울 난방비(만원)", "겨울 순이익(만원)"]])
        st.dataframe(fuel_df, width="stretch", hide_index=True)

    with tab3:
        st.bar_chart(insul_df.set_index("시나리오")[["겨울 난방비(만원)", "겨울 순이익(만원)"]])
        st.dataframe(insul_df, width="stretch", hide_index=True)

    with tab4:
        st.bar_chart(airtight_df.set_index("시나리오")[["겨울 난방비(만원)", "겨울 순이익(만원)"]])
        st.dataframe(airtight_df, width="stretch", hide_index=True)

    with tab5:
        st.bar_chart(side_wing_df.set_index("시나리오")[["겨울 난방비(만원)", "겨울 순이익(만원)"]])
        st.dataframe(side_wing_df, width="stretch", hide_index=True)


def show_references() -> None:
    st.write("---")
    with st.expander("📚 분석 근거 및 데이터 출처 보기"):
        st.markdown(
            """
### 1. 기상 데이터
- 현재 버전의 지역별 `base`, `amp` 값은 의사결정 비교용 간이 파라미터입니다.
- 선택적으로 `region`, `date`, `min_temp` 컬럼을 가진 CSV를 업로드하면 해당 지역의 겨울철 자료에서 기상 파라미터를 추정합니다.
- 다음 단계에서는 10년치 시간별 기온 자료를 연결해 지역별, 월별, 시간대별 보정계수로 교체하는 것이 좋습니다.

### 2. 난방부하 산출 구조
- 기본 구조: `외피면적 × U값 × (목표온도 - 외기온) × 가온시간`
- 기밀도 계수는 틈새바람과 누기로 인한 추가 난방부하를 반영하기 위한 보정값입니다.
- 방풍벽 계수는 온실 양쪽 방풍벽이 외부 바람 노출을 완화하는 효과를 반영하기 위한 보정값입니다.
- 외피면적은 아치형 지붕, 측벽, 마구리 면적을 근사 계산합니다.

### 3. 에너지 기준
- 면세유: 발열량 8,500kcal/L, 효율 85% 가정
- 전기: 열당량 860kcal/kWh, 효율 98% 가정

### 4. 감가상각 기준
- 첨부 엑셀 `연장재배 투자비(300평)`과 `경영비(10a, 300평)`의 300평 기준 자료를 기본값으로 사용합니다.
- 기본 투자비는 현재 온실면적에 비례해 `현재 온실면적 ÷ 300평` 계수로 환산합니다.
- 이중비닐 공사와 보온커튼 공사는 10년, 이중비닐 피복재는 3년, 다겹보온커튼 자재비는 5년 정액법입니다.
"""
        )


require_login()

st.title("🗺️ [전남] 무화과 겨울재배 의사결정지원시스템")
st.markdown("겨울철 투자 분석뿐만 아니라, 여름 작기를 포함한 연간 총 소득까지 예측합니다.")
st.divider()

submit_btn, input_values = collect_inputs()

if submit_btn:
    show_results(input_values)
else:
    st.info("👈 왼쪽 메뉴에서 데이터를 입력하고 '분석 실행' 버튼을 눌러주세요.")

show_references()
