
from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

# ==========================
# ĐỌC FILE EXCEL
# ==========================

# Sheet thuật ngữ
df = pd.read_excel(
    "thuatngu.xlsx",
    sheet_name="Thuat ngu hoc vu"
)

df.columns = df.columns.str.strip()

# Sheet học tập
df_hoc = pd.read_excel(
    "thuatngu.xlsx",
    sheet_name="hoc tap"
)

df_hoc.columns = df_hoc.columns.str.strip()

# Danh sách thuật ngữ
ds_thuat_ngu = df["Thuật ngữ"].tolist()


# ==========================
# TRANG CHỦ
# ==========================
@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# TRANG THUẬT NGỮ
# ==========================
@app.route("/vocab")
def vocab():

    return render_template(
        "vocab.html",
        title="ĐỊNH NGHĨA",
        meaning="Hãy nhập hoặc chọn một thuật ngữ ở bên phải.",
        ds_thuat_ngu=ds_thuat_ngu
    )
# ==========================
# TÌM KIẾM TỔNG HỢP (XỬ LÝ ĐIỀU HƯỚNG TRANG)
# ==========================
@app.route("/tim-kiem", methods=["POST"])
def tim_kiem():
    word = request.form["keyword"].lower().strip()

    # 1. Kiểm tra xem từ khóa có nằm trong sheet Thuật ngữ không
    row_vocab = df[df["Thuật ngữ"].str.lower().str.strip() == word]
    if not row_vocab.empty:
        title = row_vocab.iloc[0]["Thuật ngữ"]
        meaning = row_vocab.iloc[0]["định nghĩa"]
        # Lấy lại danh sách thuật ngữ để hiển thị thanh bên trang vocab
        ds_thuat_ngu = df["Thuật ngữ"].dropna().tolist()
        return render_template(
            "vocab.html",
            title=title,
            meaning=meaning,
            ds_thuat_ngu=ds_thuat_ngu
        )

    # 2. Nếu không có ở Thuật ngữ, kiểm tra tiếp trong sheet Học tập
    row_study = df_hoc[df_hoc["Nội dung học"].str.lower().str.strip() == word]
    if not row_study.empty:
        tieu_de = row_study.iloc[0]["Nội dung học"]
        ketqua = row_study.iloc[0]["Phương pháp học"]
        return render_template(
            "study.html",
            tieu_de=tieu_de,
            ketqua=ketqua
        )

    # 3. Nếu hoàn toàn không tìm thấy ở cả 2 nơi
    return render_template(
        "vocab.html",
        title="Không tìm thấy kết quả",
        meaning=f"Từ khóa '{request.form['keyword']}' không có trong hệ thống Thuật ngữ hoặc Học tập.",
        ds_thuat_ngu=df["Thuật ngữ"].dropna().tolist()
    )


# ==========================
# BẤM VÀO THUẬT NGỮ BÊN PHẢI
# ==========================
@app.route("/thuatngu/<tu>")
def thuat_ngu(tu):

    row = df[
        df["Thuật ngữ"].str.lower().str.strip()
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
# GỢI Ý TÌM KIẾM (AJAX) - ĐÃ CẬP NHẬT
# ==========================
@app.route("/suggest")
def suggest():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    # Lấy danh sách từ cả 2 sheet (loại bỏ giá trị trống)
    ds_thuat_ngu = df["Thuật ngữ"].dropna().tolist()
    ds_hoc_tap = df_hoc["Nội dung học"].dropna().tolist()
    
    # Gộp chung hai danh sách lại để tìm kiếm tổng hợp
    ds_tong_hop = list(set(ds_thuat_ngu + ds_hoc_tap))

    # Ưu tiên thuật ngữ bắt đầu bằng q, sau đó chứa q
    starts = [t for t in ds_tong_hop if t and str(t).lower().strip().startswith(q)]
    contains = [t for t in ds_tong_hop if t and q in str(t).lower().strip() and not str(t).lower().strip().startswith(q)]
    
    results = (starts + contains)[:10]  # Trả về tối đa 10 gợi ý tổng hợp
    return jsonify(results)

# ==========================
# TRANG HỌC TẬP
# ==========================
@app.route("/study")
def study():

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

    ket_qua = df_hoc[
        df_hoc["Nội dung học"].str.lower().str.strip()
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
# CHẠY SERVER
# ==========================
if __name__ == "__main__":
    app.run(debug=True)

