from http.server import BaseHTTPRequestHandler
from flask import Flask, render_template, request, jsonify
import json
import pypinyin
import re
from io import StringIO, BytesIO
from csv import reader
import os
import cgi

app = Flask(__name__, 
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')))

def chinese_to_pinyin(text):
    """生成ID：保留中文前的非中文字符，中文转换为拼音首字母拼接，保留数字格式"""
    text = str(text)
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    number_pattern = re.compile(r'\d+')
    
    match = chinese_pattern.search(text)
    if not match:
        return text
    
    prefix = text[:match.start()].strip()
    chinese_part = text[match.start():]
    
    last_number = None
    number_matches = list(number_pattern.finditer(chinese_part))
    if number_matches:
        last_number = number_matches[-1].group()
        chinese_part = chinese_part[:number_matches[-1].start()] + chinese_part[number_matches[-1].end():]
    
    pinyin_list = pypinyin.lazy_pinyin(chinese_part)
    pinyin_part = ''.join([word[0].upper() for word in pinyin_list])
    
    if prefix and pinyin_part:
        result = f"{prefix}-{pinyin_part}"
    elif prefix:
        result = prefix
    else:
        result = pinyin_part
    
    if last_number:
        result = f"{result}-{last_number}"
    
    return result

def get_description_after_semicolon(text):
    """获取分号后的内容"""
    if ';' in text:
        return text.split(';', 1)[1].strip()
    return text.strip()

def determine_plc_data_type(address, description=''):
    """根据地址和描述确定 plcDataType"""
    if not address and not description:
        return 'boolean'
    
    full_text = f"{str(address)};{str(description)}".upper()
    address_part = str(address).upper().split(';')[0]
    
    if re.match(r'^[IQM]\d+\.\d+', address_part):
        return 'boolean'
    
    if 'INT' in full_text:
        return 'int'
    elif 'REAL' in full_text:
        return 'float'
    elif 'WORD' in full_text:
        return 'short'
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
                
                first_col = row[0].strip() if row[0] else ''
                if not first_col:
                    continue
                
                if ';' in first_col:
                    parts = first_col.split(';', 1)
                    address = parts[0].strip()
                    description = parts[1].strip()
                else:
                    address = first_col
                    description = ''
                
                if len(row) > 1:
                    other_parts = [get_description_after_semicolon(part.strip()) for part in row[1:] if part and part.strip()]
                    if other_parts:
                        if description:
                            description = f"{description}-{'-'.join(other_parts)}"
                        else:
                            description = '-'.join(other_parts)
                
                if not description:
                    description = get_description_after_semicolon(address)
                
                name = description
                id = chinese_to_pinyin(description)
                plc_data_type = determine_plc_data_type(address, name)
                
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
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with app.test_client() as test_client:
            response = test_client.get(self.path)
            self.wfile.write(response.data)
            
    def do_POST(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                # 获取 boundary
                boundary = content_type.split('boundary=')[1].encode()
                
                # 读取请求内容
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # 创建类文件对象
                data_file = BytesIO(post_data)
                
                # 解析 multipart 数据
                form = cgi.FieldStorage(
                    fp=data_file,
                    headers=self.headers,
                    environ={
                        'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': content_type,
                        'CONTENT_LENGTH': content_length
                    }
                )
                
                # 获取上传的文件
                if 'file' in form:
                    fileitem = form['file']
                    if fileitem.filename:
                        # 读取文件内容
                        file_content = fileitem.file.read().decode('utf-8')
                        # 处理 CSV 内容
                        json_result = csv_to_json(file_content)
                        
                        # 发送响应
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response_data = json.dumps({'result': json_result})
                        self.wfile.write(response_data.encode('utf-8'))
                        return
                    
            # 如果不是文件上传或处理失败
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = json.dumps({'error': '请上传CSV文件'})
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = json.dumps({'error': f'处理文件时出错: {str(e)}'})
            self.wfile.write(error_response.encode('utf-8')) 