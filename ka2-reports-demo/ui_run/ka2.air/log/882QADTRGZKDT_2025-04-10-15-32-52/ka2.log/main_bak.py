#!/usr/bin/env python3
# -*- encoding=utf8 -*-
"""
fire
"""
import multiprocessing
import ast
import sys
import re

import xlrd
import chardet
from airtest.core.android.android import *
from pathlib import Path
from poco.drivers.unity3d import UnityPoco
from env_params import ACCOUNTS

# 监听系统级别弹窗
# todo 结束条件
from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco


auto_setup(__file__)


"""
注意下面有 "todo" 的，都是要根据对应测试的app自定义的
"""


# todo 多机执行时，为了保证含有（注册）业务逻辑不发生注册冲突，可以加（随机睡眠），注册账号名根据（当前时间戳创建）
# todo 本地测试时可以注释掉
# random_sleep = random.randint(0, 3) + random.randint(0, 20) / 10
# print(f"---------- random sleep: {random_sleep} -------------")
# time.sleep(random_sleep)


def modify_file_name():
    base_pth = os.path.dirname(__file__)
    print("base_pth : {}".format(base_pth))
    for root, dirs, files in os.walk(base_pth):
        for file in files:
            # 跳过main.py不处理
            if file == "main.py":
                continue
            # 获取文件名和文件路径
            file_path = os.path.join(root, file)
            file_name = os.path.splitext(file)[0]
            file_ext = os.path.splitext(file)[1]
            encoding = chardet.detect(file_name.encode())['encoding']
            # 替换文件名中的乱码字符
            try:
                real_name = file_name.encode('cp437').decode(encoding)
            except:
                try:
                    real_name = file_name.encode('cp437').decode('gb18030')
                except:
                    real_name = file_name
            print("real_name : {}".format(real_name))
            try:
                new_file_path = os.path.join(root, real_name + file_ext)
                # 重命名文件
                os.rename(file_path, new_file_path)
            except:
                pass


# modify_file_name()


# 脚本所需的基本变量
# ================ # ========start======== # ================
# step1 : 手机默认参数
# run pkg type
run_type = "Android"  # 默认为安卓包
# todo 改为自己要执行的包名
pkg_name = "com.beeplay.card2prepare"
# gol_maxTryTime_info
gol_maxTryTime_info = 3
# todo 图片rgb检验通道是否需要开启，默认（True），要对比的准确点就开启（True），否则就（False）
rgb_type = True
# todo 当前测试执行的环境，默认本地调试为（Test），其他都是线上（UWA平台）
run_env = "Test"
# run_env = "Online"
# todo 本地测试用开关
wake_up_flag = False  # 是否唤醒app
stop_app_flag = False  # 是否在ui测试任务执行结束后，关闭apk包进程

if run_env == "Test":
    print("==========当前device : {}========= ".format(Android().uuid))
else:
    print("========== 当前device : {}========= ".format(device().uuid))
try:
    if run_env == "Test":
        cur_devices = Android().uuid
    else:
        cur_devices = device().uuid
    print(f'当前连接设备号为:[{cur_devices}]')
except Exception as e:
    print("设备连接异常：{}", e)
    sys.exit(-1)
# 连接当前设备实例
if run_type == "Android":
    run_type_obj = connect_device("Android:///{}".format(cur_devices))
    swipe_start_scale = 0.8
    swipe_end_scale = 0.4
    swipe_duration = 0.5
    device_brand = run_type_obj.shell("getprop ro.product.brand").strip("\n")
    print("device_brand : ", type(device_brand))
    device_model = run_type_obj.shell("getprop ro.product.model")
else:
    run_type_obj = connect_device("iOS:///{}".format(cur_devices))  # iOS:///127.0.0.1:8100
    swipe_start_scale = 0.95
    swipe_end_scale = 0.3
    swipe_duration = 0.2
    device_brand = run_type_obj.device_info.get("model", "Unknown")
    device_model = run_type_obj.device_info.get("name")
print("swipe_start_scale : ", swipe_start_scale)
print("swipe_end_scale : ", swipe_end_scale)
print("swipe_duration : ", swipe_duration)
print("device_brand : ", device_brand)
print("device_model : ", device_model)
cur_dev_width, cur_dev_height = run_type_obj.get_current_resolution()
print("当前设备分辨率:", cur_dev_width, cur_dev_height)
# ------------------------------------------------------------------
# step2 : 获取下面所执行的excel表相关信息
# excel_path，icon_path
excel_name = "新手引导.xlsx"
curPath = os.path.dirname(__file__)
excelPath = os.path.join(curPath, excel_name)
print('获取执行的表格所在路径 : ', excelPath)
iconPath = ""
print('获取图标根路径 : ', iconPath)
# 从Excel第几步开始
startID_login = 1
# 最大重试次数。超过该次数直接进行下一步
try_times = []
# todo 选择前置场景用到的sheet名，默认执行的是（main）
sheet_name = "main"
duration = 6
print(" >>> current run sheet_name : {} <<< ".format(sheet_name))
# ------------------------------------------------------------------
# step3. 常见的系统权限弹窗按钮的 XPath 列表

# # 初始化设备和 Poco
# poco = AndroidUiautomationPoco()
system_monitor_type = 1   # 监控模式: 1=全匹配模式(airtest), 2=关键词匹配模式(node节点文本匹配)
permission_buttons = [
    # Meizu
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.android.packageinstaller:id/permission_allow_button",  # 电话权限 允许按钮

    # Redmi
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.lbe.security.miui:id/permission_allow_button",  # 电话权限 始终允许按钮
    "com.lbe.security.miui:id/permission_allow_foreground_only_button",  # 电话权限 仅在使用中允许按钮

    # vivo
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.android.permissioncontroller:id/permission_allow_button",  # 电话权限 允许按钮
    "com.android.permissioncontroller:id/permission_allow_one_time_button",  # 电话权限 本次时使用时允许按钮
    "com.android.packageinstaller:id/permission_allow_button",  # 电话权限 始终允许按钮

    # Honor
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.android.permissioncontroller:id/permission_allow_button",  # 电话权限 始终允许按钮
    "android:id/log_access_dialog_allow_button",  # 设备日志 允许访问一次按钮

    # OnePlus
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.qianxi.fqsg_yy.qxhf:id/tv_ok",  # 个人信息保护指引权限 同意按钮
    "com.android.permissioncontroller:id/permission_allow_button",  # 电话权限 始终允许按钮
]

# 常见的系统权限弹窗按钮的关键词列表
permission_keywords_yes = [
    "允许", "同意", "始终允许", "仅在使用中允许", "本次时使用时允许", "允许访问一次"
]

# permission_keywords_no = [
#     "不", "拒绝", "禁止", "否"
# ]

# ================ # ========end======== # ================
# 函数封装模块


def get_value_from_dict(path, data_dict):
    keys = path.split('.')
    return get_value_recursive(data_dict, keys)


def get_value_recursive(current_dict, keys):
    if not keys:
        return current_dict
    key = keys.pop(0)
    if key in current_dict:
        return get_value_recursive(current_dict[key], keys)
    else:
        raise KeyError(f"Key '{key}' not found in dictionary")


def wake_up(pkg_name, run_type, run_type_obj):
    """
    唤醒设备
    """
    print("开始解锁设备 ...... ")
    if run_type == "Android":
        print("android手机已锁，开始解锁 ...... ")
        wake()
    else:
        loc = run_type_obj.is_locked()
        if loc:
            print("ios手机已锁，开始解锁 ...... ")
            run_type_obj.unlock()
            time.sleep(1)
            # 垂直 沿中间从下往上滑动
            swipe_start = [0.5 * int(cur_dev_width), swipe_start_scale * int(cur_dev_height)]
            swipe_end = [0.5 * int(cur_dev_width), swipe_end_scale * int(cur_dev_height)]
            print("start:{}, end:{}".format(swipe_start, swipe_end))
            run_type_obj.swipe(swipe_start, swipe_end, duration=swipe_duration)
            time.sleep(1)
    try:
        stop_app(pkg_name)
        time.sleep(2)
        start_app(pkg_name)
    except:
        start_app(pkg_name)


def read_excel(file_name, sheet_name):
    """
    读取指定excel表中，指定sheet名的数据
    :param file_name: excel表路径
    :param sheet_name: excel表中指定的sheet名字
    :return:
    """
    data = xlrd.open_workbook(file_name)
    table = data.sheet_by_name(sheet_name)
    # 获取总行数、总列数。因为第一行是title，不参与图片对比所以去除1行
    nrows = table.nrows
    guide_name = table.col_values(1)
    guide_type = table.col_values(2)
    # 获取第5列的内容【强引导ICON名】步骤描述
    step_name = table.col_values(4)
    # 获取第6列的内容【用户自定义的图片对比度】
    current_threshold = table.col_values(5)
    # 获取第7列的内容【用户自定义的等待时间】
    wait_time = table.col_values(6)
    # 获取第8列的内容【特殊操作】
    special_step = table.col_values(7)
    special_step2 = table.col_values(8)
    # 读取Excel表格内所有待执行步骤
    steps_list = list(iconPath + i + ".png" for i in step_name)
    # print("guide_type : ", guide_type)
    # print("step_name : ", step_name)
    # print("current_threshold : ", current_threshold)
    # print("wait_time : ", wait_time)
    # print("special_step : ", special_step)
    # print("nrows : ", nrows)
    # print("steps_list : ", steps_list)
    return guide_name, guide_type, step_name, current_threshold, wait_time, special_step, special_step2, nrows, steps_list


def run_precondition():
    """
    执行前置步骤，一般有特殊处理条件的
    :return:
    """
    if wake_up_flag is True:
        wake_up(pkg_name, run_type, run_type_obj)
    start_time = time.time()
    skip_flag = False

    # app启动后
    # 如果在1分钟内没有检测到 >> 更新 << 就默认当前最新版本，不用更新，直接切换账号，重新注册；
    # 如果在1分钟内检测到 >> 更新 << ，就设置循环查询 >>切换账号<< 按钮，出现该按钮时，更新已经结束；
    try:
        #  todo 如果前置步骤中除了解锁屏幕及开启app，没有其他操作，则直接pass即可
        #  todo 否则，自定义逻辑
        pass
        return True
    except Exception as err:
        print(f"run precondition err : {err}")
        return False


def run_excel_steps(max_try_time, excel_pth, sheet_name, print_type="更新、登录、强制引导"):
    """
    引导类型分类 0 ~ 100(UI图片识别及相关操作)：
                0：循环等待直到目标结束
                1：循环等待直到目标出现
                2：是否进入主界面，未进入直接停止测试
                3：执行完后直接对比其他步
                4：拖拽
                5：强制点击操作（点击成功后会默认睡眠1s）
                6：非强制点击操作
                7：文本输入
                8：断言
                9：重启app

              101 ～ ***(POCO相关操作)
                101：循环等待直到目标结束
                102：循环等待直到目标出现
                103：单击操作；点击后并校验当前控件是否消失
                104：拖拽控件
                105：单击操作；点击后不校验（点击成功后会默认睡眠 0.5 s）
                106：长按控件

    :param max_try_time: 最大重试次数
    :param excel_pth: 读取excel表的名称
    :param sheet_name: 读取表中sheet的名称
    :param print_type: 打印信息标头
    :return: 执行结果
    """
    pre_result = run_precondition()
    print(f"pre_result : {pre_result}")
    if pre_result is True:
        print("**************************** \033[1;32m前置步骤执行成功\033[0m ****************************")

    else:
        print("**************************** \033[1;31m前置步骤执行失败\033[0m ****************************")
        return False
    special_step_dic = {
        4: [[0, 0], 2],
        5: 1,
        6: [0, 0],
        7: "xs" + str(int(time.time())),
        105: 1
    }
    guide_name, guide_type, step_name, current_threshold, \
    wait_time, special_step, special_step2, nrows, \
    steps_list_val = read_excel(excel_pth, sheet_name)
    # startID:从第几步开始执行。rows：获取Excel总列数，即自动化步骤总数
    poco_flag = True
    for i in range(startID_login, nrows):
        # 适配poco操作，尾缀不带png，获取到的是UIObjectProxy
        if guide_type[i] >= 101:
            if poco_flag is True:
                print(" >>> start init poco obj <<< ")
                poco = UnityPoco(device=run_type_obj)
                poco_flag = False
                print("poco : ", poco, id(poco))
            try:
                # 防止关闭游戏导致poco异常
                # poco("UI").child("login_view").offspring("Toggle").child("Background")
                split_str = steps_list_val[i].split(".png")[0]
                poco_obj = eval(split_str)
                # 将生成的Poco对象赋值给poco对象的属性
                setattr(poco, "generated_poco", poco_obj)

                # 使用poco对象执行后续操作
                png_cur = poco.generated_poco  # 示例操作，您可以根据实际需求执行其他操作
            except Exception as err:
                print(f"【前置读取表格中数据异常】- 【{err}】")
                return False
        else:
            png_cur = steps_list_val[i]
        try:
            cur_threshold = float(current_threshold[i]) if current_threshold[i] != '' else 0.6
        except:
            print(f"当前ID【{i}】中对比度参数异常，请检查对应表内数据！！！")
            return False
        try:
            cur_wait_time = float(wait_time[i]) if wait_time[i] != '' else 0
        except:
            print(f"当前ID【{i}】中等待时间参数异常，请检查对应表内数据！！！")
            return False
        try:
            cur_special_step = ast.literal_eval(special_step[i]) \
                if special_step[i] != '' else special_step_dic.get(guide_type[i])
        except:
            try:
                cur_special_step = int(float(special_step[i]) \
                                           if special_step[i] != '' else special_step_dic.get(guide_type[i]))
            except:
                try:
                    cur_special_step = (str(special_step[i]) \
                                            if special_step[i] != '' else special_step_dic.get(guide_type[i]))
                except:
                    print(f"当前ID【{i}】中等特殊操作参数异常，请检查对应表内数据！！！")
                    return False
        cur_special_step2 = special_step2[i]
        print("------------- >>> --------------- >>> -------------------- >>> ----------------------")
        print(f"【{print_type}】 当前步骤ID: 【{i}】, 当前步骤类型: 【{guide_type[i]}】, "
              f"当前任务描述: 【{guide_name[i]}】, 执行图片: 【{png_cur}】, 对比度:【{cur_threshold}】, "
              f"下一步的执行等待时间: 【{cur_wait_time}】, 特殊操作1:【{cur_special_step}】, 特殊操作2:【{cur_special_step2}】.")
        # continue
        # 第二步～最后一步，执行前才有睡眠，睡眠时间是上一步的wait_time参数
        if i >= 2:
            cur_wait_time = float(wait_time[i - 1]) if wait_time[i - 1] != '' else 0
            print(f"         执行第【{i}】 -- 当前需等待: {cur_wait_time}s后继续执行下一步    ")
            sleep(cur_wait_time)
        print("------------- >>> --------------- >>> -------------------- >>> ----------------------")
        try:
            if guide_type[i] == 0:
                # 进入页面后可能 >>自动更新游戏<< ，此时需要校验，直到更新的 >>标识图片<< 消失
                while exists(Template(png_cur, rgb=rgb_type, threshold=cur_threshold)):
                    print(f'发现预期图片【{png_cur}】，等待其消失 ...')
                else:
                    print(f'预期图片【{png_cur}】已经消失 ...')
                    continue

            elif guide_type[i] == 1:
                # 适配一些卡顿的性能差的手机，一般会在登陆，更新，加载资源等地方阻塞，导致后续逻辑异常
                while not exists(Template(png_cur)):
                    print(f'正在查找预期图片【{png_cur}】...')
                    time.sleep(0.2)
                else:
                    print(f'已找到预期图片【{png_cur}】...')
                    continue

            elif guide_type[i] == 2:
                # 进入游戏主界面，一般是在登陆、创角成功后
                for j in range(3):
                    main_icon = os.path.join(iconPath, "引导员对话.png")
                    main_icon_exists = Template(main_icon)
                    if exists(main_icon_exists):
                        print("已成功进入【主界面】...")
                        continue
                    else:
                        print("未成功进入【主界面】, 测试终止 ！！！")
                        return False

            # 【3】次数最多的操作所以此处不处理了，直接放到else的判断分支里
            elif guide_type[i] == 4:
                # 拖拽操作
                try:
                    v1 = wait(Template(png_cur, rgb=rgb_type, threshold=cur_threshold), timeout=20)
                    v2 = (v1[0] + cur_special_step[0][0], v1[1] + cur_special_step[0][1])
                    cur_swipe_duration = cur_special_step[1]
                    swipe(v1, v2, duration=cur_swipe_duration)
                except Exception as err:
                    print(f"【拖拽】- 【{png_cur}】参数获取异常, err: {err}, 退出当前测试！！！")
                    return False
                print(f"【拖拽成功】 - 【{png_cur}】- 【 v1: {v1}, v2: {v2}, duration: {cur_swipe_duration} 】")
                # todo 创建两个进程，分别执行左手指滑动和右手指点击操作
                # p1 = Process(target=swipe_thread, args=(png_cur, v1, v2, cur_swipe_duration))
                # p2 = Process(target=touch_thread, args=(cur_swipe_duration, touch_position))
                # # 启动两个进程
                # p1.start()
                # p2.start()
                # # 等待两个进程结束
                # p1.join()
                # p2.join()

            elif guide_type[i] == 5:
                # 找不到当前图片，不点击会影响到后续执行流程，同时点击成功后会默认睡眠1s，类似 >>确定<< 按钮
                for i in range(cur_special_step):
                    try:
                        # 个别战斗场景耗时较长; wait() 不到就会抛异常】
                        position = wait(Template(png_cur, rgb=rgb_type, threshold=cur_threshold), interval=0.2,
                                        timeout=20)
                        touch(position)
                        print(f"【点击成功】 - 【{png_cur}】")
                    except Exception as err:
                        print("首图匹配失败，准备匹配备用图。异常信息：{}".format(err))
                        png_cur2 = png_cur.replace('.png', '1.png')  # 备用图
                        my_file = Path(png_cur2)
                        if my_file.exists():
                            print(f"备用图存在【{my_file}】，继续执行对比！！！")
                            try:
                                # 个别战斗场景耗时较长;   wait() 不到就会抛异常
                                position = wait(Template(png_cur2, rgb=rgb_type, threshold=0.5), interval=0.2,
                                                timeout=5)
                                touch(position)
                            except Exception as err:
                                print(f"【点击】- 【{png_cur}】异常, err: {err}, 退出当前测试！！！")
                                return False
                        else:
                            print(f"备用图不存在【{my_file}】，跳过当前对比步骤！！！")
                            return False
                    time.sleep(1)

            elif guide_type[i] == 6:
                # 找不到当前图片，不点击不会影响到后续执行流程，类似 >>跳过<< 按钮
                for num in range(2):
                    if exists(Template(png_cur, rgb=rgb_type, threshold=cur_threshold)):
                        touch(Template(png_cur, rgb=rgb_type, threshold=cur_threshold))
                        sleep(1)
                    else:
                        print(f"第【{num}】次【非强制点击操作】, 继续查找当前图片【{png_cur}】")
                        pass

            elif guide_type[i] == 7:
                # try:
                print(f"【正在输入文本】 - cur_special_step:【{cur_special_step}】- cur_special_step2: 【{cur_special_step2}】")
                # 有 "$." 的需要特殊处理在
                if "$." in cur_special_step:
                    cur_special_step = cur_special_step.replace("$", device_brand)
                    cur_special_step = get_value_from_dict(ACCOUNTS, cur_special_step)
                if cur_special_step2 == "" or cur_special_step2 is None:
                    enter_type = False
                else:
                    enter_type = True
                print("enter_type : ", enter_type)
                filtered_text = re.sub(r'[^\w\u4e00-\u9fff]', '', str(cur_special_step))
                text(filtered_text, enter=enter_type)
                time.sleep(1)
            # except:
            #     print(f"【输入文本异常】 - 【{cur_special_step}】")
            #     return False

            elif guide_type[i] == 8:
                for i in range(30):
                    try:
                        print(f"【断言是否存在】 - 【{cur_special_step}】")
                        current_position = assert_exists(Template(png_cur, rgb=rgb_type, threshold=cur_threshold),
                                                         msg="断言当前图片是否存在")
                        print(f"【断言存在】 - 【{current_position}】")
                        return True
                    except Exception as err:
                        print(f"【断言是否存在】 - 【{cur_special_step}】- 【{err}】")
                        continue
                return False

            elif guide_type[i] == 9:
                try:
                    print(f"【重启App】")
                    stop_app(pkg_name)
                    time.sleep(1)
                    start_app(pkg_name)
                except Exception as err:
                    print(f"【重启App异常】- 【{err}】")
                    return False

            elif guide_type[i] == 10:
                # 判断相对坐标是否有值，如果有值则直接点击该值替代图片对比
                base_png = png_cur.split(".png")[0]
                for current_i in range(10):
                    if current_i == 0:
                        cur_threshold = cur_threshold
                        v_cur_name = base_png + ".png"
                    else:
                        cur_threshold = 0.55
                        v_cur_name = base_png + f'{current_i}.png'
                    if not Path(v_cur_name).exists():
                        print(f"当前图片【{v_cur_name}】不存在，结束对比！！！")
                        return False
                    else:
                        print(f"当前图片【{v_cur_name}】存在，开始本次对比！！！")
                    try:
                        v_cur = Template(v_cur_name, rgb=rgb_type, threshold=cur_threshold)
                        if cur_special_step == "" or cur_special_step is None:
                            position = wait(v_cur, interval=0.2, timeout=20)
                        else:
                            position = wait(v_cur, interval=0.2, timeout=20)[0] + cur_special_step[0], \
                                       wait(v_cur, interval=0.2, timeout=20)[1] + cur_special_step[1]
                        touch(position)
                        print("position : ", position)
                        sleep(2)
                        break
                    # 没有抛异常证明执行成功，那么将执行结束时间赋当前的值
                    # 首图匹配失败，准备匹配备用图......
                    except Exception as e:
                        print(f"当前图匹配失败，继续匹配备用图 -- 【{base_png + f'{int(current_i) + 1}.png'}】。异常信息：{e}")
                        continue
            # todo -------------------------- 此处开始均为poco控件操作封装 --------------------------
            elif guide_type[i] == 101:
                print(f"开始等待【Poco控件】-【{png_cur}】出现 .")
                png_cur.wait_for_appearance()
                while True:
                    if png_cur.exists() is False:
                        print(f"正在等待【Poco控件】-【{steps_list_val[i]}】出现 .")
                    else:
                        print(f"【Poco控件】-【{steps_list_val[i]}】已出现 .")
                        break

            elif guide_type[i] == 102:
                print(f"开始等待【Poco控件】-【{png_cur}】消失 .")
                while True:
                    if png_cur.exists() is True:
                        print(f"正在等待【Poco控件】-【{steps_list_val[i]}】消失 .")
                    else:
                        print(f"【Poco控件】-【{steps_list_val[i]}】已消失 .")
                        break

            elif guide_type[i] == 103:
                print(f"单击并校验【Poco控件】-【{png_cur}】 .")
                png_cur.wait_for_appearance()
                if not cur_special_step:
                    try:
                        anchor_point = png_cur.attr("anchorPoint")
                        print(f"单击并校验【Poco控件】-【{png_cur}】- 【锚点位置: {anchor_point}】.")
                        png_cur.focus(anchor_point).click()
                    except Exception as err:
                        print(f"单击并校验【Poco控件】-【{png_cur}】- 【异常】- 【{err}】.")
                        try:
                            png_cur.click()
                        except:
                            return False
                else:
                    try:
                        png_cur.focus(cur_special_step).click()
                    except:
                        return False
                time.sleep(2)
                while png_cur.exists():
                    print(f"校验【Poco控件】是否消失 -【{png_cur}】- 第【{len(try_times)}】次开始 .")
                    if len(try_times) < max_try_time:
                        if not cur_special_step:
                            try:
                                anchor_point = png_cur.attr("anchorPoint")
                                print(f"单击并校验【Poco控件】-【{png_cur}】- 【锚点位置: {anchor_point}】.")
                                png_cur.focus(anchor_point).click()
                            except Exception as err:
                                print(f"单击并校验【Poco控件】-【{png_cur}】- 【异常】- 【{err}】.")
                                try:
                                    png_cur.click()
                                except:
                                    pass
                                pass
                        else:
                            try:
                                png_cur.focus(cur_special_step).click()
                            except:
                                pass
                        try_times.append(i)
                    else:
                        print(f"单击并校验【Poco控件】-【{png_cur}】- 【失败】- 【控件未消失】 .")
                        return False
                else:
                    print(f"单击并校验【Poco控件】-【{png_cur}】- 第【{len(try_times)}】次成功 .")
                    try_times.clear()

            elif guide_type[i] == 104:
                print(f"拖拽【Poco控件】-【{png_cur}】 .")
                png_cur.wait_for_appearance()
                if not cur_special_step:
                    print(f"拖拽【Poco控件】-【异常】- 【缺少目标位置】 .")
                    return False
                else:
                    try:
                        swipe_pur_png = eval(cur_special_step)
                        setattr(poco, "swipe_poco", swipe_pur_png)
                        swipe_poco_obj = poco.swipe_poco
                        swipe_anchor_point = swipe_poco_obj.attr("anchorPoint")
                        anchor_point = png_cur.attr("anchorPoint")
                        print(f"拖拽【Poco控件】-【{png_cur}】- 【锚点位置: {anchor_point}】=== > "
                              f"拖拽至【Poco控件】-【{cur_special_step}】- 【目标锚点位置: {swipe_anchor_point}】.")
                        png_cur.focus(anchor_point).drag_to(swipe_poco_obj.focus(swipe_anchor_point))
                    except:
                        return False
                time.sleep(0.5)

            elif guide_type[i] == 105:
                print(f"单击不校验【Poco控件】-【{png_cur}】 .")
                png_cur.wait_for_appearance()
                for i in range(cur_special_step):
                    try:
                        anchor_point = png_cur.attr("anchorPoint")
                        print(f"单击不校验【Poco控件】-【{png_cur}】- 【锚点位置: {anchor_point}】.")
                        png_cur.focus(anchor_point).click()
                    except Exception as err:
                        print(f"单击不校验【Poco控件】-【{png_cur}】- 【异常】- 【{err}】.")
                        try:
                            png_cur.click()
                        except:
                            return False
                        return False
                    time.sleep(0.5)

            elif guide_type[i] == 106:
                print(f"长点击【Poco控件】-【{png_cur}】 .")
                png_cur.wait_for_appearance()
                if not cur_special_step:
                    try:
                        anchor_point = png_cur.attr("anchorPoint")
                        print(f"长点击【Poco控件】-【{png_cur}】- 【锚点位置: {anchor_point}】.")
                        png_cur.focus(anchor_point).long_click(cur_special_step2)
                    except Exception as err:
                        print(f"长点击【Poco控件】-【{png_cur}】- 【异常】- 【{err}】.")
                        try:
                            png_cur.long_click(cur_special_step2)
                        except:
                            return False
                        return False
                else:
                    try:
                        png_cur.focus(cur_special_step).long_click(cur_special_step2)
                    except:
                        return False
                time.sleep(0.5)

            elif guide_type[i] == 107:
                # todo set_text()
                pass

            else:
                # 判断相对坐标是否有值，如果有值则直接点击该值替代图片对比
                base_png = png_cur.split(".png")[0]
                for current_i in range(10):
                    if current_i == 0:
                        cur_threshold = cur_threshold
                        v_cur_name = base_png + ".png"
                    else:
                        cur_threshold = 0.55
                        v_cur_name = base_png + f'{current_i}.png'
                    if not Path(v_cur_name).exists():
                        print(f"当前图片【{v_cur_name}】不存在，结束对比！！！")
                        return False
                    else:
                        print(f"当前图片【{v_cur_name}】存在，开始本次对比！！！")
                    try:
                        v_cur = Template(v_cur_name, rgb=rgb_type, threshold=cur_threshold)
                        if cur_special_step == "" or cur_special_step is None:
                            position = wait(v_cur, interval=0.2, timeout=20)
                        else:
                            print("cur_special_step : ", cur_special_step)
                            print("cur_special_step : ", cur_special_step[0],cur_special_step[1])
                            position = wait(v_cur, interval=0.2, timeout=20)[0] + cur_special_step[0], \
                                       wait(v_cur, interval=0.2, timeout=20)[1] + cur_special_step[1]
                        touch(position)
                        print("当前步骤类型: 【3.0】, 点击完坐标 -> 再次判断图片是否仍存在: 【{}】".format(exists(v_cur)))
                        sleep(2)
                        while exists(v_cur) and len(try_times) < max_try_time:
                            print(
                                "【更新、登录、开场】当前步骤ID:[{}]。点击完坐标，但图片依然存在。将进入第[{}]次循环判断逻辑。将点击[{}]--->\n".format(
                                    i,
                                    len(try_times),
                                    position))
                            touch(position)
                            sleep(2)
                            try_times.append(i)
                        if exists(v_cur):
                            print("【更新、登录、开场】当前步骤ID:[{}]。点击完坐标[{}]后图片依然存在，判断失败！！！\n".format(current_i, position))
                            raise ("【更新、登录、开场】当前步骤ID:[{}]。点击完坐标[{}]后图片依然存在，判断失败！！！\n".format(current_i, position))
                        else:
                            print("【更新、登录、开场】当前步骤ID:[{}]。点完坐标[{}]后图片消失 ！！！对比成功，继续下一张图片对比！！！\n".format(current_i, position))
                            try_times.clear()
                            break
                    # 没有抛异常证明执行成功，那么将执行结束时间赋当前的值
                    # 首图匹配失败，准备匹配备用图......
                    except Exception as e:
                        print(f"当前图匹配失败，继续匹配备用图 -- 【{base_png + f'{int(current_i) + 1}.png'}】。异常信息：{e}")
                        continue
        except Exception as err:
            print(f"error {err}")
            return False

    return True


# def monitor_popups(monitor_flag):
#     """
#     监控系统弹窗并自动点击关闭
#     """
#     poco_obj = AndroidUiautomationPoco()
#     print("============> 开始监控系统权限弹窗 <==============")
#     while monitor_flag.value:
#         try:
#             # poco_obj("com.lbe.security.miui:id/permission_allow_foreground_only_button").click()
#             for xpath in permission_buttons:
#                 print(f"====> start check xpath :{xpath} <===")
#                 if poco_obj(xpath).exists():
#                     poco_obj(xpath).click()
#                     time.sleep(1)
#                     # 判断弹窗是否消失
#                     if not poco_obj(xpath).exists():
#                         print(f"❀ 检测到系统弹窗按钮：【{xpath}】，关闭弹窗：【✓】\r\n")
#                     else:
#                         print(f"❀ 检测到系统弹窗按钮：【{xpath}】，关闭弹窗：【✘】\r\n")
#         except Exception as err:
#             print(f"⛔︎ 监控弹窗时发生错误：【{err}】")
#         time.sleep(0.5)


def monitor_popups(monitor_flag):
    """
    监控系统弹窗并自动点击关闭
    """
    android_poco = AndroidUiautomationPoco()
    print("============> 开始监控系统权限弹窗 <==============")
    while monitor_flag.value:
        try:
            # 遍历页面上的所有控件
            for node in android_poco():
                # 获取控件的文本内容
                text = node.get_text()
                if text:
                    # 检查文本内容是否包含任何关键词,
                    # todo 后续考虑是否增加 不/否/禁止等 拒绝权限的关键词反推
                    for keyword in permission_keywords_yes:
                        if keyword == text:
                            print(f"❀ 检测到系统弹窗按钮: {node} - {text}，尝试点击关闭...")
                            node.click()
                            time.sleep(1)
                            # 判断弹窗是否消失
                            android_poco_check = AndroidUiautomationPoco()
                            if node not in android_poco_check():
                                print(f"❀ 检测到系统弹窗按钮：{node} - {text}，关闭弹窗：【✓】\r\n")

                            # if not node.exists():
                            #     print(f"❀ 检测到系统弹窗按钮：【{text}】，关闭弹窗：【✓】\r\n")
                            # else:
                            #     print(node, node.exists())
                            #     print(f"❀ 检测到系统弹窗按钮：【{text}】，关闭弹窗：【✘】\r\n")
                            break
        except Exception as err:
            print(f"⛔︎ 监控弹窗时发生错误：【{err}】")
        time.sleep(0.5)


class UIAutomation:
    """
    UI自动化脚本执行类
    """
    def __init__(self):
        self.pkg_name = pkg_name
        self.run_type = run_type
        self.run_type_obj = run_type_obj
        self.monitor_flag = None
        self.monitor_process = None

    def init_monitor(self):
        """初始化系统弹窗监控"""
        self.monitor_flag = multiprocessing.Value('b', True)
        # 使用函数式方法创建进程，避免序列化问题
        self.monitor_process = multiprocessing.Process(
            target=monitor_popups, args=(self.monitor_flag,)
        )
        self.monitor_process.start()

    def run_test(self):
        """执行测试流程"""
        try:
            self.init_monitor()

            # 执行测试步骤
            result = run_excel_steps(gol_maxTryTime_info, excelPath, sheet_name)
            if result:
                print("**************************** \033[1;32m当前测试成功\033[0m ****************************")
            else:
                print("**************************** \033[1;31m当前测试失败\033[0m ****************************")
            print(">>>>>>>>>>>>模拟UI操作")
            time.sleep(20)
            if stop_app_flag:
                stop_app(self.pkg_name)

        except Exception as e:
            print(f"测试执行异常: {e}")
            return False
        finally:
            if self.monitor_process:
                self.monitor_flag.value = False
                self.monitor_process.join()
                print(">============ 终止监控系统权限弹窗 ==============<")
        return True



automation = UIAutomation()
automation.run_test()

# if __name__ == "__main__":
#     """主入口函数"""
#     automation = UIAutomation()
#     automation.run_test()
