from flask import Flask, render_template, request, jsonify, redirect, session
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re  # THÊM THƯ VIỆN REGEX ĐỂ XỬ LÝ CHUỖI VĂN BẢN

app = Flask(__name__)

# ==========================
# CẤU HÌNH DATABASE
# ==========================
app.secret_key = "fptsupport"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


from datetime import datetime

# ==========================
# BẢNG USER (Cấu hình chuẩn)
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Khai báo mối quan hệ để lấy danh sách bài đăng của user dễ dàng
    posts = db.relationship('Post', backref='author', lazy=True)
    # Thêm dòng này để liên kết với các bình luận của user
    comments = db.relationship('Comment', backref='commenter', lazy=True)

# ==========================
# BẢNG POST (Diễn đàn)
# ==========================
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Thêm dòng này để lấy danh sách bình luận của bài viết dễ dàng
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

# ==========================
# BẢNG COMMENT (Mới thêm)
# ==========================
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)                                # Nội dung bình luận
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Thời gian bình luận
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)     # Bình luận thuộc bài viết nào
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)     # Ai là người bình luận
# Đảm bảo tạo bảng (Giữ nguyên hoặc đưa xuống dưới cùng trước app.run)
with app.app_context():
    db.create_all()


# ==========================
# ROUTE DIỄN ĐÀN (FORUM)
# ==========================
@app.route("/forum", methods=["GET", "POST"])
def forum():
    # Cơ chế "Bảo hiểm": Nếu chưa đăng nhập, tự động tạo/gán tài khoản ẩn danh để không bị văng lỗi
    if "username" not in session:
        session["username"] = "SinhVienAnDanh"

    # Tìm user hiện tại trong Database
    current_user = User.query.filter_by(username=session["username"]).first()
    
    # Nếu tài khoản (kể cả ẩn danh) chưa tồn tại trong Database, tự tạo mới luôn
    if not current_user:
        current_user = User(username=session["username"], password=generate_password_hash("123456"))
        db.session.add(current_user)
        db.session.commit()

    # Xử lý khi sinh viên nhấn nút "Đăng bài lên diễn đàn"
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        
        if title and content:
            # Tạo bài đăng mới liên kết với user hiện tại thông qua biến author
            new_post = Post(title=title, content=content, author=current_user)
            db.session.add(new_post)
            db.session.commit()
            return redirect("/forum")

    # Lấy toàn bộ bài viết từ mới nhất tới cũ nhất để hiển thị ra giao diện
    all_posts = Post.query.order_by(Post.date_posted.desc()).all()
    
    return render_template(
        "forum.html",
        posts=all_posts,
        username=session["username"]
    )
# (Giữ nguyên đoạn db.create_all() phía dưới của bạn để Flask tự tạo bảng mới này vào database.db)
# ==========================
# ROUTE XỬ LÝ BÌNH LUẬN
# ==========================
@app.route("/forum/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "username" not in session:
        return redirect("/login")
        
    current_user = User.query.filter_by(username=session["username"]).first()
    comment_content = request.form.get("comment_content", "").strip()
    
    if comment_content:
        # Tạo đối tượng bình luận mới đi kèm thông tin bài viết và người dùng
        new_comment = Comment(content=comment_content, post_id=post_id, commenter=current_user)
        db.session.add(new_comment)
        db.session.commit()
        
    return redirect("/forum")
# ==========================
# ĐỌC FILE EXCEL
# ==========================
df = pd.read_excel(
    "thuatngu.xlsx",
    sheet_name="Thuat ngu hoc vu"
)

df.columns = df.columns.str.strip()

df_hoc = pd.read_excel(
    "thuatngu.xlsx",
    sheet_name="hoc tap"
)

df_hoc.columns = df_hoc.columns.str.strip()

ds_thuat_ngu = df["Thuật ngữ"].dropna().tolist()


# ==========================================================
# HÀM BỔ TRỢ: TỰ ĐỘNG FORMAT VĂN BẢN SANG HTML (MỚI THÊM)
# ==========================================================
def xu_ly_format_html(text_goc):
    if not text_goc or pd.isna(text_goc):
        return ""
    
    text = str(text_goc).strip()
    
    # 1. Tự động nhận diện đề mục lớn chuyển thành thẻ h3
    cac_muc_chinh = ["Nội dung học", "Lưu ý quan trọng", "Cách học hiệu quả"]
    for muc in cac_muc_chinh:
        text = text.replace(muc, f"<h3>💡 {muc}</h3>")
        
    # 2. Tự động in đậm các từ khóa nhỏ đứng trước dấu hai chấm ở đầu dòng
    text = re.sub(r'(^|\n)([^:\n]+:)', r'\1<strong>\2</strong>', text)
    
    # 3. Ép xuống dòng bằng cách đổi \n thành <br>
    text = text.replace("\n", "<br>")
    
    return text


# ==========================
# ĐĂNG KÝ
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        # Tên tài khoản đã tồn tại
        if user:

            return render_template(
                "register.html",
                error="⚠️ Tên tài khoản đã tồn tại"
            )

        new_user = User(
            username=username,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ==========================
# ĐĂNG NHẬP
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
                user.password,
                password):

            session["username"] = username

            return redirect("/")

        return render_template(
            "login.html",
            error="❌ Sai tài khoản hoặc mật khẩu"
        )

    return render_template("login.html")


# ==========================
# ĐĂNG XUẤT
# ==========================
@app.route("/logout")
def logout():

    session.pop("username", None)

    return redirect("/login")


# ==========================
# TRANG CHỦ
# ==========================
@app.route("/")
def home():

    if "username" not in session:
        return redirect("/login")

    return render_template(
        "index.html",
        username=session["username"]
    )


# ==========================
# TRANG THUẬT NGỮ
# ==========================
@app.route("/vocab")
def vocab():

    if "username" not in session:
        return redirect("/login")

    return render_template(
        "vocab.html",
        title="ĐỊNH NGHĨA",
        meaning="Hãy nhập hoặc chọn một thuật ngữ ở bên phải.",
        ds_thuat_ngu=ds_thuat_ngu
    )


# ==========================
# TÌM KIẾM
# ==========================
@app.route("/tim-kiem", methods=["POST"])
def tim_kiem():

    if "username" not in session:
        return redirect("/login")

    word = request.form["keyword"].lower().strip()

    row_vocab = df[
        df["Thuật ngữ"]
        .str.lower()
        .str.strip() == word
    ]

    if not row_vocab.empty:

        title = row_vocab.iloc[0]["Thuật ngữ"]

        meaning = row_vocab.iloc[0]["định nghĩa"]

        return render_template(
            "vocab.html",
            title=title,
            meaning=meaning,
            ds_thuat_ngu=ds_thuat_ngu
        )

    row_study = df_hoc[
        df_hoc["Nội dung học"]
        .str.lower()
        .str.strip() == word
    ]

    if not row_study.empty:

        tieu_de = row_study.iloc[0]["Nội dung học"]

        ketqua = row_study.iloc[0]["Phương pháp học"]
        
        # SỬA ĐỔI: Xử lý format dấu xuống dòng và từ khóa trước khi render sang study.html
        ketqua = xu_ly_format_html(ketqua)

        return render_template(
            "study.html",
            tieu_de=tieu_de,
            ketqua=ketqua
        )

    return render_template(
        "vocab.html",
        title="Không tìm thấy kết quả",
        meaning=f"Từ khóa '{request.form['keyword']}' không có trong hệ thống.",
        ds_thuat_ngu=ds_thuat_ngu
    )


# ==========================
# BẤM THUẬT NGỮ
# ==========================
@app.route("/thuatngu/<tu>")
def thuat_ngu(tu):

    if "username" not in session:
        return redirect("/login")

    row = df[
        df["Thuật ngữ"]
        .str.lower()
        .str.strip()
        == tu.lower().strip()
    ]

    if not row.empty:

        title = row.iloc[0]["Thuật ngữ"]

        meaning = row.iloc[0]["định nghĩa"]

    else:

        title = "Không tìm thấy"

        meaning = "Thuật ngữ này chưa có trong hệ thống."

    return render_template(
        "vocab.html",
        title=title,
        meaning=meaning,
        ds_thuat_ngu=ds_thuat_ngu
    )


# ==========================
# GỢI Ý
# ==========================
@app.route("/suggest")
def suggest():

    q = request.args.get(
        "q",
        ""
    ).strip().lower()

    if not q:
        return jsonify([])

    ds_hoc_tap = df_hoc[
        "Nội dung học"
    ].dropna().tolist()

    ds_tong_hop = list(
        set(ds_thuat_ngu + ds_hoc_tap)
    )

    starts = [
        t for t in ds_tong_hop
        if t and str(t).lower().startswith(q)
    ]

    contains = [
        t for t in ds_tong_hop
        if t and q in str(t).lower()
        and not str(t).lower().startswith(q)
    ]

    return jsonify(
        (starts + contains)[:10]
    )


# ==========================
# TRANG HỌC TẬP
# ==========================
@app.route("/study")
def study():

    if "username" not in session:
        return redirect("/login")

    return render_template(
        "study.html",
        tieu_de="Hỗ trợ học tập",
        ketqua="Hãy chọn một nội dung ở bên trái."
    )


# ==========================
# CHỌN NỘI DUNG HỌC
# ==========================
@app.route("/hoc/<mon>")
def hoc(mon):

    if "username" not in session:
        return redirect("/login")

    ket_qua = df_hoc[
        df_hoc["Nội dung học"]
        .str.lower()
        .str.strip()
        == mon.lower().strip()
    ]

    if not ket_qua.empty:

        noidung = ket_qua.iloc[0]["Phương pháp học"]
        
        # SỬA ĐỔI: Chạy qua hàm xử lý format để bẻ dòng và in đậm từ khóa tự động
        noidung = xu_ly_format_html(noidung)

    else:

        noidung = "Chưa có dữ liệu."

    return render_template(
        "study.html",
        tieu_de=mon,
        ketqua=noidung
    )

# ==========================
# TRANG TÀI KHOẢN
# ==========================
@app.route("/account")
def account():

    if "username" not in session:
        return redirect("/login")

    return render_template(
        "account.html",
        username=session["username"]
    )
# ==========================
# CHẠY SERVER
# ==========================
if __name__ == "__main__":
    app.run(debug=True)
