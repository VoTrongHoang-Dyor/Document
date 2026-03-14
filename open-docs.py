import webbrowser
import os

# Danh sách các tệp tài liệu HTML của TeraChat
docs = [
    "BusinessPlan.html",
    "Core_Spec.html",
    "Design.html",
    "Feature_Spec.html",
    "Function.html",
    "Introduction.html",
    "Web_Marketplace.html"
]

def open_documentation():
    # Lấy đường dẫn tuyệt đối của thư mục chứa script này
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"🚀 Đang khởi động {len(docs)} tài liệu TeraChat...")
    
    for doc in docs:
        file_path = os.path.join(base_dir, doc)
        if os.path.exists(file_path):
            webbrowser.open(f"file://{file_path}")
            print(f"✅ Đã mở: {doc}")
        else:
            print(f"❌ Không tìm thấy: {doc}")

if __name__ == "__main__":
    open_documentation()
