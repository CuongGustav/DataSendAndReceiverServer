import psycopg2
from flask import Flask, request, jsonify, send_from_directory
import os
from flask_cors import CORS

# Kết nối đến PostgreSQL
conn = psycopg2.connect(
    dbname="pbl6database", 
    user="pbl6database_user", 
    password="jmlxM8qXZ2w5sX94Oe2jFw5b2gP6HyVJ", 
    host="dpg-ctj712rqf0us7399n5mg-a.singapore-postgres.render.com", 
    port="5432"
)

app = Flask(__name__)
CORS(app)

# Thư mục chứa ảnh
UPLOAD_FOLDER = 'statics'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tạo bảng nếu chưa tồn tại
def create_all_tables():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS text (
                id SERIAL PRIMARY KEY,
                english TEXT NOT NULL,
                vietnamese TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image (
                id SERIAL PRIMARY KEY,
                image_path TEXT NOT NULL
            );
        """)
        conn.commit()

# Lưu văn bản vào cơ sở dữ liệu
def save_text_to_db(english_text, vietnamese_text):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM text")  # Xóa dữ liệu cũ
        cur.execute(
            "INSERT INTO text (english, vietnamese) VALUES (%s, %s)",
            (english_text, vietnamese_text)
        )
        conn.commit()

# Đọc văn bản từ cơ sở dữ liệu
def read_text_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT english, vietnamese FROM text ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        return {"english": result[0], "vietnamese": result[1]} if result else {"english": "", "vietnamese": ""}

# Lưu hình ảnh vào cơ sở dữ liệu và thư mục
def save_image_to_db(image_file):
    with conn.cursor() as cur:
        cur.execute("SELECT image_path FROM image ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        if result:
            old_image_path = result[0]
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
            cur.execute("DELETE FROM image WHERE id = (SELECT id FROM image ORDER BY id DESC LIMIT 1)")

        image_filename = image_file.filename
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image_file.save(image_path)

        cur.execute("INSERT INTO image (image_path) VALUES (%s)", (image_path,))
        conn.commit()

# Đọc hình ảnh từ cơ sở dữ liệu
def read_image_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT image_path FROM image ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        return {"image_path": result[0]} if result else {"image_path": ""}

# API nhận văn bản từ client
@app.route('/send_text', methods=['POST'])
def send_text():
    try:
        data = request.get_json()
        english_text = data.get('english')
        vietnamese_text = data.get('vietnamese')
        if not (english_text and vietnamese_text):
            return jsonify({"message": "Both English and Vietnamese texts are required"}), 400

        save_text_to_db(english_text, vietnamese_text)
        return jsonify({
            "message": "Text received successfully",
            "received_text": {"english": english_text, "vietnamese": vietnamese_text}
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API lấy văn bản từ cơ sở dữ liệu
@app.route('/get_text', methods=['GET'])
def get_text():
    try:
        text = read_text_from_db()
        if text["english"]:
            return jsonify(text), 200
        return jsonify({"message": "No text available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API xóa văn bản
@app.route('/delete_text', methods=['DELETE'])
def delete_text():
    try:
        data = request.get_json()
        if data.get('status') == "success":
            with conn.cursor() as cur:
                cur.execute("DELETE FROM text")
                conn.commit()
            return jsonify({"message": "Text deleted successfully"}), 200
        return jsonify({"message": "Invalid status"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API nhận hình ảnh từ client
@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({"message": "No image file provided"}), 400

        save_image_to_db(image_file)
        return jsonify({"message": "Image received and saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API lấy hình ảnh từ cơ sở dữ liệu
@app.route('/get_image', methods=['GET'])
def get_image():
    try:
        image = read_image_from_db()
        if image["image_path"]:
            filename = os.path.basename(image["image_path"])
            return send_from_directory(UPLOAD_FOLDER, filename), 200
        return jsonify({"message": "No image available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API xóa hình ảnh
@app.route('/delete_image', methods=['DELETE'])
def delete_image():
    try:
        data = request.get_json()
        if data.get('status') == "success":
            with conn.cursor() as cur:
                cur.execute("SELECT image_path FROM image ORDER BY id DESC LIMIT 1")
                result = cur.fetchone()
                if result and os.path.exists(result[0]):
                    os.remove(result[0])
                cur.execute("DELETE FROM image")
                conn.commit()
            return jsonify({"message": "Image deleted successfully"}), 200
        return jsonify({"message": "Invalid status"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    create_all_tables()
    app.run(debug=True)
