# 文件名：gui_app.py

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
import io
import threading
from datetime import datetime, timedelta

# Solana 原生代币
SOL_MINT = "So11111111111111111111111111111111111111112"

# 替换成你的 Helius API Key
HELIUS_METADATA_API = "https://api.helius.xyz/v0/token-metadata?api-key=YOUR_HELIUS_API_KEY"

class SolanaMarketGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Solana 活跃交易对排行榜")

        self.token_icon_cache = {}
        self.tk_images = {}

        self.create_widgets()
        self.markets = []

    def create_widgets(self):
        # 控制面板
        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_btn = ttk.Button(ctrl_frame, text="刷新市场数据", command=self.refresh_data)
        self.refresh_btn.pack(side=tk.LEFT)

        # 日志文本框
        self.log_text = tk.Text(self.root, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X, padx=5, pady=5)

        # 表格区域
        columns = ("base", "quote", "base_mint", "quote_mint", "launch_time", "liquidityUSD")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 绑定双击显示 token 图标
        self.tree.bind("<Double-1>", self.on_double_click)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def refresh_data(self):
        self.refresh_btn.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())  # 清空表格
        self.token_icon_cache.clear()
        self.tk_images.clear()
        self.log("开始刷新 Jupiter 市场数据...")

        def worker():
            try:
                self.log("正在从 Jupiter 拉取市场数据...")
                markets = self.fetch_jupiter_markets()
                self.log(f"获取到市场数量: {len(markets)}")

                self.log("正在过滤符合条件的市场...")
                filtered = self.filter_markets(markets, days=7)
                self.log(f"筛选出最近7天上线且与SOL配对的市场数量: {len(filtered)}")

                self.log("正在按流动性排序...")
                top20 = self.get_top_markets(filtered)
                self.markets = top20

                for m in top20:
                    base = m.get("baseSymbol", "N/A")
                    quote = m.get("quoteSymbol", "N/A")
                    base_mint = m.get("baseMint")
                    quote_mint = m.get("quoteMint")
                    launch_time_str = m.get("launchTime")
                    launch_time_fmt = launch_time_str.split("T")[0] if launch_time_str else "未知"
                    liquidity_usd = round(m.get("liquidityUSD", 0), 2)

                    # 在表格中插入数据
                    self.tree.insert("", tk.END, values=(
                        base, quote, base_mint, quote_mint, launch_time_fmt, liquidity_usd
                    ))

                self.log("刷新完成。")
            except Exception as e:
                self.log(f"错误：{e}")
                messagebox.showerror("错误", f"获取数据失败：{e}")
            finally:
                self.refresh_btn.config(state=tk.NORMAL)

        threading.Thread(target=worker).start()

    def fetch_jupiter_markets(self):
        # 使用 lite-api.jup.ag 免费端点
        url = "https://lite-api.jup.ag/v1/markets"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Debug: 打印一下返回字段结构
            if isinstance(data, list) and len(data) > 0:
                sample = data[0]
                self.log(f"API 返回字段示例: {list(sample.keys())}")
            else:
                self.log("API 返回为空或不是列表。")

            return data
        except Exception as e:
            self.log(f"API 请求失败，错误: {e}")
            return []

    def filter_markets(self, markets, days=7):
        # 过滤出最近7天且与SOL配对的市场
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        filtered = []

        for m in markets:
            launch_time_str = m.get("launchTime")
            if not launch_time_str:
                # Debug：没有 launchTime 字段，跳过
                self.log(f"跳过无 launchTime 市场: {m.get('marketAddress', 'unknown')}")
                continue

            try:
                dt = datetime.fromisoformat(launch_time_str.replace("Z", "+00:00"))
            except Exception:
                self.log(f"无法解析 launchTime: {launch_time_str}")
                continue

            if dt < cutoff_time:
                continue

            if m.get("baseMint") == SOL_MINT or m.get("quoteMint") == SOL_MINT:
                filtered.append(m)

        return filtered

    def get_top_markets(self, filtered_markets, top_n=20):
        # 按流动性 USD 排序，取 Top N
        sorted_markets = sorted(filtered_markets, key=lambda x: x.get("liquidityUSD", 0), reverse=True)
        return sorted_markets[:top_n]

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        item = item[0]
        values = self.tree.item(item, "values")
        base_mint = values[2]
        quote_mint = values[3]
        base_name = values[0]
        quote_name = values[1]

        win = tk.Toplevel(self.root)
        win.title(f"{base_name} / {quote_name} Token 图标")

        def load_and_show():
            base_icon = self.get_token_icon(base_mint)
            quote_icon = self.get_token_icon(quote_mint)

            if base_icon:
                lbl1 = tk.Label(win, image=base_icon)
                lbl1.image = base_icon
                lbl1.pack(side=tk.LEFT, padx=10, pady=10)
                tk.Label(win, text=base_name).pack(side=tk.LEFT, padx=10)
            else:
                tk.Label(win, text=f"{base_name} 图标未找到").pack(side=tk.LEFT, padx=10, pady=10)

            if quote_icon:
                lbl2 = tk.Label(win, image=quote_icon)
                lbl2.image = quote_icon
                lbl2.pack(side=tk.LEFT, padx=10, pady=10)
                tk.Label(win, text=quote_name).pack(side=tk.LEFT, padx=10)
            else:
                tk.Label(win, text=f"{quote_name} 图标未找到").pack(side=tk.LEFT, padx=10, pady=10)

        threading.Thread(target=load_and_show).start()

    def get_token_icon(self, mint):
        if mint in self.token_icon_cache:
            return self.token_icon_cache[mint]

        try:
            url = f"{HELIUS_METADATA_API}&mint={mint}"
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            meta = data[0]
            offchain = meta.get("offChainMetadata")
            if not offchain:
                offchain_uri = meta.get("offChainUri")
                if not offchain_uri:
                    return None
                r = requests.get(offchain_uri)
                r.raise_for_status()
                offchain = r.json()
            image_url = offchain.get("image")
            if not image_url:
                return None
            img_resp = requests.get(image_url)
            img_resp.raise_for_status()
            img_data = img_resp.content
            from PIL import Image
            image = Image.open(io.BytesIO(img_data)).convert("RGBA")
            image = image.resize((64, 64), Image.ANTIALIAS)
            tk_img = ImageTk.PhotoImage(image)
            self.token_icon_cache[mint] = tk_img
            return tk_img
        except Exception:
            return None
