# -*- coding: utf-8 -*-
# /usr/lib/bin
import base64
import hashlib
import json
import struct
import threading

import pyttsx3 as tts
from tkinter import *
from tkinter.ttk import Treeview
from tkinter import ttk
from tkinter.messagebox import showerror
import os
from PIL import Image, ImageTk
import time
import socket


win = Tk()
timerStr = StringVar()
screen_width = win.winfo_screenwidth()
screen_height = win.winfo_screenheight()


# 声音播放
class Voice(object):
    def __init__(self, text):
        self.playMsg = text

    def play(self):
        engine = tts.init()
        engine.setProperty('rate', 110)  # 语音播放语数
        engine.setProperty('volume', 1)  # 播放音量,0~1
        voices = engine.getProperty('voices')  # 语言
        engine.setProperty('voice', voices[0].id)  # 0中文 1英文
        t = u'%s' % self.playMsg
        engine.say(t)
        engine.runAndWait()


class SocketClient(object):
    def __init__(self):
        self.buffer_size = 1024
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with open('config.ini', 'r') as f:
            f_list = f.readlines()
            for i in range(0, len(f_list), 3):
                if f_list[i].find('Socket'):
                    self.host = f_list[i+1].replace("\n", "").split("=")[1]
                    self.post = int(f_list[i+2].replace("\n", "").split("=")[1])
                    self.addr = (self.host, self.post)

    def create(self):
        try:
            # 创建一个TCP/IP的套接字
            # self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 创建一个UDP/IP套接字
            # self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_socket.connect(self.addr)
            self.client_socket.setblocking(0)
            print("connect to ", self.addr)
            self.client_socket.sendall('连接成功!!!!!!!'.encode())
            # while True:
            #     # 接收内容
            #     data = self.client_socket.recv(self.buffer_size)
            #     data = data.decode(encoding='utf-8')
            #     print(data)
        except socket.error:
            print('error', socket.error)
            showerror(title='错误', message='连接远程中心出错')
        # finally:
        #     self.client_socket.close()

    def sendMsg(self):
        self.client_socket.send(bytes('asdasdasd'), encodings='utf-8')
        data = self.client_socket.recv(self.buffer_size)
        data = data.decode(encoding='utf-8')
        if data:
            return
        else:
            pass

    # 关闭socket连接
    def Close(self):
        self.client_socket.send(bytes('close'), encoding='utf-8')
        self.client_socket.close()

# WebSocket server 对象
class SocketServer(object):
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with open('config.ini', 'r') as f:
            f_list = f.readlines()
            for i in range(0, len(f_list), 3):
                if f_list[i].find('Socket'):
                    self.host = f_list[i+1].replace("\n", "").split("=")[1]
                    self.post = int(f_list[i+2].replace("\n", "").split("=")[1])
                    self.addr = (self.host, self.post)
        self.server_socket.bind(self.addr)
        self.server_socket.listen(10)
        self.server_socket.setblocking(1)
        t = threading.Thread(target=self.handler_accept(self.server_socket))
        t.start()

    def handler_accept(self, sock):
        while True:
            conn, addr = sock.accept()

            data = conn.recv(8096)
            headers = self.get_headers(data)
            response_tpl = "HTTP/1.1 101 Switching Protocols\r\n" \
                           "Upgrade:websocket\r\n" \
                           "Connection: Upgrade\r\n" \
                           "Sec-WebSocket-Accept: %s\r\n" \
                           "WebSocket_Location: ws://%s\r\n\r\n"

            #第一次连接发回报文
            magic_string = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
            if headers.get('Sec-WebSocket-Key'):
                value = headers['Sec-WebSocket-Key'] + magic_string

            ac = base64.b64encode(hashlib.sha1(value.encode('utf-8')).digest())
            response_str = response_tpl % (ac.decode('utf-8'), headers.get("Host"))
            # print(response_str)
            conn.sendall(bytes(response_str, encoding="utf-8"))
            t = threading.Thread(target=self.handler_msg, args=(conn,))
            t.start()

    def get_headers(self, data):
        headers = {}
        data = str(data, encoding="utf-8")

        header, body = data.split("\r\n\r\n", 1)

        header_list = header.split("\r\n")

        for i in header_list:
            i_list = i.split(":", 1)
            if len(i_list) >= 2:
                headers[i_list[0]] = "".join(i_list[1::]).strip()
            else:
                i_list = i.split(" ", 1)
                if i_list and len(i_list) == 2:
                    headers["method"] = i_list[0]
                    headers["protocol"] = i_list[1]
        return headers

    def handler_msg(self, conn):
        while conn:
            while True:
                data_recv = conn.recv(8096)
                # print(data_recv)
                if data_recv[0:1] == b"\x81":
                    data_parse = self.parse_payload(data_recv)
                    # 消息转化成对象
                    if data_parse != None:
                        data_obj = json.loads(data_parse)
                        voice_str = insertTab(data_obj)
                        Voice(voice_str).play()
                    # print(data_obj["xingming"])
                    # print(data_parse)
                self.send_msg(conn, bytes("recv: {}".format(data_parse), encoding="utf-8"))

    def parse_payload(self, payload):
        payload_len = payload[1] & 127
        if payload_len == 126:
            extend_payload_len = payload[2:4]
            mask = payload[4:8]
            decoded = payload[8:]
        elif payload_len == 127:
            extend_payload_len = payload[2:10]
            mask = payload[10:14]
            decoded = payload[14:]
        else:
            extend_payload_len = None
            mask = payload[2:6]
            decoded = payload[6:]
        bytes_list = bytearray()

        for i in range(len(decoded)):
            # 解码方式
            chunk = decoded[i] ^ mask[i % 4]
            bytes_list.append(chunk)
        body = str(bytes_list, encoding='utf-8')
        return body

    def send_msg(self, conn, msg_bytes):
        # 接收的第一字节，一般都是x81不变
        first_byte = b"\x81"
        length = len(msg_bytes)
        if length < 126:
            first_byte += struct.pack("B", length)
        elif length <= 0xFFFF:
            first_byte += struct.pack("!BH", 126, length)
        else:
            first_byte += struct.pack("!BQ", 127, length)

        msg = first_byte + msg_bytes
        conn.sendall(msg)
        return True


class WebSocketThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "WebSocketThread"
        self.daemon = True
        self._stop_event = threading.Event()

    def run(self):
        sock = SocketServer()

    def stop(self):
        self._stop_event.set()


# ESC键退出程序
def ESCQuit(event):
    # print(f"特殊按键触发:{event.char},对应的ASCII码:{event.keycode}")
    if event.keycode == 27:
        sys.exit()


# 语音播放
def speak(text):
    p = Voice(text)
    p.play()


# 时钟计时器
def tricket():
    timerStr.set(time.strftime('%H:%M:%S', time.localtime(time.time())))
    win.after(1000, tricket)


# 获取当前日期以及星期
def getNowTime():
    week_dick = {'0': '星期天', '1': '星期一', '2': '星期二', '3': '星期三', '4': '星期四', '5': '星期五', '6': '星期六'}
    now_date = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    now_week = time.strftime('%w', time.localtime(time.time()))
    return '%s %s' % (now_date, week_dick[now_week])


# 插入表格
def insertTab(obj_data):
    items = tab.get_children()
    for item in items:
        a = tab.item(item)
        if a["text"] == obj_data['zhenshi']:
            tab.delete(item)
    xm = obj_data['xingming'][0:1]+'*'*(len(obj_data['xingming'])-1)
    tab.insert("", 'end', value=(obj_data['jiuzhenh'], xm, obj_data['keshi'], obj_data['yisheng'], obj_data['zhenshi']), text=obj_data['zhenshi'])
    return '请%s%s到%s诊室就诊' % (obj_data['jiuzhenh'], obj_data['xingming'], obj_data['zhenshi'])


if __name__ == '__main__':
    WebSocketThread().start()
    win.title('智能导诊平台')
    # 全屏显示
    win.attributes("-fullscreen", True)
    win.configure(bg='darkturquoise')
    win.bind('<Key>', ESCQuit)
    image_open = Image.open(os.getcwd() + '/images/yiyuan.png')
    yy_photo = ImageTk.PhotoImage(image_open)
    Label(win, image=yy_photo, bg='darkturquoise').place(x=0, y=0, width=438, height=110)
    now_time = getNowTime()
    Label(win, text=now_time, bg='darkturquoise', font=('Arial', 20), fg='white')\
        .place(x=screen_width-450, y=0, width=230, height=110)
    timerStr.set(time.strftime('%H:%M:%S', time.localtime(time.time())))
    Label(win, textvariable=timerStr, bg='darkturquoise', font=('Arial', 20), fg='white')\
        .place(x=screen_width-220, y=0, width=110, height=110)

    win.after(1000, tricket)
    # 表格样式
    tree_style = ttk.Style(win)
    # print(tree_style.theme_names())
    tree_style.theme_settings("classic", {"Treeview": {
            "configure": {"padding": 0},
            "map": {
                "background": [("active", "aliceblue"), ("!disabled", "aliceblue")],
                "fieldbackground": [("!disabled", "aliceblue")],
                "foreground": [("focus", "#535655"), ("!disabled", "#535655")]
            }
        }
    })
    tree_style.theme_use("classic")
    tree_style.configure("Treeview", font=('Microsoft YaHei', 20), rowheight=80, background='aliceblue',
                         fieldbackground='aliceblue', foreground='#535655', borderwidth=0)
    tree_style.configure("Treeview.Heading", background='aliceblue', foreground='#0C706B',
                         font=('Microsoft YaHei', 20, 'bold'), padding=10, borderwidth=0)
    # print(tree_style.configure("Treeview.Item"))
    # tree_style.layout("Treeview.Row", [])

    tab = Treeview(win, height=20, show="headings")
    tab.place(x=0, y=110, width=screen_width, height=screen_height - 110 - 50)

    # 定义列
    tab["columns"] = ("就诊号", "姓名", "科室", "医生", "诊室")
    tab.column("就诊号", width=int(screen_width * 0.15), anchor="center")
    tab.column("姓名", width=int(screen_width * 0.25), anchor="center")
    tab.column("科室", width=int(screen_width * 0.2), anchor="center")
    tab.column("医生", width=int(screen_width * 0.2), anchor="center")
    tab.column("诊室", width=int(screen_width * 0.2), anchor="center")
    # 设置表头
    tab.heading("就诊号", text="就诊号")
    tab.heading("姓名", text="姓名")
    tab.heading("科室", text="科室")
    tab.heading("医生", text="医生")
    tab.heading("诊室", text="诊室")

    Label(win, text='温馨提醒：请保持安静，耐心等待', background='lightcyan', font=('Microsoft YaHei', 16), fg='darkgray')\
        .place(x=0, y=screen_height - 50, width=screen_width, height=50)
    win.mainloop()

