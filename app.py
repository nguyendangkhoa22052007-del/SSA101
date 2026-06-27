from flask import Flask, render_template, request, jsonify, redirect, session
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re  
from markupsafe import Markup
from datetime import datetime

app = Flask(__name__)

# ==========================
# CẤU HÌNH DATABASE & KEY
# ==========================
app.secret_key = "fptsupport"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================
# CÁC MODEL DATABASE
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    security_question = db.Column(db.String(200), nullable=False)
    security_answer = db.Column(db.String(200), nullable=False)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='commenter', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)                                
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now) 
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)     
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)     

# Khởi tạo database tự động
with app.app_context():
    db.create_all()

# ==========================
# ĐỌC FILE EXCEL & CHUẨN HÓA DỮ LIỆU
# ==========================
try:
    df = pd.read_excel("thuatngu.xlsx", sheet_name="Thuat ngu hoc vu")
    df.columns = df.columns.str.strip()
    ds_thuat_ngu = df["Thuật ngữ"].dropna().tolist()

    df_hoc = pd.read_excel("thuatngu.xlsx", sheet_name="hoc tap")
    df_hoc.columns = df_hoc.columns.str.strip()
    ds_hoc_tap = df_hoc["Nội dung học"].dropna().tolist()
except Exception as e:
    print(f"❌ LỖI ĐỌC FILE EXCEL: Tắt file Excel nếu đang mở! Chi tiết: {e}")
    ds_thuat_ngu = []
    ds_hoc_tap = []

# ==========================================================
# HÀM BỔ TRỢ: FORMAT VĂN BẢN THÀNH 3 CARDS
# ==========================================================
def xu_ly_format_html(text_goc):
    if not text_goc or pd.isna(text_goc):
        return ""
    
    text = str(text_goc).strip()
    text = re.sub(r'(?i)<h3>\s*💡?\s*', '', text)
    text = re.sub(r'💡\s*', '', text)
    text = text.replace('</h3>', '')
    text = text.replace('<strong>', '').replace('</strong>', '')
    text = text.replace('\n', '<br>')
    
    text = re.sub(r'(^|<br>)\s*([^:<]+:)', r'\1<strong>\2</strong>', text)
    parts = re.split(r'(?i)(Nội dung học(?: tập)?|Lưu ý quan trọng|Cách học hiệu quả)', text)
    
    if len(parts) == 1:
        return Markup(text)
        
    final_html = '<div class="cards-container">'
    intro = parts[0].strip()
    if intro and intro != '<br>':
        intro = re.sub(r'^(<br>)+|(<br>)+$', '', intro)
        final_html += f'<div class="intro-text">{intro}</div>'
        
    icons = {
        'nội dung học': '📚',
        'nội dung học tập': '📚',
        'lưu ý quan trọng': '⚠️',
        'cách học hiệu quả': '🚀'
    }
    
    for i in range(1, len(parts), 2):
        keyword = parts[i].strip()
        content = parts[i+1].strip()
        content = re.sub(r'^(<br>)+|(<br>)+$', '', content)
        icon = icons.get(keyword.lower(), '📌')
        
        final_html += f'''
        <div class="study-card">
            <div class="card-header-study">
                <h2>
                    <span class="card-icon" style="margin-right: 10px; vertical-align: middle;">{icon}</span><span style="vertical-align: middle;">{keyword}</span>
                </h2>
            </div>
            <div class="card-body-study">
                {content}
            </div>
        </div>
        '''
    final_html += '</div>'
    return Markup(final_html)

# ==========================
# AUTHENTICATION ROUTES
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        security_question = request.form["security_question"]
        security_answer = request.form["security_answer"].strip().lower()

        if password != confirm_password:
            return render_template("register.html", error="❌ Mật khẩu xác nhận không khớp.")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="⚠️ Tên tài khoản đã tồn tại.")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="❌ Email đã được sử dụng.")

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            security_question=security_question,
            security_answer=generate_password_hash(security_answer) 
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["username"] = username
            return redirect("/")

        # Nếu sai mật khẩu hoặc tài khoản, chỉ ở lại trang login và báo lỗi
        return render_template("login.html", error="❌ Sai tài khoản hoặc mật khẩu")
    return render_template("login.html")
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

# ==========================
# MAIN FEATURES
# ==========================
@app.route("/")
def home():
    if "username" not in session:
        return redirect("/login")
    return render_template("index.html", username=session["username"])

@app.route("/vocab")
def vocab():
    if "username" not in session:
        return redirect("/login")
    return render_template(
        "vocab.html",
        title="ĐỊNH NGHĨA",
        meaning="Hãy nhập hoặc chọn một thuật ngữ ở bên phải.",
        ds_thuat_ngu=ds_thuat_ngu,
        username=session["username"]
    )

@app.route("/thuatngu/<tu>")
def thuat_ngu(tu):
    if "username" not in session:
        return redirect("/login")

    row = df[df["Thuật ngữ"].str.lower().str.strip() == tu.lower().strip()]
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
        ds_thuat_ngu=ds_thuat_ngu,
        username=session["username"]
    )

@app.route("/study")
def study():
    if "username" not in session:
        return redirect("/login")
    return render_template(
        "study.html",
        tieu_de="Hỗ trợ học tập",
        ketqua="Hãy chọn một nội dung ở bên phải hoặc thanh tìm kiếm.",
        ds_hoc_tap=ds_hoc_tap, 
        username=session["username"]
    )

@app.route("/hoc/<mon>")
def hoc(mon):
    if "username" not in session:
        return redirect("/login")

    ket_qua = df_hoc[df_hoc["Nội dung học"].str.lower().str.strip() == mon.lower().strip()]
    if not ket_qua.empty:
        noidung = ket_qua.iloc[0]["Phương pháp học"]
        noidung = xu_ly_format_html(noidung)
    else:
        noidung = "Chưa có dữ liệu."

    return render_template(
        "study.html",
        tieu_de=mon,
        ketqua=noidung,
        ds_hoc_tap=ds_hoc_tap,
        username=session["username"]
    )

# ==========================
# TÌM KIẾM TỔNG HỢP & GỢI Ý
# ==========================
@app.route("/tim-kiem", methods=["POST"])
def tim_kiem():
    if "username" not in session:
        return redirect("/login")

    raw_keyword = request.form.get("keyword", "")
    word = raw_keyword.lower().strip()

    row_vocab = df[df["Thuật ngữ"].str.lower().str.strip() == word]
    if not row_vocab.empty:
        title = row_vocab.iloc[0]["Thuật ngữ"]
        meaning = row_vocab.iloc[0]["định nghĩa"]
        return render_template(
            "vocab.html",
            title=title,
            meaning=meaning,
            ds_thuat_ngu=ds_thuat_ngu,
            username=session["username"]
        )

    row_study = df_hoc[df_hoc["Nội dung học"].str.lower().str.strip() == word]
    if not row_study.empty:
        tieu_de = row_study.iloc[0]["Nội dung học"]
        ketqua = row_study.iloc[0]["Phương pháp học"]
        ketqua = xu_ly_format_html(ketqua)
        return render_template(
            "study.html",
            tieu_de=tieu_de,
            ketqua=ketqua,
            ds_hoc_tap=ds_hoc_tap,
            username=session["username"]
        )

    return render_template(
        "vocab.html",
        title="Không tìm thấy kết quả",
        meaning=f"Từ khóa '{raw_keyword}' không có trong hệ thống.",
        ds_thuat_ngu=ds_thuat_ngu,
        username=session["username"]
    )

@app.route("/suggest")
def suggest():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    ds_tong_hop = list(set(ds_thuat_ngu + ds_hoc_tap))
    starts = [t for t in ds_tong_hop if t and str(t).lower().startswith(q)]
    contains = [t for t in ds_tong_hop if t and q in str(t).lower() and not str(t).lower().startswith(q)]

    return jsonify((starts + contains)[:10])

# ==========================
# DIỄN ĐÀN TRONG TRƯỜNG
# ==========================
@app.route("/forum", methods=["GET", "POST"])
def forum():
    if "username" not in session:
        session["username"] = "SinhVienAnDanh"

    current_user = User.query.filter_by(username=session["username"]).first()
    if not current_user:
        current_user = User(
            username=session["username"],
            email="anonymous@luscc.local",
            password=generate_password_hash("123456"),
            security_question="None",
            security_answer="None"
        )
        db.session.add(current_user)
        db.session.commit()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if title and content:
            new_post = Post(title=title, content=content, author=current_user)
            db.session.add(new_post)
            db.session.commit()
            return redirect("/forum")

    all_posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template("forum.html", posts=all_posts, username=session["username"])

@app.route("/forum/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "username" not in session:
        return redirect("/login")
        
    current_user = User.query.filter_by(username=session["username"]).first()
    comment_content = request.form.get("comment_content", "").strip()
    
    if comment_content:
        new_comment = Comment(content=comment_content, post_id=post_id, user_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()
        
    return redirect("/forum")

# ==========================
# QUẢN LÝ TÀI KHOẢN & ĐỔI MẬT KHẨU
# ==========================
@app.route("/account")
def account():
    if "username" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["username"]).first()
    return render_template(
        "account.html",
        username=user.username,
        email=user.email,
        security_question=user.security_question
    )

@app.route("/change-password", methods=["POST"])
def change_password():
    if "username" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["username"]).first()
    old_password = request.form["old_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if not check_password_hash(user.password, old_password):
        return render_template(
            "account.html",
            username=user.username, email=user.email, security_question=user.security_question,
            error="❌ Mật khẩu cũ không đúng."
        )

    if new_password != confirm_password:
        return render_template(
            "account.html",
            username=user.username, email=user.email, security_question=user.security_question,
            error="❌ Mật khẩu xác nhận không khớp."
        )

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return render_template(
        "account.html",
        username=user.username, email=user.email, security_question=user.security_question,
        success="✅ Đổi mật khẩu thành công!"
    )

# ==========================================================
# ROUTE QUÊN MẬT KHẨU (NẰM TRÊN APP.RUN LÀ CHUẨN)
# ==========================================================
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "username" in session:
        return redirect("/")

    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username", "").strip()

        # HÀNH ĐỘNG 1: KIỂM TRA USERNAME ĐỂ LẤY CÂU HỎI BẢO MẬT
        if action == "check_user":
            user = User.query.filter_by(username=username).first()
            if not user:
                return render_template("forgot_password.html", error="❌ Tên tài khoản không tồn tại trên hệ thống.")
            
            return render_template(
                "forgot_password.html", 
                username=username, 
                security_question=user.security_question
            )

        # HÀNH ĐỘNG 2: XÁC THỰC CÂU TRẢ LỜI VÀ ĐỔI MẬT KHẨU MỚI
        elif action == "reset_password":
            user = User.query.filter_by(username=username).first()
            if not user:
                return render_template("forgot_password.html", error="❌ Có lỗi xảy ra, vui lòng thử lại.")

            answer_input = request.form.get("security_answer", "").strip().lower()
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            # NẾU TRẢ LỜI SAI: Giữ nguyên form, truyền lại câu hỏi bảo mật kèm lỗi đỏ rõ ràng
            if not check_password_hash(user.security_answer, answer_input):
                return render_template(
                    "forgot_password.html", 
                    username=username, 
                    security_question=user.security_question,
                    error="❌ Câu trả lời bảo mật không chính xác!"
                )

            if new_password != confirm_password:
                return render_template(
                    "forgot_password.html", 
                    username=username, 
                    security_question=user.security_question,
                    error="❌ Mật khẩu mới xác nhận không khớp."
                )

            # Hợp lệ -> Đổi mật khẩu thành công
            user.password = generate_password_hash(new_password)
            db.session.commit()
            
            return render_template("login.html", success="✅ Đổi mật khẩu thành công! Hãy đăng nhập bằng mật khẩu mới.")

    return render_template("forgot_password.html")

# ĐỂ CHẠY SERVER CUỐI FILE
if __name__ == "__main__":
    app.run(debug=True)
