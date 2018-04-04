#!/usr/bin/python
# _*_ coding:utf-8 _*_

import commands

r = commands.getoutput('ps aux | grep -v "grep" | grep tomcat | grep org.apache.catalina.startup.Bootstrap | wc -l')

t = int(r)
if t == 0:
    print "stop"
elif t == 1:
    print "start"
else:
    print "%s Tomcat Running, can't start or stop" % t
