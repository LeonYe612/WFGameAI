from roboflow import Roboflow

rf = Roboflow(api_key="84wuVrPhNhDVw7PcGV6M")
workspace = rf.workspace("paperrockscissors-7axmg")

# 列出该工作区所有项目
projects = workspace.projects()
for project in projects:
    print(project)
