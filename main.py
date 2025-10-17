# main.py
import sys
import os
import yaml
import logging
from collections import deque
from datetime import datetime
import hashlib
import time
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 添加 utils 路径
sys.path.append(os.path.dirname(__file__))
from utils.prompt_builder import build_analysis_prompt
from utils.llm_analyzer import LLMAnalyzer
from utils.report_saver import ReportSaver
from utils.email_notifier import EmailNotifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log")
    ]
)

class LogMonitorHandler(FileSystemEventHandler):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logs_config = config['logs']
        self.context_buffer = deque(maxlen=100)
        self.dedup_cache = {}  # {hash: timestamp}
        self.dedup_window = config.get('dedup_window_seconds', 300)

        # 初始化组件
        self.llm = LLMAnalyzer(config['llm'])
        self.saver = ReportSaver(config['output_dir'])
        self.notifier = EmailNotifier(config['email'])

        # 获取所有监控文件的关键字集合
        self.keywords = set()
        for lc in self.logs_config:
            self.keywords.update(lc['keywords'])

    def on_modified(self, event):
        if event.is_directory or not self._is_monitored_file(event.src_path):
            return

        try:
            with open(event.src_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            self._process_new_lines(lines)
        except Exception as e:
            logging.error(f"读取日志失败 {event.src_path}: {e}")

    def _is_monitored_file(self, filepath):
        return any(filepath == lc['path'] or filepath.endswith(lc['path']) for lc in self.logs_config)

    def _process_new_lines(self, lines):
        last_n = self.config['context_lines']['before']
        recent_lines = list(self.context_buffer)[-last_n:]

        for line in lines[len(recent_lines):]:
            line = line.strip()
            if not line:
                continue

            self.context_buffer.append(line)

            if self._contains_error(line):
                context = self._extract_context()
                context_hash = hashlib.md5(context.encode()).hexdigest()

                # 去重判断
                now = time.time()
                if context_hash in self.dedup_cache:
                    if now - self.dedup_cache[context_hash] < self.dedup_window:
                        logging.info("【去重】跳过重复告警")
                        continue
                self.dedup_cache[context_hash] = now

                self._trigger_alert(context)

    def _contains_error(self, line):
        return any(kw.lower() in line.lower() for kw in self.keywords)

    def _extract_context(self):
        total = len(self.context_buffer)
        idx = total - 1
        # 找到最后一条匹配 error 的行（即最新的一条）
        while idx >= 0:
            line = self.context_buffer[idx]
            if self._contains_error(line):
                break
            idx -= 1
        if idx < 0:
            idx = total - 1  # fallback

        start = max(0, idx - self.config['context_lines']['before'])
        end = min(total, idx + self.config['context_lines']['after'] + 1)
        return "\n".join(list(self.context_buffer)[start:end])


    def _trigger_alert(self, context):
        logging.info("发现 ERROR 级别日志，触发 AI 分析...")
        prompt = build_analysis_prompt(context)
        try:
            raw_response = self.llm.query(prompt)
            logging.info(f"[LLM Raw Output]:\n{raw_response}")
            analysis = self._safe_parse_json(raw_response)
            if not analysis:
                logging.error("AI 返回非 JSON 内容，转存原始输出")
                analysis = {
                    "summary": "AI 分析失败",
                    "severity": "未知",
                    "diagnosis_path": ["解析失败，请查看原始输出"],
                    "solution": {"immediate": "人工介入", "long_term": "检查 LLM 输出格式"}
                }
                # 附加原始输出便于调试
                analysis["raw_llm_output"] = raw_response

            # 注入时间戳
            analysis["timestamp"] = datetime.now().isoformat()

            report_path = self.saver.save(context, analysis)
            self.notifier.send(analysis, context, report_path)
            logging.info(f"告警处理完成，报告已保存至: {report_path}")

        except Exception as e:
            logging.error(f"处理告警时发生错误: {e}")

    def _safe_parse_json(self, text):
        try:
            # 尝试提取第一个 `{...}` 结构
            start = text.find('{')
            end = text.rfind('}') + 1
            if start == -1 or end == 0:
                return None
            cleaned = text[start:end]
            return json.loads(cleaned)
        except Exception as e:
            logging.warning(f"JSON 解析失败: {e}")
            return None


def load_config(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    config_file = "/home/chenyq/study/python/agentLazyLLM/lazyllm-venv/log_monitor/config.yaml"
    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        sys.exit(1)

    config = load_config(config_file)
    handler = LogMonitorHandler(config)

    observer = Observer()
    paths = [lc['path'] for lc in config['logs']]
    for path in set(os.path.dirname(p) or '.' for p in paths):
        observer.schedule(handler, path, recursive=False)
        logging.info(f"监听目录: {path}")

    logging.info("日志监控启动，按 Ctrl+C 停止...")
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("监控已停止")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
