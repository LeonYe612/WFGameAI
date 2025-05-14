"""
主应用的视图
"""

from django.shortcuts import render

def index_view(request):
    """
    网站首页视图
    
    渲染首页模板，显示平台主要功能和链接
    """
    return render(request, 'index.html') 