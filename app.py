import psycopg2
from flask import Flask, request, jsonify
import base64


# Kết nối đến PostgreSQL
conn = psycopg2.connect(
    dbname="pbl6db", 
    user="pbl6db_user", 
    password="HThN1TO2dBVELOYFdv7aRQK4yNSVTQds", 
    host="dpg-ct2s33btq21c73b7alug-a.singapore-postgres.render.com", 
    port="5432"
)

app = Flask(__name__)

# Tạo bảng nếu chưa tồn tại
def create_all_tables():
    with conn.cursor() as cur:
        # Tạo bảng text_data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS text_data (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL
            );
        """)
        
        # Tạo bảng image_data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image_data (
                id SERIAL PRIMARY KEY,
                image BYTEA NOT NULL
            );
        """)
        
        # Tạo bảng status với trạng thái TRUE/FALSE
        cur.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id SERIAL PRIMARY KEY,
                image_status BOOLEAN DEFAULT TRUE,
                text_status BOOLEAN DEFAULT TRUE
            );
        """)
        
        conn.commit()

# Hàm lưu văn bản vào cơ sở dữ liệu
def save_text_to_db(text):
    with conn.cursor() as cur:
        # Xóa tất cả dữ liệu cũ trong bảng text_data
        cur.execute("DELETE FROM text_data")
        conn.commit()
        # Sau đó, lưu văn bản mới vào bảng
        cur.execute("INSERT INTO text_data (content) VALUES (%s)", (text,))
        conn.commit()

# Hàm đọc văn bản từ cơ sở dữ liệu
def read_text_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT content FROM text_data ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        if result:
            return {"text": result[0]}
        return {"text": ""}

# Hàm lưu hình ảnh vào cơ sở dữ liệu
def save_image_to_db(image_base64):
    with conn.cursor() as cur:
        # Chuyển đổi chuỗi Base64 thành dữ liệu nhị phân
        image_data = base64.b64decode(image_base64)
        
        # Kiểm tra nếu có ảnh cũ trong cơ sở dữ liệu và xóa nếu có
        cur.execute("SELECT COUNT(*) FROM image_data")
        count = cur.fetchone()[0]
        if count > 0:
            cur.execute("DELETE FROM image_data WHERE id = (SELECT id FROM image_data ORDER BY id DESC LIMIT 1)")
            conn.commit()
        
        # Thêm hình ảnh mới vào cơ sở dữ liệu
        cur.execute("INSERT INTO image_data (image) VALUES (%s)", (image_data,))
        conn.commit()

# Hàm đọc hình ảnh từ cơ sở dữ liệu
def read_image_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT image FROM image_data ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        if result:
            return {"image": base64.b64encode(result[0]).decode("utf-8")}
        return {"image": ""}

# Hàm cập nhật trạng thái của image và text
def update_status(image_status, text_status):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO status (image_status, text_status) VALUES (%s, %s)", (image_status, text_status))
        conn.commit()

# API nhận văn bản từ client
@app.route('/send_text', methods=['POST'])
def send_text():
    try:
        data = request.get_json()
        text = data.get('text')
        if text:
            save_text_to_db(text)  # Lưu văn bản vào DB
            update_status(None, True)  # Đặt trạng thái mặc định là TRUE (còn trong DB)
            return jsonify({"message": "Text received successfully", "received_text": text}), 200
        else:
            return jsonify({"message": "No text provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API để lấy văn bản từ cơ sở dữ liệu
@app.route('/get_text', methods=['GET'])
def get_text():
    try:
        text_data = read_text_from_db()
        if "text" in text_data and text_data["text"]:
            return jsonify(text_data), 200
        else:
            return jsonify({"message": ""}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API kiểm tra trạng thái văn bản
@app.route('/check_text', methods=['POST'])
def check_text():
    try:
        data = request.get_json()
        status = data.get('status')
        if status == "success":
            with conn.cursor() as cur:
                # Xóa văn bản nếu nhận thành công
                cur.execute("DELETE FROM text_data WHERE id = (SELECT id FROM text_data ORDER BY id DESC LIMIT 1)")
                conn.commit()
            # Cập nhật trạng thái text_status thành FALSE (đã xóa)
            update_status(None, False)  # Chỉ cập nhật text_status, image_status để None (không thay đổi)
            return jsonify({"message": "Text deleted successfully and status reset"}), 200
        else:
            return jsonify({"message": "No 'success' status provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API nhận hình ảnh từ client (Base64)
@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        image_base64 = data.get('image')  # Dữ liệu ảnh Base64 từ client
        if image_base64:
            save_image_to_db(image_base64)  # Lưu ảnh vào DB
            update_status(True, None)  # Đặt trạng thái mặc định là TRUE (còn trong DB)
            return jsonify({"message": "Image received and saved successfully"}), 200
        else:
            return jsonify({"message": "No image data provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API để lấy hình ảnh từ cơ sở dữ liệu
@app.route('/get_image', methods=['GET'])
def get_image():
    try:
        image_data = read_image_from_db()
        if "image" in image_data and image_data["image"]:
            return jsonify({"image": image_data["image"]}), 200
        else:
            return jsonify({"message": ""}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API kiểm tra trạng thái hình ảnh
@app.route('/check_image', methods=['POST'])
def check_image():
    try:
        data = request.get_json()
        status = data.get('status')
        if status == "success":
            with conn.cursor() as cur:
                # Xóa hình ảnh nếu nhận thành công
                cur.execute("DELETE FROM image_data WHERE id = (SELECT id FROM image_data ORDER BY id DESC LIMIT 1)")
                conn.commit()
            # Cập nhật trạng thái image_status thành FALSE (đã xóa)
            update_status(False, None) 
            return jsonify({"message": "Image deleted successfully and status reset"}), 200
        else:
            return jsonify({"message": "No 'success' status provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Tạo bảng khi chạy lần đầu
    create_all_tables()
    app.run(debug=True)
