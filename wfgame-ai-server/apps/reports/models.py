#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试报告管理应用的数据模型
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models.common import CommonFieldsMixin


class Report(CommonFieldsMixin):
    """测试报告"""
    STATUS_CHOICES = (
        ('generating', _('生成中')),
        ('completed', _('已完成')),
        ('failed', _('生成失败')),
    )

    name = models.CharField(_('报告名称'), max_length=255)
    task = models.ForeignKey('tasks.Task',
                          verbose_name=_('关联任务'),
                          on_delete=models.SET_NULL,
                          null=True,
                          related_name='reports')
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='generating')
    report_path = models.CharField(_('报告路径'), max_length=500)
    summary_path = models.CharField(_('汇总报告路径'), max_length=500, blank=True)
    duration = models.FloatField(_('持续时间(秒)'), default=0)
    total_cases = models.IntegerField(_('用例总数'), default=0)
    passed_cases = models.IntegerField(_('通过用例数'), default=0)
    failed_cases = models.IntegerField(_('失败用例数'), default=0)
    error_cases = models.IntegerField(_('错误用例数'), default=0)
    skipped_cases = models.IntegerField(_('跳过用例数'), default=0)
    success_rate = models.FloatField(_('c成功率'), default=0)

    class Meta:
        db_table = 'report_report'
        verbose_name = _('测试报告')
        verbose_name_plural = _('测试报告')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['success_rate']),
        ]

    def __str__(self):
        return self.name


class ReportDetail(CommonFieldsMixin):
    """
    报告详情
    与报告表关联，记录每个设备上每个脚本的执行结果
    1对多关系：一个报告包含多个报告详情
    """
    report = models.ForeignKey(Report,
                            verbose_name=_('报告'),
                            on_delete=models.CASCADE,
                            related_name='details')
    device = models.ForeignKey('devices.Device',
                            verbose_name=_('设备'),
                            on_delete=models.SET_NULL,
                            null=True)
    # script = models.ForeignKey('scripts.Script',
    #                         verbose_name=_('脚本'),
    #                         on_delete=models.SET_NULL,
    #                         null=True)
    result = models.CharField(_('执行结果'), max_length=50, default='pending')
    duration = models.FloatField(_('持续时间(秒)'), default=0)
    error_message = models.TextField(_('错误信息'), blank=True) # 当前设备，任务中断时的错误信息
    screenshot_path = models.CharField(_('截图路径'), max_length=500, blank=True)
    log_path = models.CharField(_('日志路径'), max_length=500, blank=True)
    """
    每一步执行结果，按脚本 steps 的顺序一一对应。
    结构示例（外层为数组，数组中每个元素表示一个脚本在该设备上的一次执行记录，包含 meta/steps/summary；整个数组存入 step_results）：
    [
        {
            "meta": {
                "id": 200,
                "name": "测试脚本A",
                "loop-count": 2,
                "max-duration": 60
            },
            "steps": [
                {
                    "action": "wait_for_stable",
                    "remark": "等待应用启动后界面稳定",
                    "duration": 3,
                    "max_wait": 6,
                    "detection_method": "ai",
                    "result": {
                        "status": "pending",
                        "display_status": "等待中",
                        "start_time": null,
                        "end_time": null,
                        "local_pic_pth": "",
                        "oss_pic_pth": "",
                        "error_msg": "", # 当前步骤执行的报错信息
                        }
                },
                {
                   "action": "click",
                    "remark": "如果发现【权限弹窗】，点击【确定】按钮",
                    "yolo_class": "operation-confirm",
                    "detection_method": "ai",
                    "result": {
                        "status": "pending",
                        "display_status": "等待中",
                        "start_time": null,
                        "end_time": null,
                        "local_pic_pth": "",
                        "oss_pic_pth": "",
                        "error_msg": "", # 当前步骤执行的报错信息
                    }
            ],
            "summary": {
                "total": 2,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "start_time": null,
                "end_time": null,
                "duration": null,
                "duration_ms": null
            }
        },
        {
            "meta": {
            },
            "steps": [
                {
                }
            ],
            "summary": {
            }
        }
    ]
    """
    step_results = models.JSONField(_('步骤结果'), default=dict, blank=True)

    class Meta:
        db_table = 'report_detail'
        verbose_name = _('报告详情')
        verbose_name_plural = _('报告详情')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report.name} - {self.device.name if self.device else 'Unknown Device'} - {self.script.name if self.script else 'Unknown Script'}"

    def init_step_results_from_script(self):
        """根据绑定脚本的 steps 初始化完整结构（包含 meta/steps/summary）。"""
        raw_steps = []
        if hasattr(self, 'script') and self.script and isinstance(getattr(self.script, 'steps', None), list):
            raw_steps = self.script.steps

        steps = []
        for i, s in enumerate(raw_steps or []):
            title = s.get('title') if isinstance(s, dict) else None
            action = s.get('action') if isinstance(s, dict) else None
            params = s.get('params') if isinstance(s, dict) else None
            steps.append({
                "index": i + 1,
                "title": title or f"Step {i+1}",
                "action": action or "",
                "params": params or {},
                "status": "pending",
                "start_time": None,
                "end_time": None,
                "duration": None,
                "duration_ms": None,
                "screenshot_path": "",
                "thumbnail_path": "",
                "message": "",
                "error_message": "",
                "result": {"matched": None, "coords": None, "extra": {}},
                "retries": 0,
            })

        data = {
            "meta": {
                "id": getattr(getattr(self, 'script', None), 'id', None),
                "name": getattr(getattr(self, 'script', None), 'name', ""),
                "loop-count": 1,
                "max-duration": None,
            },
            "steps": steps,
            "summary": {
                "total": len(steps),
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "start_time": None,
                "end_time": None,
                "duration": None,
                "duration_ms": None,
            }
        }

        self.step_results = data
        self.save(update_fields=["step_results"])
        return len(steps)

