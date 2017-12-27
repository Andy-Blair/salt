"""saltstack URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
from django.conf import settings
import views

urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/salt/website/")),
    url(r'^login/$', views.login_view, name='login_view'),
    url(r'^logout/$', views.logout_view, name='logout_view'),
    url(r'^website/$', views.website, name='website'),
    url(r'^website/(update|rollback)*/$', views.update_detail, name='update_detail'),
    url(r'^website/(update|rollback)*/s/$', views.detail_socket, name='detail_socket'),
    url(r'^website/rollback/s$', views.detail_socket, name='detail_socket'),
    url(r'^website_manage/$', views.website_manage, name='website_manage'),
    url(r'^website/(\d+)/d$', views.website_detail, name='website_detail'),
    url(r'^website/add/$', views.website_add, name='website_add'),
    url(r'^website/add/cpf/$', views.create_pro_file, name='create_pro_file'),
    url(r'^website/add/server/auth$', views.server_auth, name='server_auth'),
    url(r'^website/add/website/auth$', views.website_auth, name='website_auth'),
    url(r'^website/modify/(\d+)/$', views.website_modify, name='website_modify'),
    url(r'^website/del/(\d+)/$', views.website_del, name='website_del'),
    url(r'^website_list/$', views.wesite_list, name='website_list'),
    url(r'^website/tag/$', views.website_tag, name='website_tag'),
    url(r'^server_manage/$', views.server_manage, name='server_manage'),
    url(r'^server_list/$', views.server_list, name='server_list'),
]

# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
