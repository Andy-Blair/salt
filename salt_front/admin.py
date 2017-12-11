# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.contrib import admin

from models import *

# Register your models here.

class ServersAdmin(admin.ModelAdmin):
    list_display = ('ipaddress','ostype','describe')

class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('name','url','path','type','git_url')

class ServicesAdmin(admin.ModelAdmin):
    list_display = ('name','belong')


admin.site.register(Servers,ServersAdmin)
admin.site.register(Services,ServicesAdmin)
admin.site.register(Website,WebsiteAdmin)
