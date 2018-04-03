tail_id=`ps aux | grep -v grep | grep tomcat | grep tail | awk '{print $2}'`
if [ -n "$tail_id" ];then
  kill -9 $tail_id
else
  echo "no tail run"
fi
