"""QMS查询API - Vercel Serverless"""
import json, sys, os, re, warnings
warnings.filterwarnings('ignore')

QMS_BASE = "https://sunnyqms.sunnyoptical.cn"
QMS_API = QMS_BASE + "/base/prod/qmsSjssjtyGl/getMeasurementDataByTime"
FACTORY_AREAS = [("120003", "三工厂"), ("120002", "二工厂"), ("120001", "一工厂")]
MOLD_NUMBERS = ["B", "E", "TM", "M", ""]
BASE_PARAMS = {
    "cGx": "3-ZCX", "cSjlx": "尺寸巡检", "cJytxbm": "LbE0b001",
    "cFactory": "1200", "cXs": "24", "cSfcg": "1", "cJsfs": "1",
}

def handler(request):
    try:
        body = json.loads(request.body or '{}')
        token = body.get('token', '')
        part = body.get('part', '')
        mirror = body.get('mirror', '')
        start = body.get('start', '')
        end = body.get('end', '')
        sfcg = body.get('sfcg', '')
        
        if not token:
            return _json({'error': '请先登录'})
        
        import requests
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
                                return _json(data)
                except:
                    continue
        
        return _json({"error": "未找到数据", "success": False})
    except Exception as e:
        return _json({"error": str(e)})

def _json(data):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(data, ensure_ascii=False)
    }
