#!/usr/bin/python
# _*_ coding:utf-8 _*_

index_file = "/apps/product/web_git/tmp_log_index"
tmp_log = "/apps/product/web_git/tmp_log"
try:
    with open(index_file) as f:
        index = int(f.read())
except Exception:
    index = 0
with open(tmp_log) as lf:
    lf.seek(index, 0)
    con = lf.read()
    if len(con) > 0:
        with open(index_file, 'w') as tf:
            if "Server startup in" not in con:
                new_index = lf.tell()
            else:
                new_index = 0
            tf.write(str(new_index))
        print con
