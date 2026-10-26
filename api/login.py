"""SSO登录API - Vercel Serverless"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

def handler(request):
    try:
        body = json.loads(request.body or '{}')
        username = body.get('username', '')
        password = body.get('password', '')
        mac = body.get('mac', '')
        
        if not username or not password or not mac:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': False, 'error': '请填写完整'})
            }
        
        # SSO登录
        import requests, re, warnings
        warnings.filterwarnings('ignore')
        
        SSO_BASE = "https://sso.sunnyoptical.cn"
        QMS_CAS = "https://sunnyqms.sunnyoptical.cn/login/cas"
        
        session = requests.Session()
        session.verify = False
        
        # Step 1: 获取登录页面
        service_url = QMS_CAS
        login_url = f"{SSO_BASE}/login?service={service_url}"
        r1 = session.get(login_url, timeout=15)
        
        # 提取execution token
        import re as re2
        exec_match = re2.search(r'name=["\']execution["\'][^>]*value=["\']([^"\']*)["\']', r1.text)
        exec_token = exec_match.group(1) if exec_match else "e1s1"
        event_match = re2.search(r'name=["\']_eventId["\'][^>]*value=["\']([^"\']*)["\']', r1.text)
        event_id = event_match.group(1) if event_match else "submit"
        lt_match = re2.search(r'name=["\']lt["\'][^>]*value=["\']([^"\']*)["\']', r1.text)
        lt = lt_match.group(1) if lt_match else ""
        
        # Step 2: POST凭据
        body_data = {
            'username': username,
            'password': password,
            'macAddress': mac,
            'execution': exec_token,
            '_eventId': event_id,
            'state': '1',
            'lt': lt,
        }
        r2 = session.post(login_url, data=body_data, timeout=15, allow_redirects=False)
        
        if r2.status_code not in (301, 302):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': False, 'error': f'SSO登录未跳转(HTTP {r2.status_code})'})
            }
        
        # Step 3: 跟随重定向获取token
        ticket_url = r2.headers.get('Location', '')
        if not ticket_url:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': False, 'error': 'SSO无Location'})
            }
        
        r3 = session.get(ticket_url, timeout=15, allow_redirects=True)
        
        # 从URL或cookie中提取token
        token = None
        final_url = r3.url if hasattr(r3, 'url') else ''
        
        token_match = re2.search(r'token=Bearer%20([A-Za-z0-9._-]+)', final_url)
        if token_match:
            token = token_match.group(1)
        
        if not token:
            token_match2 = re2.search(r'token=Bearer\s+([A-Za-z0-9._-]+)', final_url)
            if token_match2:
                token = token_match2.group(1)
        
        if not token:
            for cookie_name, cookie_value in session.cookies.items():
                if 'qmes_token' in cookie_name:
                    token_match3 = re2.search(r'Bearer%20([A-Za-z0-9._-]+)', cookie_value)
                    if token_match3:
                        token = token_match3.group(1)
                    else:
                        token_match4 = re2.search(r'Bearer\s+([A-Za-z0-9._-]+)', cookie_value)
                        if token_match4:
                            token = token_match4.group(1)
        
        if not token and r3.text:
            token_match5 = re2.search(r'Bearer%20([A-Za-z0-9._-]+)', r3.text)
            if token_match5:
                token = token_match5.group(1)
        
        if token:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': True, 'token': token})
            }
        else:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': False, 'error': 'Token未找到'})
            }
    except Exception as e:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'ok': False, 'error': str(e)})
        }
