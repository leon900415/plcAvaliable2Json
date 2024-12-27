from http.server import BaseHTTPRequestHandler
from flask import Flask, render_template, request, jsonify
import json
import pypinyin
import re
from io import StringIO
from csv import reader
import os

app = Flask(__name__, 
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')))

def chinese_to_pinyin(text):
    """
    将文本转换为ID格式：
    非中文字符 + "-" + 中文拼音首字母 + "-" + 剩余非中文字符
    """
    text = str(text)
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    
    # 分割所有中文片段
    parts = chinese_pattern.split(text)
    chinese_matches = chinese_pattern.findall(text)
    
    # 处理中文部分：转换为拼音首字母
    pinyin_parts = []
    if chinese_matches:
        for chinese in chinese_matches:
            pinyin_list = pypinyin.lazy_pinyin(chinese)
            pinyin_parts.append(''.join([word[0].upper() for word in pinyin_list]))
    
    # 组合结果
    result_parts = []
    
    # 添加第一个非中文部分（如果存在）
    if parts[0]:
        result_parts.append(parts[0].strip())
    
    # 添加中文拼音部分（如果存在）
    if pinyin_parts:
        result_parts.append(''.join(pinyin_parts))
    
    # 添加剩余的非中文部分（如果存在）
    for part in parts[1:]:
        if part.strip():
            result_parts.append(part.strip())
    
    # 用 "-" 连接所有部分
    return '-'.join(result_parts)

def get_name_from_row(row):
    """
    从行数据生成 name：
    1. 用 "-" 连接所有非空列
    2. 取第一个分号后的内容
    """
    # 过滤掉空列并去除前后空格
    valid_columns = [col.strip() for col in row if col.strip()]
    
    # 用 "-" 连接所有列
    full_text = '-'.join(valid_columns)
    
    # 获取第一个分号后的内容
    if ';' in full_text:
        return full_text.split(';', 1)[1].strip()
    return full_text.strip()

def determine_plc_data_type(row):
    """
    根据行内容确定 plcDataType：
    连接所有列检查关键字
    """
    # 连接所有非空列
    full_text = '-'.join([col.strip() for col in row if col.strip()]).upper()
    
    if 'INT' in full_text:
        return 'int'
    elif 'WORD' in full_text:
        return 'short'
    elif 'REAL' in full_text:
        return 'float'
    return 'boolean'

def csv_to_json(csv_content):
    """将CSV内容转换为指定格式的JSON"""
    try:
        properties = []
        csv_reader = reader(StringIO(csv_content))
        
        for index, row in enumerate(csv_reader, 1):
            try:
                if not row or not any(row):
                    continue
                
                # 获取 name
                name = get_name_from_row(row)
                if not name:
                    continue
                
                # 生成 ID
                id = chinese_to_pinyin(name)
                
                # 确定数据类型
                plc_data_type = determine_plc_data_type(row)
                
                properties.append({
                    "id": id,
                    "name": name,
                    "expands": {
                        "plcDataType": plc_data_type,
                        "isShowCurve": 1
                    }
                })
                
            except Exception as row_error:
                print(f"处理第 {index} 行时出错: {str(row_error)}")
                continue
        
        result = {
            "events": [],
            "properties": properties,
            "functions": [],
            "tags": []
        }
        
        return json.dumps(result, indent=4, ensure_ascii=False)
        
    except Exception as e:
        raise Exception(f"CSV处理错误: {str(e)}\n请确保CSV文件格式正确，并且所有行的数据完整。")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': '请上传CSV文件'}), 400
    
    try:
        file_content = file.stream.read().decode('utf-8')
        json_result = csv_to_json(file_content)
        return jsonify({'result': json_result})
    except Exception as e:
        return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        try:
            with app.test_client() as test_client:
                response = test_client.get(self.path)
                self.send_response(response.status_code)
                for header, value in response.headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_POST(self):
        """Handle POST requests"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            with app.test_client() as test_client:
                response = test_client.post(
                    self.path,
                    data=body,
                    headers=dict(self.headers)
                )
                self.send_response(response.status_code)
                for header, value in response.headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())

# 本地开发服务器启动
if __name__ == '__main__':
    app.run(debug=True, port=5000) 