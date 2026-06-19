import requests
import json

# 测试基础URL
BASE_URL = "http://localhost:8000/api/v1"

# 测试用户注册
import random
import string

def generate_random_string(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def test_register():
    url = f"{BASE_URL}/users/register"
    headers = {"Content-Type": "application/json"}
    random_username = f"testuser_new_{generate_random_string()}"
    random_email = f"{random_username}@example.com"
    data = {
        "username": random_username,
        "email": random_email,
        "password": "testpassword",
        "role": "NORMAL",
        "trading_pairs": ["BTCUSDT", "ETHUSDT"]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print("注册测试:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    return response.json()

# 测试用户登录
def test_login(username, password):
    url = f"{BASE_URL}/users/login"
    headers = {"Content-Type": "application/json"}
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print("登录测试:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    return response.json()

# 测试获取用户信息
def test_get_user_info(token):
    url = f"{BASE_URL}/users/me"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    print("获取用户信息测试:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    return response.json()

# 测试更新用户交易对
def test_update_trading_pairs(token):
    # 添加交易对测试
    url = f"{BASE_URL}/users/me/trading-pairs"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    # 测试添加一个新的交易对
    data_add = {
        "action": "add",
        "trading_pair": "SOLUSDT"
    }
    response_add = requests.patch(url, headers=headers, data=json.dumps(data_add))
    print("添加交易对测试:")
    print(f"状态码: {response_add.status_code}")
    print(f"响应: {response_add.text}")

    # 测试删除一个交易对
    data_remove = {
        "action": "remove",
        "trading_pair": "BTCUSDT"
    }
    response_remove = requests.patch(url, headers=headers, data=json.dumps(data_remove))
    print("删除交易对测试:")
    print(f"状态码: {response_remove.status_code}")
    print(f"响应: {response_remove.text}")

    # 测试无效操作类型
    data_invalid = {
        "action": "invalid",
        "trading_pair": "ETHUSDT"
    }
    response_invalid = requests.patch(url, headers=headers, data=json.dumps(data_invalid))
    print("无效操作类型测试:")
    print(f"状态码: {response_invalid.status_code}")
    print(f"响应: {response_invalid.text}")

    return response_add.json(), response_remove.json(), response_invalid.json()

# 测试更新用户信息
def test_update_user_info(token):
    url = f"{BASE_URL}/users/me"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    # 生成唯一邮箱地址
    random_string = generate_random_string()
    unique_email = f"updated_{random_string}@example.com"
    data = {
        "email": unique_email,
        "trading_pairs": ["ETHUSDT", "DOGEUSDT", "PEPEUSDT"]
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    print("更新用户信息测试:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    return response.json()

# 运行测试
if __name__ == "__main__":
    print("开始测试...")
    register_result = test_register()
    if register_result.get("code") == 200:
        # 获取注册的用户名和密码
        username = register_result.get("data", {}).get("username")
        password = "testpassword"  # 注册时使用的密码
        login_result = test_login(username, password)
        if login_result.get("code") == 200:
            token = login_result.get("data", {}).get("access_token")
            if token:
                test_get_user_info(token)
                test_update_trading_pairs(token)
                test_update_user_info(token)
    print("测试结束.")