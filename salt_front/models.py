# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import Group

# Create your models here.


class Servers(models.Model):
    # server info
    server_id = models.AutoField(primary_key=True)
    ipaddress = models.CharField(max_length=50,unique=True)
    ostype = models.CharField(max_length=50)
    describe = models.CharField(max_length=200)
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return self.ipaddress


class Website(models.Model):
    # website info
    website_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    path = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    deploy_env = models.CharField(max_length=50)
    deploy_status = models.IntegerField(default=0)  # 0-no deploy,1-deploying
    dev_branch = models.CharField(max_length=50)
    git_url = models.CharField(max_length=100,default="-")
    server = models.ManyToManyField(Servers)
    init_result = models.IntegerField(default=0)  # 0-not init,1-init success,2-init fail
    merge_result = models.CharField(max_length=50,default="-")
    build_result = models.CharField(max_length=50,default="-")
    create_tag_result = models.CharField(max_length=50,default="-")

    def __unicode__(self):
        return self.name


class Services(models.Model):
    # service info
    service_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    belong = models.CharField(max_length=100)
    server = models.ManyToManyField(Servers)

    def __unicode__(self):
        return self.name


class Commit(models.Model):
    # commit information
    com_id = models.AutoField(primary_key=True)
    tag_name = models.CharField(max_length=50)
    tag_message = models.CharField(max_length=5000)
    commit_id = models.CharField(max_length=100,unique=True)
    update_date = models.DateTimeField(auto_now_add=True)
    website = models.ForeignKey(Website)

    def __unicode__(self):
        return self.tag_name


class Jenkins(models.Model):
    jk_id = models.AutoField(primary_key=True)
    jk_name = models.CharField(max_length=50)
    # build_status = models.CharField(max_length=50)
    # last_build_result = models.CharField(max_length=50)
    # last_build_time = models.DateTimeField(auto_now_add=True)
    website = models.OneToOneField(Website)

    def __unicode__(self):
        return self.jk_name


class Email_user(models.Model):
    em_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)

    def __unicode__(self):
        return self.email
