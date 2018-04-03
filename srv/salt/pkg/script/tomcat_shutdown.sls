tomcat_shutdown:
  cmd.script:
  - source: salt://pkg/script/tomcat_shutdown.sh
  - user: app
