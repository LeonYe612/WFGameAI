#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @Time    : 2024/11/27 15:07
# @Author  : Buker
# @File    : env_params.py
# @desc    : 存储所有配置参数


import time

# ---------------- 身份证信息 ---------------
Ids_dic = {"任和": "620523198810120156",
           "王勇": "310107197909294632",
           "李超": "320103198609050776",
           "陈凌枫": "330324198904300218",
           "张仟": "360723199207010317",
           "马凤兰": "230204195606030047",
           "韩龙": "120101198810070517",
           "张旭": "110104198704261237",
           "周辰": "420302198811211324",
           "陈冬": "420702198910107735",
           "杨振琪": "130304198812131514",
           "陈玉花": "37092319861210434X",
           "赵宇涵": "370725199508020011",
           "徐芝鑫": "370212198801241055",
           "徐建超": "13063819890227253X",
           "高智": "522501199008282013",
           "饶桑林": "421181198901101319",
           "吴杨文": "431124198701024018",
           "黄斯敏": "310112199408103914",
           "李豹": "432503198701235019",
           "李冬冬": "513723198608095530",
           "石海波": "430724198612182817",
           "田大伟": "320202198801281514",
           "辜彬礼": "445121199301274596",
           "叶建成": "500226199107221211",
           "林建斌": "352228198611053538",
           "王光虎": "320381198410214913",
           "邱君": "42102319940912635X",
           "吴伟": "350502199306140518",
           "黄锦声": "440682198206162132",
           "刘丹": "430722199307198195",
           "陈蒙": "653126198911080312",
           "王彭全": "420102198710273111",
           "王玉龙": "13042519880910001X",
           "姜龙": "320981198809080972",
           "冀磊": "370982198609101690",
           "刘东川": "513001199103228877",
           "王程龙": "231083198502191814",
           "高科": "370303198601032119",
           "叶菲": "130404198205013028",
           "谢波": "510781198111010459",
           "李冰凌": "620302199212210620",
           "宋震林": "622201197909230032",
           "方存磊": "342422198503180135",
           "余昌隆": "412826198802168051",
           "吕权富": "452527198309202495",
           "崔默": "321088199011118119",
           "王琎": "410105198306172738",
           "叶桂梅": "421123196512041225",
           "刘良鹏": "520112199108100315"
           }
ACCOUNTS = {
    "HUAWEI": {
        "username": "djtest2004",
        "password": "123456"
    },
    "HONOR": {
        "username": "djtest2004",
        "password": "123456"
    },
    "Xiaomi": {
        "username": "djtest2004",
        "password": "654321"
    }
}

# --------------- 脚本默认配置参数 ---------------
# 基础运行配置
BASE_CONFIG = {
    # 运行环境配置
    "run_type": "Android",  # 运行平台类型
    "pkg_name": "com.qianxi.fqsg_yy.qxhf",  # todo 测试应用包名
    # "pkg_name": "com.beeplay.card2test",  # todo 测试应用包名
    "run_env": "Online",  # todo 运行环境(Test/Online)
    "start_system_popups_flag": True,  # todo 是否开启系统弹窗监控线程，默认True，结合 [auto_pause_monitor]，否则会出现监控线程一直运行的情况，可能会影响性能
    "start_foreground_flag": True,  # todo 是否开启apk焦点窗口置顶线程，默认True
    "auto_pause_monitor": True,  # todo 进入主界面后是否自动暂停监控线程，默认True，结合 [start_system_popups_flag]
    "error_continue": False,  # todo 遇到某一步出现异常无法进行后，是否终止当前测试，或者继续
    "wake_up_flag": True,  # 是否自动唤醒app
    "stop_app_flag": True,  # 测试完成后是否关闭应用
    "log_type": 0,  # 打印日志类型：0=打印，1=保存日志至test.log
    "max_try_time": 3,  # 最大重试次数
    "start_app_delay": 3,  # 开启app后睡眠时间，等待app开启
    "start_app_retry_times": 5,  # app应用开启/关闭失败重试次数，默认5次
    "random_sleep": {  # 随机延迟配置(用于多机执行)
        "enable": False,  # 是否通脚本多机器执行时 随机延迟
        "min": 0,  # 最小延迟秒数
        "max": 3  # 最大延迟秒数
    },

    # 图像识别配置
    "rgb_type": True,  # todo 图片rgb检验开关
    "default_threshold": 0.8,  # 默认图像匹配阈值
    "retry_threshold": 0.65,  # 重试时的图像匹配阈值

    # UI操作配置(以下睡眠时间均为对应类型操作后的固定睡眠时间，区别于excel表中的等待时间)
    "default_delay": 0.25,  # 默认执行完当前步骤后，到下一步的睡眠时间(秒)
    "click_delay": 0.5,  # 单击后下一步判断时间(秒)
    "click_retry_interval": 1,  # 单击重试间隔时间(秒)
    "long_click_delay": 1,  # 长按点击后下一步判断时间(秒)
    "swipe_delay": 2,  # 滑动等待超时时间(秒)
    "text_input_delay": 1,  # 文本输入后延迟时间(秒)
    "assert_retry_times": 1,  # 断言重试次数(次)
    "backup_pics_nums": 30,  # 备选图上限数
    "click_disappear_retry_times": 5,  # 点击图片后，图片消失，重试次数
    "wait_timeout": 120,  # 等待图片出现/消失 默认超时时间 120S
    "coordinate_click_interval": 20,  # 点击指定坐标，多次点击循环间隔时间， 默认 20S

    # POCO操作配置
    "poco_wait_appearance_timeout": 120,  # POCO控件等待出现超时时间(秒)，系统默认120s

    # 设备默认解锁屏幕滑动参数
    "device_info": {
        "android": {
            "swipe_start_scale": 0.8,  # 滑动起始比例
            "swipe_end_scale": 0.4,  # 滑动结束比例
            "swipe_duration": 0.5,  # 滑动持续时间
        },
        "ios": {
            "swipe_start_scale": 0.95,  # 滑动起始比例
            "swipe_end_scale": 0.3,  # 滑动结束比例
            "swipe_duration": 0.2,  # 滑动持续时间
            "device_url": "127.0.0.1:8100"  # iOS设备连接地址
        }
    },

    # 特殊步骤参数配置
    "special_step_config": {
    }
}

# Excel配置
EXCEL_CONFIG = {
    "excel_name": "新手引导_1.xlsx",  # Excel文件名
    # "excel_name": "新手引导.xlsx",  # Excel文件名
    "start_id_login": 1,  # 登录开始步骤ID
    "sheet_name": "main",  # 工作表名称
    "duration": 6,  # 默认操作间隔时间(秒)
    "icon_path": "",  # 图标路径
}

# 权限按钮配置
SYSTEM_PERMISSION_CONFIG = {
    # 监控模式
    "system_monitor_type": 1,  # 1=全匹配模式(airtest), 2=关键词匹配模式
    # 主测试步骤中，监控弹窗启动时间(s)【一般在进入游戏主界面，开始正式测试流程过程中，出现无法继续执行后续步骤时候，考虑出现系统弹窗阻塞情况使用该参数】
    "system_monitor_restart_timeout": 15,
    # 系统级别权限监控间隔时间（s）
    "system_monitor_interval_timeout": 0.5,
    # 权限按钮资源ID
    "system_buttons": [
        # Meizu
        "com.qianxi.fqsg_yy.qxhf:id/tv_ok",
        "com.android.packageinstaller:id/permission_allow_button",

        # Redmi
        "com.qianxi.fqsg_yy.qxhf:id/tv_ok",
        "com.lbe.security.miui:id/permission_allow_button",
        "com.lbe.security.miui:id/permission_allow_foreground_only_button",

        # vivo
        "com.qianxi.fqsg_yy.qxhf:id/tv_ok",
        "com.android.permissioncontroller:id/permission_allow_button",
        "com.android.permissioncontroller:id/permission_allow_one_time_button",
        "com.android.packageinstaller:id/permission_allow_button",

        # Honor
        "com.qianxi.fqsg_yy.qxhf:id/tv_ok",
        "com.android.permissioncontroller:id/permission_allow_button",
        "android:id/log_access_dialog_allow_button",

        # OnePlus
        "com.qianxi.fqsg_yy.qxhf:id/tv_ok",
        "com.android.permissioncontroller:id/permission_allow_button"
    ],
    # 权限按钮文本关键词
    "system_keywords": {
        "allow": [
            "允许",
            "同意",
            "始终允许",
            "仅在使用中允许",
            "本次时使用时允许",
            "允许访问一次"
        ],
        "deny": [  # 预留的拒绝权限关键词
            "不",
            "拒绝",
            "禁止",
            "否"
        ],
    }
}

# SDK 权限弹窗配置（一般渠道包会有一些特殊处理的弹窗）
SDK_PERMISSION_CONFIG = {
    # 监控模式
    "sdk_monitor_type": 2,  # 1=全匹配模式(airtest), 2=关键词匹配模式
    # 主测试步骤中，监控弹窗启动时间(s)【一般在进入游戏主界面，开始正式测试流程过程中，出现无法继续执行后续步骤时候，考虑出现系统弹窗阻塞情况使用该参数】
    "sdk_monitor_restart_timeout": 15,
    # 权限按钮资源ID
    "sdk_buttons": [
    ],
    # 权限按钮文本关键词
    "sdk_keywords": {
        "allow": [
            "不在展示",  # 华为
            "本应用今日不在展示",  # 华为
        ],
        "deny": [  # 预留的拒绝权限关键词
        ],

    }
}

"""
# 特殊步骤配置
STEP_TYPE_CONFIG = {
    0: "等待控件出现",  # 循环等待直到目标控件图出现，默认 30s，参考wait_timeout
    1: "等待控件消失",  # 循环等待直到目标控件图消失，默认 30s，参考wait_timeout
    2: "校验主界面",  # 是否进入主界面，进入后自动关闭监控线程，参考auto_pause_monitor
    3: "普通点击",  # 点击图片后 对比 被点击的图片是否消失（弹窗等）
    4: "拖拽操作",  # 拖拽操作
    5: "多图点击",  # 多备选图点击
    6: "非强制点击",  # 非强制点击
    7: "文本输入",  # 输入文本内容
    8: "断言校验",  # 断言操作，默认重试 1 次，参考 assert_retry_times
    9: "重启应用",  # 重启应用操作
    10: "长按",  # 长按操作，默认1s

    # POCO控件操作
    101: "等待控件出现",  # 循环等待直到目标控件图出现，默认 30s，参考wait_timeout
    102: "等待控件消失",  # 循环等待直到目标控件图消失，默认 30s，参考wait_timeout
    103: "点击并校验",  # 点击并校验控件消失
    104: "控件拖拽",  # 控件拖拽操作
    105: "点击不校验",  # 点击不校验控件消失
    106: "长按控件",  # 长按控件
    107: "文本输入"  # 输入文本内容
    108: "校验主界面"  # 是否进入主界面，进入后自动关闭监控线程，参考auto_pause_monitor
}
"""
