from flask import Flask, render_template, request, jsonify, redirect, session
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==========================
# CẤU HÌNH DATABASE
# ==========================
app.secret_key = "fptsupport"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ==========================
# BẢNG USER
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )


with app.app_context():
    db.create_all()


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
