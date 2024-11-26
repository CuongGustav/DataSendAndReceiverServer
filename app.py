import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def hello():
    return "<p>Hello</p>"

# Đường dẫn đến file JSON
json_text_file = 'text_data.json'
# Đường dẫn đến file JSON lưu hình ảnh
json_image_file = 'image_data.json'

# Hàm lưu văn bản vào file JSON
def save_text_to_file(text):
    with open(json_text_file, 'w') as f:
        json.dump({"text": text}, f)
# Hàm đọc văn bản từ file JSON
def read_text_from_file():
    try:
        with open(json_text_file, 'r') as f:
            content = f.read().strip()  
            if not content:
                return {"text": "No text found in file"}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"text": "No valid data found or file is missing"}
# Hàm xóa văn bản trong file JSON
def clear_text_in_file():
    with open(json_text_file, 'w') as f:
        json.dump({"text": ""}, f)
# API để nhận văn bản từ client
@app.route('/send_text', methods=['POST'])
def send_text():
    try:
        data = request.get_json()
        text = data.get('text')
        if text:
            save_text_to_file(text)  
            return jsonify({"message": "Text received successfully", "received_text": text}), 200
        else:
            return jsonify({"message": "No text provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/get_text', methods=['GET'])
def get_text():
    try:
        # Đọc văn bản từ file JSON
        text_data = read_text_from_file()
        
        # Nếu có văn bản, trả về và xóa văn bản trong file
        if "text" in text_data and text_data["text"]:
            clear_text_in_file()  # Xóa văn bản trong file JSON
            return jsonify(text_data), 200
        else:
            return jsonify({"message": "No text available"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Hàm lưu hình ảnh vào file JSON
def save_image_to_file(base64_image):
    with open(json_image_file, 'w') as f:
        json.dump({"image": base64_image}, f)
# Hàm đọc hình ảnh từ file JSON
def read_image_from_file():
    try:
        if not os.path.exists(json_image_file):
            return {"image": "No image found in file"}
        with open(json_image_file, 'r') as f:
            content = f.read().strip() 
            if not content:
                return {"image": "No image found in file"}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"image": "No valid data found or file is missing"}

# Hàm xóa hình ảnh trong file JSON
def clear_image_in_file():
    with open(json_image_file, 'w') as f:
        json.dump({"image": ""}, f)
# API để nhận hình ảnh từ client dưới dạng base64
@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()  
        base64_image = data.get('image')  

        if base64_image:
            save_image_to_file(base64_image)  
            return jsonify({"message": "Image received and saved successfully"}), 200
        else:
            return jsonify({"message": "No image data provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# API để lấy hình ảnh từ server dưới dạng base64
@app.route('/get_image', methods=['GET'])
def get_image():
    try:
        image_data = read_image_from_file()
        if "image" in image_data and image_data["image"]:
            image_base64 = image_data["image"]
            clear_image_in_file()  
            return jsonify({"image": image_base64}), 200
        else:
            return jsonify({"message": "No image available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
