tomcat_start:
  cmd.run:
    - name: sh /apps/product/tomcat/bin/startup.sh
    - user: app
