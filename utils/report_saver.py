# utils/report_saver.py
import os
import json
import datetime

class ReportSaver:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save(self, raw_context, analysis_dict, timestamp=None):
        ts = timestamp or datetime.datetime.now()
        date_str = ts.strftime("%Y%m%d")
        time_str = ts.strftime("%H%M%S")

        dir_path = os.path.join(self.output_dir, date_str)
        os.makedirs(dir_path, exist_ok=True)

        filename = f"alert_{time_str}.json"
        filepath = os.path.join(dir_path, filename)

        report_data = {
            "timestamp": ts.isoformat(),
            "raw_log_context": raw_context,
            "analysis": analysis_dict
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        return filepath
