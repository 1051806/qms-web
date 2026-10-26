#!/usr/bin/env python3
"""QMS中厚查询Web服务（带登录）"""
import json, sys, re, warnings, threading, urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

warnings.filterwarnings('ignore')
sys.path.insert(0, '/mnt/users/1051806/skills/eda-monitor-alert-1051806/scripts')

PORT = 8899
QMS_BASE = "https://sunnyqms.sunnyoptical.cn"

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# ============ SSO登录 ============
def sso_login(username, password, mac):
    """用用户凭据做SSO登录，返回token"""
    from qms_sso_auth import get_qms_token
    token = get_qms_token(username, password, mac)
    return token

# ============ QMS中厚查询 ============
QMS_API = QMS_BASE + "/base/prod/qmsSjssjtyGl/getMeasurementDataByTime"
FACTORY_AREAS = [("120003", "三工厂"), ("120002", "二工厂"), ("120001", "一工厂")]
MOLD_NUMBERS = ["B", "E", "TM", "M", ""]
BASE_PARAMS = {
    "cGx": "3-ZCX", "cSjlx": "尺寸巡检", "cJytxbm": "LbE0b001",
    "cFactory": "1200", "cXs": "24", "cSfcg": "1", "cJsfs": "1",
}

def query_qms(token, part, mirror, start, end, sfcg=""):
    import requests, re, warnings
    warnings.filterwarnings('ignore')
    tz_base = re.sub(r'^[A-Z]+', '', part) or part
    tz_code = f"{tz_base}-{mirror}"
    
    headers = {
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "lang": "zh-CN", "Accept": "application/json, text/plain, */*",
        "Origin": QMS_BASE, "Referer": QMS_BASE + "/", "User-Agent": "Mozilla/5.0",
    }
    
    for fa_code, fa_name in FACTORY_AREAS:
        for mh in MOLD_NUMBERS:
            params = dict(BASE_PARAMS)
            if sfcg: params["cSfcg"] = sfcg
            params["cTzCode"] = tz_code
            params["cStartTime"] = start
            params["cEndTime"] = end
            params["cFactoryArea"] = fa_code
            params["cMh"] = mh
            try:
                resp = requests.post(QMS_API, json=params, headers=headers, timeout=15, verify=False)
                data = resp.json()
                if data.get("success") and data.get("result"):
                    for k, v in data["result"].items():
                        if v.get("dailyData"):
                            return data
            except:
                continue
    return {"error": "未找到数据", "success": False}

# ============ HTTP服务 ============
class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
    
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/' or path == '/index.html':
            self._serve_file('/mnt/users/1051806/outputs/57dbd1eb-e6cc-4878-880b-fd49e4bd6c53/qms_web/index.html', 'text/html')
        elif path == '/api/health':
            self._json({"ok": True})
        else:
            self.send_error(404)
    
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        
        if path == '/api/login':
            token = sso_login(body.get('username',''), body.get('password',''), body.get('mac',''))
            if token:
                self._json({"ok": True, "token": token})
            else:
                self._json({"ok": False, "error": "SSO登录失败，请检查工号/密码/MAC地址"})
        elif path == '/api/query':
            token = body.get('token','')
            if not token:
                self._json({"error": "请先登录"})
                return
            result = query_qms(token, body.get('part',''), body.get('mirror',''),
                             body.get('start',''), body.get('end',''), body.get('sfcg',''))
            self._json(result)
        else:
            self.send_error(404)
    
    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _serve_file(self, path, mime):
        try:
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', f'{mime}; charset=utf-8')
            self._cors()
            self.end_headers()
            self.wfile.write(content)
        except:
            self.send_error(404)
    
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def log_message(self, *args):
        pass

if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f"QMS查询服务启动: http://localhost:{PORT}")
    server.serve_forever()
