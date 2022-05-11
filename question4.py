##  設問4

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


class TimeHangFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.numf = tk.Frame(self)
        self.lbl = ttk.Label(self.numf, text="過負荷判定応答回数：　")
        self.lbl.pack(side='left')
        self.spnval = tk.StringVar()
        self.spnval.set('1')
        self.NumSpn = ttk.Spinbox(self.numf, textvariable=self.spnval,
                                  from_=0, to=999, increment=1)
        self.NumSpn.pack(side='left')
        self.numf.pack(side='left', padx=10)

        self.timef = tk.Frame(self)
        self.lbl2 = ttk.Label(self.timef, text="過負荷判定応答時間：　")
        self.lbl2.pack(side='left')
        self.spnval2 = tk.StringVar()
        self.spnval2.set('0')
        self.TmSpn = ttk.Spinbox(self.timef, textvariable=self.spnval2,
                                 from_=0, to=999, increment=1)
        self.TmSpn.pack(side='left')
        self.lbl3 = ttk.Label(self.timef, text="ms")
        self.lbl3.pack(side='left')
        self.timef.pack(side='left', padx=10)


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


class overloadClass:
    def __init__(self, max):
        self.timelist = []
        self.max = max
        self.runtimelist = []
        self.starttime = None

    def append(self, inputs, runtime):
        self.timelist.append(inputs)
        self.runtimelist.append(datetime.datetime.strptime(runtime, '%Y%m%d%H%M%S'))
        if len(self.timelist) > self.max:
            self.timelist = self.timelist[len(self.timelist) - self.max:]
            self.runtimelist = self.runtimelist[len(self.runtimelist) - self.max:]

    def calculation(self):
        if len(self.timelist) == self.max:
            mean = sum(self.timelist) / len(self.timelist)
            return True, mean
        else:
            return False, None

    def SetStarttime(self, flg):
        if flg:
            self.starttime = self.runtimelist[0]
        else:
            self.starttime = None


class ServerData:
    def __init__(self, ipadr, tl, ttn, tto):
        self.ip = ipaddress.ip_interface(ipadr)
        self.timeoutlist = []
        self.__SelectState = ["Alive", "Broken", "Overload"]
        self.state = self.__SelectState[0]

        self.timeoutNum = 0
        self.timeoutLimit = int(tl)

        self.overloadNum = ttn
        self.overloadTime = tto
        self.overload = overloadClass(self.overloadNum)

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
        tmp2 = None
        if timeout != "-":
            self.timeoutNum = 0
            todt = datetime.timedelta(milliseconds=int(timeout))
            self.overload.append(todt.total_seconds() * 1000, times)
            flg2, tmp = self.overload.calculation()
            if flg2:
                if tmp > self.overloadTime:
                    if self.overload.starttime is None:
                        self.overload.SetStarttime(True)
                    self.state = self.__SelectState[2]
                else:
                    if self.overload.starttime is not None:
                        tmp2 = (datetime.datetime.strptime(times, '%Y%m%d%H%M%S') -
                                self.overload.starttime)
                    self.overload.SetStarttime(False)

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
            return self.timeoutlist[-1], tmp2
        else:
            return None, tmp2

    def SearchNotEnterd(self):
        if len(self.timeoutlist) > 0:
            if self.timeoutlist[-1].endtime is None:
                return self.timeoutlist[-1]
            else:
                return None
        else:
            return None


class FailedNetwork:
    def __init__(self, nw):
        self.nw = nw
        self.time = None

    def SetStart(self, s):
        self.time = timeoutClass(s)

    def SetEnd(self, e, t):
        self.time.SetEndTime(e, t)

    def ResetStart(self):
        self.time = None


class MainProcess:
    def __init__(self, shareQueue, number, mt):
        self.CSVData = pd.DataFrame(columns=["ServerAddress", "Failure period(Sec)"])
        self.queues = shareQueue
        self.saveName = "output_question2.csv"

        self.FailedNumber = number
        self.CSVData.to_csv(self.saveName, index=False)

        self.overloadm = int(mt[0])
        self.overloadt = float(mt[1])
        self.CSVData2 = pd.DataFrame(columns=["ServerAddress", "overload period(sec)"])
        self.saveName2 = "output_question3.csv"
        self.CSVData2.to_csv(self.saveName2, index=False)

        self.network = []
        self.CSVData3 = pd.DataFrame(columns=["NetworkAddress", "Failed period(sec)"])
        self.saveName3 = "output_question4.csv"
        self.CSVData3.to_csv(self.saveName3, index=False)

        self.serv = []
        self.nwList = []

    def threadRun(self):
        if not self.queues.empty():
            strs = self.queues.get()
            times, ip, timeout = strs.split(",")
            flg = False
            for sv in self.serv:
                if sv.SearchIP(ip):
                    tmp, tmp2 = sv.InputStr(times, timeout)
                    if tmp is not None:
                        print(["サーバー故障", str(sv.ip), tmp.period.total_seconds()])
                        pd.DataFrame([[str(sv.ip), tmp.period.total_seconds()]],
                                     columns=self.CSVData.columns).to_csv(self.saveName,
                                                                          mode='a', index=False, header=False)
                    if tmp2 is not None:
                        print(["サーバー過負荷", str(sv.ip), tmp2.total_seconds()])
                        pd.DataFrame([[str(sv.ip), tmp2.total_seconds()]],
                                     columns=self.CSVData2.columns).to_csv(self.saveName2,
                                                                           mode='a', index=False, header=False)
                    flg = True
            if not flg:
                self.serv.append(ServerData(ip, self.FailedNumber, self.overloadm, self.overloadt))
                self.serv[-1].InputStr(times, timeout)

                if not self.serv[-1].ip.network in [i.nw for i in self.nwList]:
                    self.nwList.append(FailedNetwork(self.serv[-1].ip.network))

            for nwt in self.nwList:
                flg2 = False
                for sv in self.serv:
                    if sv.ip in nwt.nw:
                        if sv.state == "Broken":
                            flg2 = True
                        else:
                            flg2 = False
                if flg2:
                    if nwt.time is None:
                        nwt.SetStart(times)
                else:
                    if nwt.time is not None:
                        nwt.SetEnd(times, None)
                        print(["ネットワーク故障", str(nwt.nw), nwt.time.period.total_seconds()])
                        pd.DataFrame([[str(nwt.nw), nwt.time.period.total_seconds()]],
                                     columns=self.CSVData3.columns).to_csv(self.saveName3,
                                                                           mode='a', index=False, header=False)
                        nwt.ResetStart()

    def end(self):
        for sv in self.serv:
            tmp = sv.SearchNotEnterd()
            if tmp is not None:
                print(["サーバー故障", str(sv.ip), "故障中"])
                pd.DataFrame([[str(sv.ip), "is_broken"]],
                             columns=self.CSVData.columns).to_csv(self.saveName,
                                                                  mode='a', index=False, header=False)
            if sv.overload.starttime is not None:
                print(["サーバー過負荷", str(sv.ip), "過負荷状態"])
                pd.DataFrame([[str(sv.ip), "is_overload"]],
                             columns=self.CSVData2.columns).to_csv(self.saveName2,
                                                                  mode='a', index=False, header=False)
        for nwt in self.nwList:
            if nwt.time is not None and nwt.time.endtime is None:
                print(["ネットワーク故障", str(nwt.nw), "故障中"])
                pd.DataFrame([[str(nwt.nw), "is_broken"]],
                             columns=self.CSVData3.columns).to_csv(self.saveName3,
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

        self.oln = TimeHangFrame(self)
        self.oln.pack(fill=tk.X, padx=30)

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
            if self.fn.spn.get().isdigit() and self.oln.NumSpn.get().isdigit() and self.oln.TmSpn.get().isdigit():
                self.failedNum = int(self.fn.spn.get())
                self.mp = MainProcess(self.ShareQueue, self.failedNum, [self.oln.NumSpn.get(), self.oln.TmSpn.get()])
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
    root.geometry("800x300")

    app1 = MainFrame(root)
    app1.pack(fill=tk.BOTH)

    root.mainloop()
