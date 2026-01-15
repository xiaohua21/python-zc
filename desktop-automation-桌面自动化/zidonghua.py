import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
import keyboard
import mouse
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard
from pynput.mouse import Button
from datetime import datetime


class AutomationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("桌面自动化工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5, font=('Arial', 10))
        self.style.configure("TLabel", font=('Arial', 10))
        self.style.configure("Header.TLabel", font=('Arial', 12, 'bold'))

        # 初始化变量
        self.is_recording = False
        self.is_playing = False
        self.is_paused = False
        self.events = []
        self.current_file = None
        self.play_thread = None
        self.record_thread = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.start_time = None
        self.last_event_time = None
        self.playback_speed = 1.0
        self.repeat_count = 1
        self.current_repeat = 0

        # 创建UI
        self.create_ui()

        # 快捷键绑定
        self.setup_hotkeys()

        # 当鼠标进入/离开程序窗口时的事件处理
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

    def create_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 状态框架
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="5")
        status_frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 10, 'bold'))
        status_label.pack(side=tk.LEFT, padx=5)

        self.events_count_var = tk.StringVar(value="事件数: 0")
        events_count_label = ttk.Label(status_frame, textvariable=self.events_count_var)
        events_count_label.pack(side=tk.RIGHT, padx=5)

        # 控制框架
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="5")
        control_frame.pack(fill=tk.X, pady=5)

        # 录制按钮
        self.record_btn = ttk.Button(control_frame, text="开始录制 (F9)", command=self.toggle_recording)
        self.record_btn.grid(row=0, column=0, padx=5, pady=5)

        # 播放按钮
        self.play_btn = ttk.Button(control_frame, text="开始播放 (F10)", command=self.toggle_playback)
        self.play_btn.grid(row=0, column=1, padx=5, pady=5)

        # 暂停按钮
        self.pause_btn = ttk.Button(control_frame, text="暂停 (F11)", command=self.toggle_pause)
        self.pause_btn.grid(row=0, column=2, padx=5, pady=5)
        self.pause_btn.state(['disabled'])

        # 停止按钮
        self.stop_btn = ttk.Button(control_frame, text="停止 (F12)", command=self.stop_all)
        self.stop_btn.grid(row=0, column=3, padx=5, pady=5)

        # 退出按钮
        self.exit_btn = ttk.Button(control_frame, text="退出", command=self.exit_program)
        self.exit_btn.grid(row=0, column=4, padx=5, pady=5)

        # 文件操作框架
        file_frame = ttk.LabelFrame(main_frame, text="文件操作", padding="5")
        file_frame.pack(fill=tk.X, pady=5)

        # 保存按钮
        self.save_btn = ttk.Button(file_frame, text="保存", command=self.save_events)
        self.save_btn.grid(row=0, column=0, padx=5, pady=5)

        # 加载按钮
        self.load_btn = ttk.Button(file_frame, text="加载", command=self.load_events)
        self.load_btn.grid(row=0, column=1, padx=5, pady=5)

        # 当前文件标签
        self.file_var = tk.StringVar(value="当前文件: 无")
        file_label = ttk.Label(file_frame, textvariable=self.file_var)
        file_label.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # 设置框架
        settings_frame = ttk.LabelFrame(main_frame, text="设置", padding="5")
        settings_frame.pack(fill=tk.X, pady=5)

        # 播放速度框架
        speed_frame = ttk.Frame(settings_frame)
        speed_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        ttk.Label(speed_frame, text="播放速度:").pack(side=tk.LEFT, padx=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.1, to=10000.0, orient=tk.HORIZONTAL,
                                variable=self.speed_var, length=200, command=self.update_speed_label)
        speed_scale.pack(side=tk.LEFT, padx=5)

        self.speed_label_var = tk.StringVar(value="1.0x")
        speed_label = ttk.Label(speed_frame, textvariable=self.speed_label_var, width=8)
        speed_label.pack(side=tk.LEFT, padx=5)

        # 预设速度按钮
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=2, sticky=tk.W)

        ttk.Label(preset_frame, text="预设速度:").pack(side=tk.LEFT, padx=5)
        for speed in [1, 10, 100, 1000, 10000]:
            preset_btn = ttk.Button(preset_frame, text=f"{speed}x",
                                    command=lambda s=speed: self.set_preset_speed(s), width=5)
            preset_btn.pack(side=tk.LEFT, padx=2)

        # 重复次数
        repeat_frame = ttk.Frame(settings_frame)
        repeat_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        ttk.Label(repeat_frame, text="重复次数:").pack(side=tk.LEFT, padx=5)
        self.repeat_var = tk.IntVar(value=1)
        repeat_spinbox = ttk.Spinbox(repeat_frame, from_=1, to=99999, textvariable=self.repeat_var, width=8)
        repeat_spinbox.pack(side=tk.LEFT, padx=5)

        # 快捷键提示框架
        hotkey_frame = ttk.LabelFrame(main_frame, text="快捷键", padding="5")
        hotkey_frame.pack(fill=tk.X, pady=5)

        hotkeys = [
            "F9: 开始/停止录制",
            "F10: 开始/停止播放",
            "F11: 暂停/继续",
            "F12: 停止所有操作",
            "ESC: 紧急停止"
        ]

        for i, hotkey in enumerate(hotkeys):
            ttk.Label(hotkey_frame, text=hotkey).grid(row=i // 3, column=i % 3, padx=10, pady=2, sticky=tk.W)

        # 日志框架
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=5, width=50, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(self.log_text, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def setup_hotkeys(self):
        # 设置全局热键
        keyboard.add_hotkey('f9', self.toggle_recording)
        keyboard.add_hotkey('f10', self.toggle_playback)
        keyboard.add_hotkey('f11', self.toggle_pause)
        keyboard.add_hotkey('f12', self.stop_all)
        keyboard.add_hotkey('esc', self.emergency_stop)

    def update_speed_label(self, *args):
        self.playback_speed = self.speed_var.get()
        if self.playback_speed < 100:
            self.speed_label_var.set(f"{self.playback_speed:.1f}x")
        else:
            self.speed_label_var.set(f"{int(self.playback_speed)}x")

    def set_preset_speed(self, speed):
        self.speed_var.set(speed)
        self.update_speed_label()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def on_mouse_enter(self, event):
        # 当鼠标进入程序窗口时暂停录制
        if self.is_recording and not self.is_paused:
            self.log("鼠标进入程序窗口，暂停录制")
            self.pause_recording()

    def on_mouse_leave(self, event):
        # 当鼠标离开程序窗口时恢复录制
        if self.is_recording and self.is_paused:
            self.log("鼠标离开程序窗口，恢复录制")
            self.resume_recording()

    def toggle_recording(self):
        if self.is_playing:
            self.log("请先停止播放")
            return

        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.events = []
        self.is_recording = True
        self.status_var.set("正在录制...")
        self.record_btn.config(text="停止录制 (F9)")
        self.events_count_var.set("事件数: 0")
        self.log("开始录制")

        # 记录开始时间
        self.start_time = time.time()
        self.last_event_time = self.start_time

        # 启动监听线程
        self.record_thread = threading.Thread(target=self.record_events)
        self.record_thread.daemon = True
        self.record_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_paused = False

        # 停止监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

        self.status_var.set("录制已停止")
        self.record_btn.config(text="开始录制 (F9)")
        self.log(f"停止录制，共记录了 {len(self.events)} 个事件")

    def pause_recording(self):
        if not self.is_recording or self.is_paused:
            return

        self.is_paused = True

        # 停止监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

        self.status_var.set("录制已暂停")
        self.log("录制已暂停")

    def resume_recording(self):
        if not self.is_recording or not self.is_paused:
            return

        self.is_paused = False
        self.last_event_time = time.time()  # 更新时间，避免暂停时间被计入

        # 重新启动监听器
        self.setup_listeners()

        self.status_var.set("正在录制...")
        self.log("录制已恢复")

    def record_events(self):
        self.setup_listeners()

    def setup_listeners(self):
        # 设置鼠标监听器
        self.mouse_listener = pynput_mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )
        self.mouse_listener.start()

        # 设置键盘监听器
        self.keyboard_listener = pynput_keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.keyboard_listener.start()

    def on_mouse_move(self, x, y):
        if not self.is_recording or self.is_paused:
            return

        current_time = time.time()
        # 只记录每隔一定时间的移动，避免记录过多事件
        if current_time - self.last_event_time > 0.05:  # 每50毫秒记录一次
            event = {
                'type': 'mouse_move',
                'x': x,
                'y': y,
                'time': current_time - self.last_event_time
            }
            self.events.append(event)
            self.last_event_time = current_time
            self.events_count_var.set(f"事件数: {len(self.events)}")

    def on_mouse_click(self, x, y, button, pressed):
        if not self.is_recording or self.is_paused:
            return

        current_time = time.time()
        event = {
            'type': 'mouse_click',
            'x': x,
            'y': y,
            'button': str(button).split('.')[-1],  # 转换为字符串，例如 'left'
            'pressed': pressed,
            'time': current_time - self.last_event_time
        }
        self.events.append(event)
        self.last_event_time = current_time
        self.events_count_var.set(f"事件数: {len(self.events)}")

    def on_mouse_scroll(self, x, y, dx, dy):
        if not self.is_recording or self.is_paused:
            return

        current_time = time.time()
        event = {
            'type': 'mouse_scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'time': current_time - self.last_event_time
        }
        self.events.append(event)
        self.last_event_time = current_time
        self.events_count_var.set(f"事件数: {len(self.events)}")

    def on_key_press(self, key):
        if not self.is_recording or self.is_paused:
            return

        current_time = time.time()
        try:
            # 正常键
            key_char = key.char
        except AttributeError:
            # 特殊键
            key_char = str(key).split('.')[-1]

        event = {
            'type': 'key_press',
            'key': key_char,
            'time': current_time - self.last_event_time
        }
        self.events.append(event)
        self.last_event_time = current_time
        self.events_count_var.set(f"事件数: {len(self.events)}")

    def on_key_release(self, key):
        if not self.is_recording or self.is_paused:
            return

        current_time = time.time()
        try:
            # 正常键
            key_char = key.char
        except AttributeError:
            # 特殊键
            key_char = str(key).split('.')[-1]

        event = {
            'type': 'key_release',
            'key': key_char,
            'time': current_time - self.last_event_time
        }
        self.events.append(event)
        self.last_event_time = current_time
        self.events_count_var.set(f"事件数: {len(self.events)}")

    def toggle_playback(self):
        if self.is_recording:
            self.log("请先停止录制")
            return

        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        if not self.events:
            self.log("没有可播放的事件")
            return

        self.is_playing = True
        self.is_paused = False
        self.status_var.set("正在播放...")
        self.play_btn.config(text="停止播放 (F10)")
        self.pause_btn.state(['!disabled'])
        self.repeat_count = self.repeat_var.get()
        self.current_repeat = 1

        self.log(f"开始播放 (速度: {self.playback_speed:.1f}x, 重复: {self.repeat_count}次)")

        # 启动播放线程
        self.play_thread = threading.Thread(target=self.play_events)
        self.play_thread.daemon = True
        self.play_thread.start()

    def stop_playback(self):
        if not self.is_playing:
            return

        self.is_playing = False
        self.is_paused = False
        self.status_var.set("播放已停止")
        self.play_btn.config(text="开始播放 (F10)")
        self.pause_btn.state(['disabled'])
        self.log("播放已停止")

    def toggle_pause(self):
        if not self.is_playing:
            return

        if self.is_paused:
            self.is_paused = False
            self.status_var.set("正在播放...")
            self.pause_btn.config(text="暂停 (F11)")
            self.log("播放已恢复")
        else:
            self.is_paused = True
            self.status_var.set("播放已暂停")
            self.pause_btn.config(text="继续 (F11)")
            self.log("播放已暂停")

    def play_events(self):
        current_repeat = 1

        while current_repeat <= self.repeat_count and self.is_playing:
            self.log(f"播放第 {current_repeat}/{self.repeat_count} 次")

            for i, event in enumerate(self.events):
                if not self.is_playing:
                    return

                # 暂停检查
                while self.is_paused:
                    time.sleep(0.1)
                    if not self.is_playing:
                        return

                # 根据播放速度调整等待时间
                wait_time = event['time'] / self.playback_speed

                # 关键优化点: 设置最小等待时间阈值
                if wait_time > 0.001:  # 只有大于1毫秒才睡眠
                    time.sleep(wait_time)

                # 根据事件类型执行操作
                try:
                    self.execute_event(event)
                    # 更新状态
                    self.status_var.set(f"正在播放... ({i + 1}/{len(self.events)})")
                except Exception as e:
                    self.log(f"执行事件时出错: {str(e)}")

            current_repeat += 1

        # 播放完成
        if self.is_playing:
            self.stop_playback()
            self.status_var.set("播放完成")
            self.log("播放完成")

    def execute_event(self, event):
        event_type = event['type']

        # 高速模式判断
        is_fast_mode = self.playback_speed > 100

        try:
            if event_type == 'mouse_move':
                # 直接设置鼠标位置，不使用平滑移动
                pyautogui.moveTo(event['x'], event['y'], duration=0)

            elif event_type == 'mouse_click':
                # 如果是按下，先确保鼠标在正确位置
                if event['pressed']:
                    # 直接设置位置
                    pyautogui.moveTo(event['x'], event['y'], duration=0)

                    if event['button'] == 'left':
                        pyautogui.mouseDown(x=event['x'], y=event['y'], button='left')
                    elif event['button'] == 'right':
                        pyautogui.mouseDown(x=event['x'], y=event['y'], button='right')
                    elif event['button'] == 'middle':
                        pyautogui.mouseDown(x=event['x'], y=event['y'], button='middle')
                else:
                    if event['button'] == 'left':
                        pyautogui.mouseUp(x=event['x'], y=event['y'], button='left')
                    elif event['button'] == 'right':
                        pyautogui.mouseUp(x=event['x'], y=event['y'], button='right')
                    elif event['button'] == 'middle':
                        pyautogui.mouseUp(x=event['x'], y=event['y'], button='middle')

            elif event_type == 'mouse_scroll':
                # 先确保鼠标在正确位置
                pyautogui.moveTo(event['x'], event['y'], duration=0)

                # 高速模式下增大滚动值
                scroll_multiplier = 200 if is_fast_mode else 100
                pyautogui.scroll(event['dy'] * scroll_multiplier)

            elif event_type == 'key_press':
                try:
                    pyautogui.keyDown(event['key'])
                except Exception as e:
                    pass

            elif event_type == 'key_release':
                try:
                    pyautogui.keyUp(event['key'])
                except Exception as e:
                    pass
        except Exception as e:
            print(f"执行事件错误: {str(e)}")
            # 继续执行，不中断整个回放

    def stop_all(self):
        if self.is_recording:
            self.stop_recording()
        if self.is_playing:
            self.stop_playback()

        self.status_var.set("就绪")
        self.log("所有操作已停止")

    def emergency_stop(self):
        self.stop_all()
        self.log("紧急停止！")
        messagebox.showinfo("紧急停止", "所有操作已紧急停止")

    def exit_program(self):
        # 先停止所有操作
        self.stop_all()
        self.log("程序已退出")
        # 销毁主窗口
        self.root.destroy()

    def save_events(self):
        if not self.events:
            messagebox.showinfo("保存", "没有可保存的事件")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="保存自动化事件"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, indent=2)

            self.current_file = file_path
            self.file_var.set(f"当前文件: {os.path.basename(file_path)}")
            self.log(f"成功保存 {len(self.events)} 个事件到 {file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存失败: {str(e)}")
            self.log(f"保存失败: {str(e)}")

    def load_events(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="加载自动化事件"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.events = json.load(f)

            self.current_file = file_path
            self.file_var.set(f"当前文件: {os.path.basename(file_path)}")
            self.events_count_var.set(f"事件数: {len(self.events)}")
            self.log(f"成功加载 {len(self.events)} 个事件从 {file_path}")
        except Exception as e:
            messagebox.showerror("加载失败", f"加载失败: {str(e)}")
            self.log(f"加载失败: {str(e)}")


def main():
    # 设置 PyAutoGUI 的安全性
    pyautogui.FAILSAFE = True

    # 优化 PyAutoGUI 的性能设置
    pyautogui.PAUSE = 0  # 消除命令之间的默认延迟

    # 降低鼠标移动的精度要求，提高速度
    pyautogui.MINIMUM_DURATION = 0  # 移动时不使用最小duration
    pyautogui.MINIMUM_SLEEP = 0  # 移动时不使用最小睡眠时间

    root = tk.Tk()
    app = AutomationTool(root)
    root.protocol("WM_DELETE_WINDOW", lambda: [app.stop_all(), root.destroy()])
    root.mainloop()


if __name__ == "__main__":
    main()
