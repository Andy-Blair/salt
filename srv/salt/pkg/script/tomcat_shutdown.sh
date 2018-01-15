tomcat_pid=`ps -ef | grep tomcat | grep -v grep | grep -v tail | awk '{print $2}'`
if [ -n "$tomcat_pid" ];then
  kill -9 $tomcat_pid
  echo "Stop Tomcat success"
else
  echo "No Tomcat start"
fi
