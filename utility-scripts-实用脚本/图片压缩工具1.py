import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import io
import os
import math

# 需要安装 tkinterDnD2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("依赖缺失", "请先安装 tkinterDnD2:\n\npip install tkinterdnd2")
    raise

class ImageCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能图片转换与压缩工具")
        self.root.geometry("900x500")
        self.root.configure(bg="#f8fafc")
        
        self.source_image = None
        self.result_image = None
        self.original_path = ""
        self.original_size = 0
        
        # 左侧：拖拽 + 预览
        left_frame = tk.Frame(root, bg="#f8fafc")
        left_frame.pack(side="left", padx=20, pady=20)
        
        self.drop_canvas = tk.Canvas(left_frame, width=300, height=300, bg="#ffffff")
        self.drop_canvas.pack()
        self.drop_canvas.create_rectangle(5, 5, 295, 295, dash=(5, 3), outline="#cbd5e1", width=2)
        self.drop_canvas.create_text(150, 150, text="点击或拖拽图片到这里\n支持 JPG, PNG, WebP, BMP", font=("Arial", 12), justify="center", fill="#374151", tags="drop_text")
        
        self.drop_canvas.bind("<Button-1>", self.browse_file)
        
        # TkinterDnD 拖拽支持
        self.drop_canvas.drop_target_register(DND_FILES)
        self.drop_canvas.dnd_bind('<<Drop>>', self.handle_drop)
        
        self.original_info = tk.Label(left_frame, text="", bg="#f8fafc", font=("Arial", 10))
        self.original_info.pack(pady=5)
        
        # 预览图
        self.preview_canvas = tk.Label(left_frame, bg="#e2e8f0", width=40, height=15)
        self.preview_canvas.pack(pady=5)
        
        # 右侧：设置 & 操作
        right_frame = tk.Frame(root, bg="#f8fafc")
        right_frame.pack(side="right", fill="y", padx=20, pady=20)
        
        tk.Label(right_frame, text="导出格式", bg="#f8fafc", font=("Arial", 10)).pack(pady=5)
        self.format_var = tk.StringVar(value="JPEG")
        tk.OptionMenu(right_frame, self.format_var, "JPEG", "PNG", "WEBP").pack(pady=5)
        
        tk.Label(right_frame, text="目标大小 (KB)", bg="#f8fafc", font=("Arial", 10)).pack(pady=5)
        self.size_var = tk.IntVar(value=100)
        self.size_scale = tk.Scale(right_frame, from_=10, to=2000, orient="horizontal", variable=self.size_var, length=300)
        self.size_scale.pack(pady=5)
        
        self.target_label = tk.Label(right_frame, text="目标大小: 100 KB", bg="#f8fafc", font=("Arial", 10), fg="#2563eb")
        self.target_label.pack()
        self.size_var.trace("w", lambda *args: self.target_label.config(text=f"目标大小: {self.size_var.get()} KB"))
        
        tk.Button(right_frame, text="开始转换", command=self.convert_image, width=30, bg="#3b82f6", fg="white").pack(pady=10)
        
        self.result_info = tk.Label(right_frame, text="", bg="#f8fafc", font=("Arial", 10))
        self.result_info.pack(pady=5)
        
        self.save_button = tk.Button(right_frame, text="保存结果", command=self.save_image, width=30, state="disabled", bg="#10b981", fg="white")
        self.save_button.pack(pady=10)

    def browse_file(self, event=None):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if path:
            self.load_image(path)
    
    def handle_drop(self, event):
        # event.data 返回字符串，Windows 拖拽可能带大括号
        path = event.data.strip('{}')
        if os.path.isfile(path):
            self.load_image(path)
    
    def load_image(self, path):
        try:
            self.source_image = Image.open(path).convert("RGB")
            self.original_path = path
            self.original_size = os.path.getsize(path) / 1024
            self.show_preview(self.source_image)
            self.original_info.config(text=f"{self.source_image.width}x{self.source_image.height} | {self.original_size:.1f} KB")
            self.result_info.config(text="")
            self.save_button.config(state="disabled")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
    
    def show_preview(self, img):
        img_copy = img.copy()
        img_copy.thumbnail((300, 300))
        self.tk_image = ImageTk.PhotoImage(img_copy)
        self.preview_canvas.config(image=self.tk_image)
    
    def convert_image(self):
        if not self.source_image:
            messagebox.showwarning("提示", "请先选择图片！")
            return
        
        target_kb = self.size_var.get()
        fmt = self.format_var.get().upper()
        img = self.source_image.copy()
        
        # 迭代压缩函数
        self.result_image = self.compress_to_target(img, fmt, target_kb)
        
        if self.result_image is None:
            messagebox.showerror("失败", "无法压缩到目标大小")
            return
        
        self.show_preview(self.result_image)
        actual_size = self.get_image_size(self.result_image, fmt)
        diff = actual_size - target_kb
        color = "green" if abs(diff) < target_kb * 0.1 else "orange"
        self.result_info.config(text=f"实际大小: {actual_size:.1f} KB | 偏差率: {diff:+.1f} KB", fg=color)
        self.save_button.config(state="normal")
    
    def compress_to_target(self, img, fmt, target_kb):
        fmt = "JPEG" if fmt=="JPG" else fmt
        for _ in range(15):  # 最大迭代次数
            buffer = io.BytesIO()
            if fmt in ["JPEG", "WEBP"]:
                # 尝试不同 quality
                quality = 95
                img.save(buffer, format=fmt, quality=quality)
                current_size = buffer.getbuffer().nbytes / 1024
                if current_size <= target_kb:
                    return img
                # 用二分法缩放
                scale_factor = math.sqrt(target_kb / current_size)
                new_w = max(1, int(img.width * scale_factor))
                new_h = max(1, int(img.height * scale_factor))
                img = img.resize((new_w, new_h), Image.LANCZOS)  # <- Pillow 10+ 兼容
            elif fmt == "PNG":
                buffer = io.BytesIO()
                img.save(buffer, format="PNG", optimize=True)
                current_size = buffer.getbuffer().nbytes / 1024
                if current_size <= target_kb:
                    return img
                scale_factor = math.sqrt(target_kb / current_size)
                new_w = max(1, int(img.width * scale_factor))
                new_h = max(1, int(img.height * scale_factor))
                img = img.resize((new_w, new_h), Image.LANCZOS)
        return img
    
    def get_image_size(self, img, fmt):
        buffer = io.BytesIO()
        fmt = "JPEG" if fmt=="JPG" else fmt
        if fmt in ["JPEG", "WEBP"]:
            img.save(buffer, format=fmt, quality=85)
        else:
            img.save(buffer, format=fmt)
        return buffer.getbuffer().nbytes / 1024
    
    def save_image(self):
        if not self.result_image:
            return
        ext = self.format_var.get().lower()
        save_path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(f"{ext.upper()} files", f"*.{ext}")])
        if save_path:
            fmt = "JPEG" if self.format_var.get()=="JPG" else self.format_var.get()
            self.result_image.save(save_path, format=fmt)
            messagebox.showinfo("保存成功", f"图片已保存到 {save_path}")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageCompressorApp(root)
    root.mainloop()
