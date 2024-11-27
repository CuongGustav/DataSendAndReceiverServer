import psycopg2
from flask import Flask, request, jsonify, send_from_directory
import base64
import os
from flask_cors import CORS


# Kết nối đến PostgreSQL
conn = psycopg2.connect(
    dbname="dbpbl6", 
    user="dbpbl6_user", 
    password="Be3v5Wmax65T6Jf05iXfHugcm3hnfkOD", 
    host="dpg-ct3hdrrtq21c738rtdrg-a.singapore-postgres.render.com", 
    port="5432"
)



app = Flask(__name__)
CORS(app)

# Thư mục chứa ảnh
UPLOAD_FOLDER = 'statics'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Cập nhật cấu hình của Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tạo bảng nếu chưa tồn tại
def create_all_tables():
    with conn.cursor() as cur:
        # Tạo bảng text_data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS text_data (
                id SERIAL PRIMARY KEY,
                english TEXT NOT NULL,
                vietnamese TEXT NOT NULL
            );
        """)
        
        # Tạo bảng image_data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image_data (
                id SERIAL PRIMARY KEY,
                image_path TEXT NOT NULL
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
def save_text_to_db(english_text, vietnamese_text):
    with conn.cursor() as cur:
        # Xóa tất cả dữ liệu cũ trong bảng text_data
        cur.execute("DELETE FROM text_data")
        conn.commit()
        # Sau đó, lưu văn bản mới vào bảng
        cur.execute(
            "INSERT INTO text_data (english, vietnamese) VALUES (%s, %s)",
            (english_text, vietnamese_text)
        )
        conn.commit()


# Hàm đọc văn bản từ cơ sở dữ liệu
def read_text_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT english, vietnamese FROM text_data ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        if result:
            return {"english": result[0], "vietnamese": result[1]}
        return {"english": "", "vietnamese": ""}


# Hàm lưu hình ảnh vào cơ sở dữ liệu và thư mục statics
def save_image_to_db(image_file):
    try:
        with conn.cursor() as cur:
            # Kiểm tra nếu có ảnh cũ trong cơ sở dữ liệu và xóa nếu có
            cur.execute("SELECT COUNT(*) FROM image_data")
            count = cur.fetchone()[0]
            if count > 0:
                cur.execute("SELECT image_path FROM image_data ORDER BY id DESC LIMIT 1")
                result = cur.fetchone()
                if result:
                    old_image_path = result[0]
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                cur.execute("DELETE FROM image_data WHERE id = (SELECT id FROM image_data ORDER BY id DESC LIMIT 1)")
            
            # Lưu ảnh mới vào thư mục statics
            image_filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

            # Lưu đường dẫn ảnh mới vào cơ sở dữ liệu
            cur.execute("INSERT INTO image_data (image_path) VALUES (%s)", (image_path,))
            conn.commit()
    except Exception as e:
        conn.rollback()  # ROLL BACK TRANSACTION nếu có lỗi
        raise e  # Đẩy lỗi ra ngoài để API xử lý



# Hàm đọc hình ảnh từ cơ sở dữ liệu
def read_image_from_db():
    with conn.cursor() as cur:
        cur.execute("SELECT image_path FROM image_data ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        if result:
            return {"image_path": result[0]}
        return {"image_path": ""}

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
        english_text = data.get('english')
        vietnamese_text = data.get('vietnamese')
        if english_text and vietnamese_text:
            save_text_to_db(english_text, vietnamese_text)  # Lưu văn bản vào DB
            update_status(None, True)  # Đặt trạng thái mặc định là TRUE (còn trong DB)
            return jsonify({
                "message": "Text received successfully",
                "received_text": {"english": english_text, "vietnamese": vietnamese_text}
            }), 200
        else:
            return jsonify({"message": "Both English and Vietnamese texts are required"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API để lấy văn bản từ cơ sở dữ liệu
@app.route('/get_text', methods=['GET'])
def get_text():
    try:
        text_data = read_text_from_db()
        if "english" in text_data and text_data["english"] and "vietnamese" in text_data and text_data["vietnamese"]:
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

# API nhận hình ảnh từ client
@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        image_file = request.files.get('image')  # Lấy tệp hình ảnh từ client
        if image_file:
            save_image_to_db(image_file)  # Lưu ảnh vào DB và thư mục statics
            return jsonify({"message": "Image received and saved successfully"}), 200
        else:
            return jsonify({"message": "No image file provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API để lấy hình ảnh từ thư mục statics
@app.route('/get_image', methods=['GET'])
def get_image():
    try:
        image_data = read_image_from_db()
        if "image_path" in image_data and image_data["image_path"]:
            # Trả về ảnh từ thư mục statics
            image_path = image_data["image_path"]
            filename = os.path.basename(image_path)
            return send_from_directory(UPLOAD_FOLDER, filename), 200
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
                # Lấy đường dẫn ảnh mới nhất trong cơ sở dữ liệu
                cur.execute("SELECT image_path FROM image_data ORDER BY id DESC LIMIT 1")
                result = cur.fetchone()
                if result:
                    image_path = result[0]
                    # Xóa ảnh khỏi thư mục statics
                    if os.path.exists(image_path):
                        os.remove(image_path)

                    # Xóa hình ảnh trong cơ sở dữ liệu
                    cur.execute("DELETE FROM image_data WHERE id = (SELECT id FROM image_data ORDER BY id DESC LIMIT 1)")
                    conn.commit()
                    
            return jsonify({"message": "Image deleted successfully"}), 200
        else:
            return jsonify({"message": "No 'success' status provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Tạo bảng khi chạy lần đầu
    create_all_tables()
    app.run(debug=True)
