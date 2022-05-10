##  =======================================
##  フィックスポイント プログラミング試験問題
##  =======================================
##  A社の監視システムでは、監視対象となる複数台のサーバに対して一定間隔でping応答確認を行っており、
##  確認結果は以下に示すカンマ区切りの形式で1行ずつ監視ログファイルに追記される。
##  -------------------------------------------------
##  ＜確認日時＞,＜サーバアドレス＞,＜応答結果＞
##  -------------------------------------------------
##  確認日時は、YYYYMMDDhhmmssの形式。ただし、年＝YYYY（4桁の数字）、月＝MM（2桁の数字。以下同様）、日＝DD、時＝hh、分＝mm、秒＝ssである。
##  サーバアドレスは、ネットワークプレフィックス長付きのIPv4アドレスである。
##  応答結果には、pingの応答時間がミリ秒単位で記載される。ただし、タイムアウトした場合は"-"(ハイフン記号)となる。
##
##  以下に監視ログの例（抜粋）を示す。
##  -------------------------------------------------
##  20201019133124,10.20.30.1/16,2
##  20201019133125,10.20.30.2/16,1
##  20201019133134,192.168.1.1/24,10
##  20201019133135,192.168.1.2/24,5
##  20201019133224,10.20.30.1/16,522
##  20201019133225,10.20.30.2/16,1
##  20201019133234,192.168.1.1/24,8
##  20201019133235,192.168.1.2/24,15
##  20201019133324,10.20.30.1/16,-
##  20201019133325,10.20.30.2/16,2
##  -------------------------------------------------
##  設問1
##  監視ログファイルを読み込み、故障状態のサーバアドレスとそのサーバの故障期間を出力するプログラムを作成せよ。
##  出力フォーマットは任意でよい。
##  なお、pingがタイムアウトした場合を故障とみなし、最初にタイムアウトしたときから、次にpingの応答が返るまでを故障期間とする。

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import pathlib
import queue
import hashlib
import difflib
import threading


class WatchFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl = ttk.Label(self, text="監視ファイル：　")
        self.lbl.pack(side='left')
        self.ent = ttk.Entry(self)
        self.ent.pack(fill=tk.X, side='left', expand=True)
        self.btn = ttk.Button(self, text="...", width=3, command=self.openDialog)
        self.btn.pack(side='left')

    def openDialog(self):
        typ = [('ログファイル', '*.log')]
        dirs = '.\\'
        fle = filedialog.askopenfilename(filetypes=typ, initialdir=dirs)
        if fle != "":
            self.ent.delete(0, tk.END)
            self.ent.insert(0, fle)

    @property
    def filepath(self):
        return self.ent.get()


class WatchProcess:
    def __init__(self, shareQueue):
        self.filename = ""
        self.queue = shareQueue
        self.beforeFile = None
        self.beforeStr = None
        self.observer = None
        self.event_handler = None

    def SetFile(self, name):
        if pathlib.Path(name).is_file() and pathlib.Path(name).stem == "log":
            self.filename = name
            return True
        else:
            return False

    def watchStart(self, name):
        if self.SetFile(name):
            with open(self.filename, "r") as f:
                tmpcomp = f.readlines()
            with open(self.filename, "rb") as f:
                tmphash = f.read()
            for tl in tmpcomp:
                self.queue.put(tl.strip())
            self.beforeStr = tmpcomp
            self.beforeFile = hashlib.md5(tmphash).hexdigest()

            dir_watch = str(pathlib.Path(self.filename).parent.cwd())
            patterns = pathlib.Path(self.filename).name
            self.event_handler = PatternMatchingEventHandler([patterns])
            self.event_handler.on_modified = self.on_modified
            self.observer = Observer()
            self.observer.schedule(self.event_handler, dir_watch, recursive=True)

            self.observer.start()
            return True
        else:
            return False

    def on_modified(self, event):
        """ファイル変更検知のためのハッシュ値を取得"""
        with open(self.filename, 'rb') as f:
            newHash = hashlib.md5(f.read()).hexdigest()
        if newHash != self.beforeFile:
            with open(self.filename, "r") as f:
                tmpcomp = f.readlines()
            diff = difflib.Differ()
            output_diff = diff.compare(self.beforeStr, tmpcomp)
            for data in output_diff:
                if data[0:1] in ['+']:
                    data = data[1:]
                    self.queue.put(data.strip())
            self.beforeStr = tmpcomp
            self.beforeFile = newHash

    def end(self):
        self.observer.stop()


class MainProcess:
    def __init__(self, shareQueue):
        self.CSVData = pd.DataFrame()
        self.queues = shareQueue
        self.saveName = None

    def threadRun(self):
        if not self.queues.empty():
            strs = self.queues.get()
            print(strs)


class MainFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.playing = False
        self.ShareQueue = queue.Queue()
        self.wf = WatchFrame(self)
        self.wf.pack(fill=tk.X, padx=30)
        self.text = tk.StringVar()
        self.text.set("実行")
        self.btn = ttk.Button(self, textvariable=self.text, command=self.Run)
        self.btn.pack()

        self.wp = None
        self.mp = None
        self.thd = None

    def Run(self):
        self.playing = not self.playing
        if self.playing:
            self.wp = WatchProcess(self.ShareQueue)
            self.mp = MainProcess(self.ShareQueue)
            if self.wp.watchStart(self.wf.filepath):
                self.thd = threading.Thread(target=self.mpLoop)
                self.thd.start()
                self.text.set("停止")
            else:
                self.playing = False
        else:
            self.wp.end()
            self.thd.join()
            self.text.set("実行")

    def mpLoop(self):
        while self.playing or not self.ShareQueue.empty():
            self.mp.threadRun()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x300")

    app1 = MainFrame(root)
    app1.pack(fill=tk.BOTH)

    root.mainloop()
