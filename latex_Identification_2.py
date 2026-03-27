

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw
import threading, queue, time
import numpy as np

from pix2tex.cli import LatexOCR
from ultralytics import YOLO

# ================= 初始化模型 =================
ocr_model = LatexOCR()
detector = YOLO("yolov8n.pt")  # 可替换为公式检测模型


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI公式识别系统（终极版）")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0f172a")

        self.queue = queue.Queue()

        self.build_ui()
        self.root.after(100, self.loop)

    # ================= UI =================
    def build_ui(self):
        top = tk.Frame(self.root, bg="#0f172a")
        top.pack(pady=10)

        def btn(text, cmd):
            return tk.Button(top, text=text, command=cmd,
                             bg="#1e293b", fg="white",
                             activebackground="#334155",
                             relief="flat", padx=10)

        btn("📂 导入", self.load).pack(side=tk.LEFT, padx=5)
        btn("📸 截图", self.screenshot).pack(side=tk.LEFT, padx=5)
        btn("📋 复制", self.copy).pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(self.root, text="Ready",
                               bg="#0f172a", fg="#38bdf8")
        self.status.pack()

        self.canvas = tk.Canvas(self.root, bg="#020617", height=350, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text = scrolledtext.ScrolledText(self.root, height=8,
                                              bg="#020617", fg="#e2e8f0",
                                              insertbackground="white")
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ================= 主循环 =================
    def loop(self):
        try:
            while True:
                func, args = self.queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        self.root.after(100, self.loop)

    def ui(self, func, *args):
        self.queue.put((func, args))

    # ================= 功能 =================
    def load(self):
        path = filedialog.askopenfilename()
        if not path: return
        img = Image.open(path)
        self.process(img)

    def screenshot(self):
        self.root.withdraw()
        time.sleep(0.2)

        top = tk.Toplevel()
        top.attributes("-fullscreen", True)
        top.attributes("-alpha", 0.3)
        canvas = tk.Canvas(top, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        start = [0,0]
        rect=None

        def down(e): start[0],start[1]=e.x,e.y

        def move(e):
            nonlocal rect
            if rect: canvas.delete(rect)
            rect=canvas.create_rectangle(start[0],start[1],e.x,e.y,outline="cyan",width=2)

        def up(e):
            x1,y1=start
            x2,y2=e.x,e.y
            top.destroy()
            self.root.deiconify()

            img = ImageGrab.grab((min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)))
            self.process(img)

        from PIL import ImageGrab
        canvas.bind("<Button-1>",down)
        canvas.bind("<B1-Motion>",move)
        canvas.bind("<ButtonRelease-1>",up)
        top.bind("<Escape>",lambda e:(top.destroy(),self.root.deiconify()))

    def process(self, img):
        self.show_image(img)

        def task():
            self.ui(self.set_status,"检测中...","orange")

            np_img = np.array(img)
            results = detector(np_img)[0]

            boxes = results.boxes.xyxy.cpu().numpy() if results.boxes else []

            draw = img.copy()
            d = ImageDraw.Draw(draw)

            latex_list = []

            for box in boxes:
                x1,y1,x2,y2 = map(int, box)
                crop = img.crop((x1,y1,x2,y2))
                latex = ocr_model(crop)
                latex_list.append(latex)

                d.rectangle([x1,y1,x2,y2], outline="cyan", width=2)

            if not boxes.any() if hasattr(boxes,"any") else len(boxes)==0:
                latex_list.append(ocr_model(img))

            self.ui(self.show_result, latex_list)
            self.ui(self.show_image, draw)
            self.ui(self.set_status,"完成","green")

        threading.Thread(target=task, daemon=True).start()

    def show_image(self, img):
        img_copy = img.copy()
        img_copy.thumbnail((900,350))
        self.tkimg = ImageTk.PhotoImage(img_copy)
        self.canvas.create_image(0,0,anchor="nw",image=self.tkimg)

    def show_result(self, lst):
        self.text.delete(1.0,tk.END)
        for i,l in enumerate(lst,1):
            self.text.insert(tk.END,f"[{i}] {l}\n")

    def set_status(self, txt, color="white"):
        self.status.config(text=txt, fg=color)

    def copy(self):
        t=self.text.get(1.0,tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(t)
        messagebox.showinfo("OK","已复制")


if __name__=='__main__':
    root=tk.Tk()
    App(root)
    root.mainloop()
