from pathlib import Path
import runpy


APP_PATH = Path(__file__).parent / "01. 최초 파이썬 앱" / "app.py"
runpy.run_path(str(APP_PATH), run_name="__main__")
