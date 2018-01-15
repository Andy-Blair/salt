tail_id=`ps -ef | grep tail | grep -v grep | awk '{print $2}'`
if [ -n "$tail_id" ];then
  kill -9 $tail_id
else
  echo "no tail run"
fi
