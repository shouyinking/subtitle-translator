
import os
import re
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from langdetect import detect
from concurrent.futures import ThreadPoolExecutor, as_completed
from pysubs2 import SSAFile
from tqdm import tqdm
import requests

API_URL = "https://api.vveai.com/v1/chat/completions"
API_KEY = "sk-KbToPGNqnjYpMBWZ189256237dBf4e30Ab4c1d55A1661217"  # ← API 密钥
MODEL = "gpt-40-mini"

SUPPORTED_EXTS = [".srt", ".vtt", ".ass"]
TARGET_LANGS = {"中文": "Chinese", "英文": "English", "日文": "Japanese"}

# API调用
def translate_batch(texts, from_lang, to_lang):
    prompt = f"请将以下{from_lang}字幕翻译成{to_lang}，保持自然流畅，不要加说明：\n\n"
    prompt += "\n".join([f"{i+1}. {line}" for i, line in enumerate(texts)])

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": ""}
        ]
    }

    try:
        res = requests.post(API_URL, json=data, headers=headers)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        lines = [re.sub(r"^\d+\.\s*", "", l).strip() for l in content.strip().split("\n") if l.strip()]
        return lines
    except Exception as e:
        print("翻译失败：", e)
        return [""] * len(texts)

# 翻译字幕（多线程）
def translate_subtitles(subs, from_lang, to_lang, max_workers=4):
    batch_size = 10
    translated_texts = [None] * len(subs)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(0, len(subs), batch_size):
            batch = [s.text for s in subs[i:i+batch_size]]
            futures.append((i, executor.submit(translate_batch, batch, from_lang, to_lang)))
        for i, future in tqdm(futures, desc="翻译进度", ncols=100):
            result = future.result()
            for j, line in enumerate(result):
                if i + j < len(subs):
                    subs[i + j].text = line
            time.sleep(1.0)
    return subs

# 字幕解析与保存
def process_subtitle(file_path, target_lang):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError("不支持的字幕格式")

    subs = SSAFile.load(file_path, encoding="utf-8")
    all_text = "\n".join([s.text for s in subs])
    from_lang_code = detect(all_text)
    lang_name_map = {"zh-cn": "中文", "ja": "日文", "en": "英文"}
    from_lang = lang_name_map.get(from_lang_code, "原始语言")

    subs = translate_subtitles(subs, from_lang, target_lang)

    output_path = file_path.replace(ext, f"_{target_lang}.ass")
    subs.save(output_path, encoding="utf-8")
    return output_path

# GUI
def run_gui():
    root = tk.Tk()
    root.title("字幕翻译助手（多格式+多语言+多线程）")
    root.geometry("500x230")

    file_path_var = tk.StringVar()
    lang_var = tk.StringVar(value="中文")

    def select_file():
        path = filedialog.askopenfilename(filetypes=[("字幕文件", "*.srt *.ass *.vtt")])
        if path:
            file_path_var.set(path)

    def start_translate():
        file_path = file_path_var.get()
        lang = lang_var.get()
        if not file_path:
            messagebox.showwarning("提示", "请选择字幕文件")
            return
        try:
            output = process_subtitle(file_path, TARGET_LANGS[lang])
            messagebox.showinfo("完成", f"翻译完成：\n{output}")
        except Exception as e:
            messagebox.showerror("出错了", str(e))

    tk.Label(root, text="字幕文件路径：").pack(pady=5)
    tk.Entry(root, textvariable=file_path_var, width=60).pack()
    tk.Button(root, text="选择文件", command=select_file).pack(pady=5)

    tk.Label(root, text="目标语言：").pack(pady=5)
    tk.OptionMenu(root, lang_var, *TARGET_LANGS.keys()).pack()

    tk.Button(root, text="开始翻译", command=start_translate, bg="#4CAF50", fg="white", font=("Arial", 12)).pack(pady=15)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
    