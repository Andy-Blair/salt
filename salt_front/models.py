# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
    url = models.URLField()
    path = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    git_url = models.CharField(max_length=100,default="-")
    server_id = models.ManyToManyField(Servers)

    def __unicode__(self):
        return self.name


class Services(models.Model):
    # service info
    service_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    belong = models.CharField(max_length=100)
    server_id = models.ManyToManyField(Servers)

    def __unicode__(self):
        return self.name
