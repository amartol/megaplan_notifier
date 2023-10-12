import os
import pystray
import sys
from sys import exit
from tkinter import *
from tkinter import ttk
from PIL import Image
from threading import Thread, Lock
from pystray import MenuItem as item
from tkinter.messagebox import showerror, showinfo
from megaplan import *
from sqlite import *
from time import sleep

DB_PATH = f"{os.getcwd()}/tasks"
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

MEGAPLAN_HOST = '192.168.0.37'

query_task_url = "/api/v3/task"
query_notify_cnt = "/api/v3/notification"
query_userinfo = "/api/v3/currentUser"
query_chat_msg_cnt = "/api/v3/chat/totalUnreadCommentsCount"
# query_prog = "/api/v3/task/extraFields"
# query_task_filter = "/api/v3/taskFilter"
task_filter = """{"filter": {"contentType": "TaskFilter", "id": "incoming"}}"""

SLEEP_TASK_TIME = 3 * 60
SLEEP_MSG_TIME = 60
TIME_TRAY_ANIMATE = 1

SW_VERSION = "0.0.2"

chat_notify_displayed = False
serv_connect = False
unread_msg_cnt = 0

tray_lock = Lock()


class MsgWarn(Toplevel):
    def close(self):
        global chat_notify_displayed
        if self.msg_type == "chat_msg":
            chat_notify_displayed = False
        self.destroy()

    def __init__(self, parent, msg_type: str, text: str):
        global chat_notify_displayed
        super().__init__(parent)
        self.msg_type = msg_type
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.title("Уведомление")
        # self.win.iconbitmap("favicon.ico")
        window_width = 360
        window_height = 100
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")  # position on center screen
        self.attributes('-topmost', 'true')
        # self.image = PhotoImage(file="./add_task.png")
        for c in range(3):
            self.columnconfigure(index=c, weight=1)
        for r in range(3):
            self.rowconfigure(index=r, weight=1)

        if self.msg_type == "task":
            label_txt = "Новая задача"
        else:
            chat_notify_displayed = True
            label_txt = "Новое cообщение чата"
        self.label_txt = ttk.Label(master=self, text=f"{label_txt}! Зайдите в Мегаплан для просмотра",
                                   background="#FF002C")
        self.label_txt.grid(row=0, column=0, columnspan=3, padx=5, pady=5)
        self.label_logo = ttk.Label(master=self, text=text)
        self.label_logo.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=NSEW)
        self.button = ttk.Button(self, text="Ок", command=self.close)
        self.button.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=NSEW)
        # self.label_logo.pack()


class Userdata:
    def save_userdata(self):
        name = self.entry_user.get()
        password = self.entry_pass.get()
        try:
            tokenid = MegaplanAuth(MEGAPLAN_HOST).get_token(name, password)  # connect to megaplan server
        except (KeyError, NameError):
            showerror("Ошибка!", "Неверные данные пользователя")
            self.entry_user.delete(first=0, last=END)
            self.entry_pass.delete(first=0, last=END)
            return 1
        if name and password:
            print('create user account...')
            self.database.create_table(
                table_name='user',
                table_config='login TEXT, password TEXT')
            self.database.connection.execute(''' INSERT INTO user (login, password) VALUES(?, ?) ''', (name, password))
            self.database.connection.commit()
            if self.database.table_exists('user'):
                print('user table created!----')
                self.w_userdata.destroy()

    def __init__(self, database: SqliteDatabase):
        self.w_userdata = Toplevel(root)
        self.w_userdata.attributes('-topmost', 'true')
        self.database = database
        # w_userdata.overrideredirect(True)
        # w_userdata.protocol("WM_DELETE_WINDOW", lambda: dismiss(w_userdata))
        self.entry_user = ttk.Entry(self.w_userdata, width=35)
        self.label_user = ttk.Label(self.w_userdata, text="user")
        self.label_user.grid(row=0, column=0, columnspan=1, padx=5, pady=5)
        self.entry_user.grid(row=0, column=1, padx=5, pady=5)

        self.entry_pass = ttk.Entry(self.w_userdata, width=35)
        self.label_pass = ttk.Label(self.w_userdata, text="pass")
        self.label_pass.grid(row=1, column=0, columnspan=1, padx=5, pady=5)
        self.entry_pass.grid(row=1, column=1, padx=5, pady=5)

        self.button = ttk.Button(self.w_userdata, text="Submit", command=self.save_userdata)
        self.button.grid(row=2, column=1, padx=5, pady=5)
        self.w_userdata.wait_window()


def tray_animate_task(tray_icon: pystray.Icon):
    global unread_msg_cnt
    img_notify = Image.open('megaplan_notify.png')
    img_icon = Image.open('megaplan.png')
    _flag_attention = True
    with tray_lock:
        while unread_msg_cnt:
            if _flag_attention:
                tray_icon.icon = img_notify
                _flag_attention = False
            else:
                tray_icon.icon = img_icon
                _flag_attention = True
            sleep(TIME_TRAY_ANIMATE)
        else:
            tray_icon.icon = img_icon


def check_task(mega_api: MegaplanApi):

    with SqliteDatabase(DB_PATH) as db:
        db_tasks = db.get_tasks_id()  # get task from database file
        if db_tasks:
            megaplan_actual_tasks = mega_api.get_query_v3(query_task_url)
            server_tasks = []
            for i in range(len(megaplan_actual_tasks)):
                # print(f"{get_query_task[i]}\n")
                server_tasks.append(megaplan_actual_tasks[i]['id'])
            # print(f"server_tasks is {server_tasks}, db_task is {db_tasks}")
            diff_task = set(db_tasks) - set(server_tasks)  # check for need cleaning database
            if diff_task:
                print(f"Different id's {diff_task}, delete it")
                for task in diff_task:
                    db.delete_task(task)

    while True:
        megaplan_tasks = mega_api.get_query_v3(query_task_url, payload=task_filter)
        for i in range(len(megaplan_tasks)):
            print(megaplan_tasks[i])
            server_task_id = megaplan_tasks[i]['id']
            # print(server_task_id)
            if server_task_id not in db_tasks:
                print(f"add task {server_task_id} to db")
                with SqliteDatabase(DB_PATH) as task_storage:
                    if megaplan_tasks[i]['owner'].get('name') is not None:
                        owner_name = megaplan_tasks[i]['owner']['name']
                    else:
                        owner_name = api.get_query_v3(query_userinfo)['name']
                    # print(f"{owner_name}\n")
                    task_storage.insert_task(server_task_id, megaplan_tasks[i]['name'], owner_name)
                    db_tasks = task_storage.get_tasks_id()
                    print(f"db task now is {db_tasks}")
                    MsgWarn(root, "task", megaplan_tasks[i]['name'])

        sleep(SLEEP_TASK_TIME)


def check_chat_msg(mega_api: MegaplanApi, tray_icon: pystray.Icon):
    global chat_notify_displayed, unread_msg_cnt
    while True:
        unread_msg_cnt = mega_api.get_query_v3(query_chat_msg_cnt)
        if unread_msg_cnt and not chat_notify_displayed:
            MsgWarn(root, "chat_msg", f"Новых сообщений: {unread_msg_cnt}")
            tray_icon.notify(f'Новых сообщений чата:{unread_msg_cnt}')
            tray_animate = Thread(target=tray_animate_task, args=(tray_icon,), daemon=True)
            if not tray_lock.locked():
                tray_animate.start()
        sleep(SLEEP_MSG_TIME)


def win_finish():
    root.destroy()  # ручное закрытие окна и всего приложения
    print("Закрытие приложения")
    exit(0)


def after_click(icon, query):
    if str(query) == "Восстановить окно":
        icon.stop()
        root.after(100, root.deiconify)
    elif str(query) == "Выход":
        icon.stop()
        root.destroy()


def icon_tray_thread():
    global serv_connect
    root.withdraw()
    img = Image.open('megaplan.png')

    icon = pystray.Icon("Megaplan", img, "Megaplan notify", menu=pystray.Menu(
        item("Восстановить окно", after_click),
        item("Выход", after_click)))

    if serv_connect:
        chat_polling = Thread(target=check_chat_msg, args=(api, icon), daemon=True)
        chat_polling.start()
        task_polling = Thread(target=check_task, args=(api,), daemon=True)
        task_polling.start()
    icon.run()


def win_minimize():
    icon_tray = Thread(target=icon_tray_thread, daemon=True)
    icon_tray.start()


def show_version():
    showinfo(message=f"Версия программы {SW_VERSION}")


if __name__ == '__main__':
    root = Tk()
    root.title("Megaplan notifier")
    root.geometry('320x240+200+100')
    if os.name != "posix":
        root.iconbitmap(os.path.join(os.getcwd(), "icon.ico"))
    main_menu = Menu()
    main_menu.add_cascade(label="Версия", command=show_version)
    main_menu.add_cascade(label="Выход", command=win_finish)
    root.config(menu=main_menu)

    for c in range(3):
        root.columnconfigure(index=c, weight=1)
    for r in range(3):
        root.rowconfigure(index=r, weight=1)

    with SqliteDatabase(DB_PATH) as db:
        if not db.table_exists('user'):  # check if user in database exist
            print('user not found, create it')
            Userdata(db)

        user_data = db.sql_to_dict("SELECT login, password FROM user")
        if user_data:
            user_name = user_data[0]['login']
            user_pwd = user_data[0]['password']
        else:
            exit(1)
        # print(user_name, user_pwd)
        if not db.table_exists('tasks'):  # check if task list in database exist
            print("create task table on db")
            db.create_table('tasks',
                            "task_id TEXT, task_name TEXT, task_owner TEXT")
    try:
        serv_response = requests.get(f'http://{MEGAPLAN_HOST}', timeout=3)  # check if megaplan server exist
        if serv_response.status_code == 401:
            serv_connect = True
    except requests.ConnectionError:
        showerror(message="Нет соединения с сервером Мегаплан!")
        print("Megaplan host unreachable")

    if serv_connect:
        token_id = MegaplanAuth(MEGAPLAN_HOST).get_token(user_name, user_pwd)  # connect to megaplan server
        api = MegaplanApi(MEGAPLAN_HOST, Token=token_id)
        get_query_userinfo = api.get_query_v3(query_userinfo)
        label_user = ttk.Label(root, text=f"Добро пожаловать, {get_query_userinfo['name']}!")
        label_user.grid(row=0, column=0, ipadx=6, ipady=6, padx=4, pady=4, sticky=NW)
    root.protocol("WM_DELETE_WINDOW", win_minimize)
    win_minimize()
    root.mainloop()
    exit(0)
