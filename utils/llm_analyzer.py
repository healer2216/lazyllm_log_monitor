# utils/llm_analyzer.py
import lazyllm
import time
import logging

class LLMAnalyzer:
    def __init__(self, config):
        self.model_name = config['model_name']
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 2)

        # 初始化模型（需确保已安装对应模型）
        try:
            self.model = lazyllm.OnlineChatModule(source='sensenova',model= config['model_name'])
            logging.info(f"[LLM] 已加载模型: {self.model_name}")
        except Exception as e:
            logging.error(f"[LLM] 模型加载失败: {e}")
            raise

    def query(self, prompt):
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                response = self.model(prompt)
                if isinstance(response, str):
                    result = response.strip()
                else:
                    result = str(response)

                duration = time.time() - start_time
                if duration > self.timeout:
                    logging.warning(f"[LLM] 请求超时 ({duration:.2f}s)")
                    continue

                logging.info(f"[LLM] 成功获取响应 (耗时: {duration:.2f}s)")
                return result

            except Exception as e:
                logging.error(f"[LLM] 第 {attempt} 次调用失败: {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(2)
        return None
