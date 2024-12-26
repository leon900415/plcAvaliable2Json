# PLC CSV 转 JSON 工具

这是一个简单的 Web 应用程序，用于将 PLC CSV 文件转换为特定格式的 JSON。

## 功能特点

- 支持拖拽上传 CSV 文件
- 自动将中文描述转换为拼音首字母作为 ID
- 根据地址类型自动判断数据类型
- 支持复制和下载转换后的 JSON

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
python app.py
```

3. 打开浏览器访问：`http://localhost:5000`

## CSV 文件格式要求

CSV 文件应包含两列（无表头）：
- 第一列：PLC 地址
- 第二列：描述（中文）

## 输出 JSON 格式

输出的 JSON 格式如下：
```json
{
    "events": [],
    "properties": [
        {
            "id": "拼音首字母",
            "name": "中文描述",
            "expands": {
                "plcDataType": "数据类型",
                "isShowCurve": 1
            }
        }
    ],
    "functions": [],
    "tags": []
}
``` 