# utils/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging


class EmailNotifier:
    def __init__(self, config):
        self.enable = config.get('enable', True)
        if not self.enable:
            logging.info("[Email] 邮件功能已禁用")
            return

        self.smtp_server = config['smtp_server']  # e.g., smtp.qq.com
        self.port = config['port']
        self.username = config['username']
        self.password = config['password']
        self.recipients = config['recipients']
        self.sender_name = config.get('sender_name', 'LogMonitor AI')

    def send(self, analysis, log_context, report_path):
        if not self.enable:
            return

        subject = f"【严重告警】系统检测到 ERROR 异常"
        body = self._build_email_body(analysis, log_context, report_path)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.username}>"
        msg["To"] = ", ".join(self.recipients)

        part = MIMEText(body, "html", "utf-8")
        msg.attach(part)

        try:
            logging.info(f"[Email] 正在连接 {self.smtp_server}:{self.port} ...")

            # 明确使用 SMTP_SSL 处理 465 端口
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_server, self.port, timeout=30)
                server.starttls()

            logging.info(f"[Email] 正在登录...")
            server.login(self.username, self.password)
            logging.info(f"[Email] 登录成功")

            server.sendmail(self.username, self.recipients, msg.as_string())
            server.close()

            logging.info(f"[Email] 成功发送邮件至 {len(self.recipients)} 名收件人")

        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"[Email] 认证失败，请检查用户名或授权码: {e}")
        except smtplib.SMTPConnectError as e:
            logging.error(f"[Email] 连接错误，可能是服务器拒绝连接: {e}")
        except TimeoutError:
            logging.error(f"[Email] 连接超时，请检查网络或防火墙")
        except ConnectionRefusedError:
            logging.error(f"[Email] 连接被拒绝，可能端口被封")
        except Exception as e:
            logging.error(f"[Email] 其他错误: {type(e).__name__}: {e}")

    def _build_email_body(self, analysis, log_context, report_path):
        diagnosis_list = "".join([f"<li>{p}</li>" for p in analysis.get("diagnosis_path", [])])
        solution_immediate = analysis.get("solution", {}).get("immediate", "无")
        solution_long_term = analysis.get("solution", {}).get("long_term", "无")

        return f"""
<html>
<body>
<h2>系统异常告警</h2>
<p><strong>时间：</strong> {analysis.get('timestamp', '未知')}</p>

<h3>日志片段</h3>
<pre style="background:#f4f4f4; padding:10px; border:1px solid #ccc; border-radius:5px;">
{log_context}
</pre>

<h3>AI 分析结果</h3>
<ul>
  <li><strong>异常说明：</strong> {analysis.get('summary', '未提供')}</li>
  <li><strong>紧急程度：</strong> 
    <span style="color:{'red' if analysis.get('severity')=='高' else 'orange' if analysis.get('severity')=='中' else 'green'};">
        {analysis.get('severity', '未知')}
    </span>
  </li>
</ul>

<h4>排查路径</h4>
<ol>{diagnosis_list}</ol>

<h4>解决方案</h4>
<p><strong>临时措施：</strong> {solution_immediate}</p>
<p><strong>长期方案：</strong> {solution_long_term}</p>

<p><strong>报告路径：</strong> {report_path}</p>

<hr>
<small>此邮件由 LogMonitor AI 自动生成。</small>
</body>
</html>
"""
