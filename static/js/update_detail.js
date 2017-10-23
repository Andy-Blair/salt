/**
 * Created by root on 9/15/17.
 */

$(function () {
    var socket=new WebSocket("ws://"+window.location.host+window.location.pathname+"/s");
    socket.onopen=function () {
        socket.send("read_start")
    };
    socket.onmessage=function (event) {
        $("#retun_data").text("hello")
    }
});
