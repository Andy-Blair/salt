tomcat_start:
  cmd.run:
    - env:
      - JAVA_HOME: /apps/product/jdk1.8.0_121
      - JRE_HOME: /apps/product/jdk1.8.0_121/jre
    - cwd: /apps/product/tomcat/bin/
    - name: sh /apps/product/tomcat/bin/startup.sh
    - user: app
