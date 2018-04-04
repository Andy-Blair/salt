tomcat_start:
  cmd.run:
    - env:
      - JAVA_HOME: /apps/product/jdk1.8
      - JRE_HOME: /apps/product/jdk1.8/jre
    - name: sh /apps/product/tomcat/bin/startup.sh
    - user: app
