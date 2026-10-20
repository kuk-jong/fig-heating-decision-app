"""Run from the release directory: python tests/smoke_app.py."""
from io import StringIO
from pathlib import Path
import json
import os
import sys
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)
app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
assert not app.exception, [e.message for e in app.exception]
app.text_input[0].set_value("invalid-password")
next(b for b in app.button if b.label == "로그인").click()
app.run()
assert len(app.error) == 1
app.text_input[0].set_value("1234")
next(b for b in app.button if b.label == "로그인").click()
app.run()
assert not app.exception, [e.message for e in app.exception]
assert any("후속 버전 v0.5.0" in c.value for c in app.caption)
next(b for b in app.button if "연간 분석 실행" in b.label).click()
app.run()
assert not app.exception and len(app.metric) == 13
assert any("관측자료 미적용" in w.value for w in app.warning)
values = app.session_state["enh_last_analysis"].copy()
# Use the supplied synthetic example for an end-to-end fit.
values["climate_file"] = StringIO((APP_DIR / "examples/climate_csv_template.csv").read_text(encoding="utf-8"))
app.session_state["enh_last_analysis"] = values
app.run()
assert not app.exception and len(app.metric) == 13
assert any("A = 11.5000" in m.value for m in app.markdown)
assert not any("관측자료 미적용" in w.value for w in app.warning)
app.run()
assert not app.exception and len(app.metric) == 13
values["climate_file"] = StringIO("bad\n1")
app.session_state["enh_last_analysis"] = values
app.run()
assert not app.exception and len(app.error) == 1 and len(app.metric) == 0
print(json.dumps({"app_version": "0.5.0", "login": "pass", "default_analysis": "pass",
                  "synthetic_csv_regression": "pass", "rerun": "pass",
                  "invalid_csv_stops_analysis": "pass"}, ensure_ascii=False))
