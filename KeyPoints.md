## **1. 报告生成逻辑**
1.单设备生成的模版使用log_template.html生成log.html。多设备报告使用report_tpl.html，将所有log.html汇总起来。

## replay_script.py 用于回放录制的脚本。
执行命令及参数解释说明：
1. python replay_script.py --show-screens --script outputs/recordlogs/scene1_nologin_steps_2025-04-07.json --loop-count 1 --script outputs/recordlogs/scene2_guide_steps_2025-04-07.json --max-duration 30：
说明：先执行场景1的登录操作，然后执行场景2的引导操作。
--script 参数表示指定了回放步骤文件为outputs/recordlogs/scene1_nologin_steps_2025-04-07.json 
--loop-count 1 ，表示此文件只会循环执行一次。
--script 参数指定了回放步骤文件为outputs/recordlogs/scene2_guide_steps_2025-04-07.json 
--max-duration 30，表示此步骤无视循环次数，会执行30秒后结束。

2. python replay_script.py --show-screens --script outputs/recordlogs/scene2_guide_steps_2025-04-07.json --max-duration 30
--script参数指定了回放步骤文件为outputs/recordlogs/scene2_guide_steps_2025-04-07.json，可能会循环执行一到多次，直到达到最大运行时间30秒。

3. python replay_script.py --show-screens --script outputs/recordlogs/scene1_login_steps_2025-04-07.json --loop-count 1：
--script参数指定了回放步骤文件为outputs/recordlogs/scene1_login_steps_2025-04-07.json，并且会循环执行一次。
