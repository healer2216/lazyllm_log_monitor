# utils/prompt_builder.py
import json

def build_analysis_prompt(log_context):
    prompt = f"""
你是一名资深运维工程师，请分析以下应用日志中的错误信息，并提供专业建议：

【原始日志上下文】
{log_context}

请根据以上日志回答以下问题：
1. 异常情况说明（简要描述发生了什么错误）
2. 紧急程度评估（高/中/低，说明理由）
3. 可能的排查路径（从代码、配置、网络、依赖等方面分析）
4. 建议的解决方案（临时缓解 + 根本解决）

请以严格的 JSON 格式输出结果，不要包含其他内容。字段定义如下：
{{
  "summary": "字符串，一句话概括",
  "severity": "高|中|低",
  "diagnosis_path": ["字符串数组", "列出可能原因"],
  "solution": {{
    "immediate": "立即可操作的措施",
    "long_term": "长期修复方案"
  }}
}}
"""
    return prompt
