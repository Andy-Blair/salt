#!/usr/bin/python
# _*_ coding:utf-8 _*_
import time

with open("/apps/product/web_git/tmp_log", 'w') as lf:
    pass
with open("/apps/product/tomcat/logs/catalina.out") as f:
    f.seek(0, 2)
    while True:
        con = f.readline()
        if len(con.strip()) > 0:
            with open("/apps/product/web_git/tmp_log", "a+") as tf:
                tf.write(con)
            if "Server startup in" in con:
                break
        else:
            time.sleep(1)
