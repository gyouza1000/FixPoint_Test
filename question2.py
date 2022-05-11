##  設問2

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
import ipaddress
import datetime


class FailedNumFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl = ttk.Label(self, text="タイムアウト判定回数：　")
        self.lbl.pack(side='left')
        self.spnval = tk.StringVar()
        self.spnval.set('0')
        self.spn = ttk.Spinbox(self, textvariable=self.spnval,
                               from_=0, to=999, increment=1)
        self.spn.pack(side='left')


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


class timeoutClass:
    def __init__(self, s):
        self.starttime = datetime.datetime.strptime(s, '%Y%m%d%H%M%S')
        self.endtime = None
        self.period = None

    def SetEndTime(self, e, to):
        if to is not None:
            self.endtime = datetime.datetime.strptime(e, '%Y%m%d%H%M%S') + to
        else:
            self.endtime = datetime.datetime.strptime(e, '%Y%m%d%H%M%S')
        self.period = self.endtime - self.starttime


class ServerData:
    def __init__(self, ipadr, tl):
        self.ip = ipaddress.ip_interface(ipadr)
        self.timeoutlist = []
        self.__SelectState = ["Alive", "Broken"]
        self.state = self.__SelectState[0]
        self.timeoutNum = 0
        self.timeoutLimit = int(tl)

    def NetworkIn(self, ipadr):
        if ipaddress.ip_interface(ipadr).network in self.ip.network:
            return True
        else:
            return False

    def SearchIP(self, ipadr):
        if ipaddress.ip_interface(ipadr).ip == self.ip.ip:
            return True
        else:
            return False

    def InputStr(self, times, timeout):
        flg = False
        if timeout != "-":
            self.timeoutNum = 0
            todt = datetime.timedelta(milliseconds=int(timeout))
        else:
            self.timeoutNum += 1
            todt = None
        if len(self.timeoutlist) > 0:
            if self.timeoutlist[-1].endtime is None:
                if timeout != "-":
                    if self.state == self.__SelectState[1]:
                        self.timeoutlist[-1].SetEndTime(times, todt)
                        self.state = self.__SelectState[0]
                        flg = True
                    else:
                        self.timeoutlist.pop()
                else:
                    if self.timeoutNum >= self.timeoutLimit:
                        self.state = self.__SelectState[1]
            else:
                if timeout == "-":
                    self.timeoutlist.append(timeoutClass(times))
        else:
            if timeout == "-":
                self.timeoutlist.append(timeoutClass(times))

        if flg:
            return self.timeoutlist[-1]
        else:
            return None

    def SearchNotEnterd(self):
        if len(self.timeoutlist) > 0:
            if self.timeoutlist[-1].endtime is None:
                return self.timeoutlist[-1]
            else:
                return None
        else:
            return None


class MainProcess:
    def __init__(self, shareQueue, number):
        self.CSVData = pd.DataFrame(columns=["ServerAddress", "Failure period(Sec)"])
        self.queues = shareQueue
        self.saveName = "output_question2.csv"

        self.FailedNumber = number
        self.CSVData.to_csv(self.saveName, index=False)

        self.serv = []

    def threadRun(self):
        if not self.queues.empty():
            strs = self.queues.get()
            times, ip, timeout = strs.split(",")
            flg = False
            for sv in self.serv:
                if sv.SearchIP(ip):
                    tmp = sv.InputStr(times, timeout)
                    if tmp is not None:
                        print([str(sv.ip), tmp.period.total_seconds()])
                        pd.DataFrame([[str(sv.ip), tmp.period.total_seconds()]],
                                     columns=self.CSVData.columns).to_csv(self.saveName,
                                                                          mode='a', index=False, header=False)
                    flg = True
            if not flg:
                self.serv.append(ServerData(ip, self.FailedNumber))
                self.serv[-1].InputStr(times, timeout)

    def end(self):
        for sv in self.serv:
            tmp = sv.SearchNotEnterd()
            if tmp is not None:
                print([str(sv.ip), "不明"])
                pd.DataFrame([[str(sv.ip), "Unknown"]],
                             columns=self.CSVData.columns).to_csv(self.saveName,
                                                                  mode='a', index=False, header=False)


class MainFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.playing = False
        self.ShareQueue = queue.Queue()
        self.wf = WatchFrame(self)
        self.wf.pack(fill=tk.X, padx=30)

        self.fn = FailedNumFrame(self)
        self.fn.pack(fill=tk.X, padx=30)
        self.failedNum = None

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
            if self.fn.spn.get().isdigit():
                self.failedNum = int(self.fn.spn.get())
                self.mp = MainProcess(self.ShareQueue, self.failedNum)
                if self.wp.watchStart(self.wf.filepath):
                    self.thd = threading.Thread(target=self.mpLoop)
                    self.thd.start()
                    self.text.set("停止")
                else:
                    self.playing = False
            else:
                self.playing = False
        else:
            self.wp.end()
            self.thd.join()
            self.text.set("実行")

    def mpLoop(self):
        while self.playing or not self.ShareQueue.empty():
            self.mp.threadRun()
        self.mp.end()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x300")

    app1 = MainFrame(root)
    app1.pack(fill=tk.BOTH)

    root.mainloop()
